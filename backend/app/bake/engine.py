"""确定性 bake：复制骨架 + 领域叠加 + SQL / Spec。"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.bake.catalog import normalize_auth_template
from app.bake.domain_schema import (
    deterministic_llm_patch,
    merge_schema,
    product_name_from_title,
    validate_schema,
    write_schema_artifacts,
)

# 答辩/开题常见硬约束：交付库表不宜过少或灌水过多
TABLE_COUNT_MIN = 6
# 含 L0 平台表 sys_message；论坛等顶格域可达 13
TABLE_COUNT_MAX = 13

# 领域 DDL / 种子模板：backend/app/bake/sql/<DOMAIN>.sql；缺省回落 DOM-GENERIC.sql
_SQL_DIR = Path(__file__).resolve().parent / "sql"
_FALLBACK_SQL = "DOM-GENERIC.sql"


def count_create_tables(sql: str) -> int:
    return len(re.findall(r"(?i)create\s+table\b", sql))


def assert_table_budget(sql: str, domain: str) -> None:
    n = count_create_tables(sql)
    if not (TABLE_COUNT_MIN <= n <= TABLE_COUNT_MAX):
        raise ValueError(
            f"{domain} schema 表数量={n}，必须在 {TABLE_COUNT_MIN}~{TABLE_COUNT_MAX} 之间"
        )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _merge_tree(src: Path, dest: Path) -> None:
    """将 src 覆盖合并到 dest（文件覆盖，目录递归）。"""
    if not src.exists():
        return
    for path in src.rglob("*"):
        rel = path.relative_to(src)
        target = dest / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def _sql_template_path(domain: str, archetype: str | None = None) -> Path:
    if domain == "DOM-GENERIC":
        from app.bake.archetype_shells import shell_sql_filename

        path = _SQL_DIR / shell_sql_filename(archetype)
        if path.is_file():
            return path
    path = _SQL_DIR / f"{domain}.sql"
    if path.is_file():
        return path
    fallback = _SQL_DIR / _FALLBACK_SQL
    if not fallback.is_file():
        raise FileNotFoundError(f"缺少 SQL 模板: {path} 与 {_FALLBACK_SQL}")
    return fallback


def domain_sql(
    domain: str,
    db_name: str,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
) -> str:
    """按领域加载 SQL；GENERIC 多主路径从已有模板拼装。"""
    if domain == "DOM-GENERIC":
        from app.bake.archetype_shells import path_flags, shell_sql_filename
        from app.bake.sql_compose import compose_generic_sql

        arches = list(archetypes or ([archetype] if archetype else ["ARCH-CRUD"]))
        need_flow, need_trade, need_reserve = path_flags(arches)
        if sum([need_flow, need_trade, need_reserve]) >= 2:
            return compose_generic_sql(
                need_flow=need_flow,
                need_trade=need_trade,
                need_reserve=need_reserve,
                db_name=db_name,
                table_min=TABLE_COUNT_MIN,
                table_max=TABLE_COUNT_MAX,
            )
        fname = shell_sql_filename(archetypes=arches)
        path = _SQL_DIR / fname
        if not path.is_file():
            path = _sql_template_path(domain, archetype)
        text = path.read_text(encoding="utf-8")
    else:
        text = _sql_template_path(domain, archetype).read_text(encoding="utf-8")
    return (
        text.replace("${DB_NAME}", db_name)
        .replace("${DOMAIN}", domain)
        .replace("${TABLE_COUNT_MIN}", str(TABLE_COUNT_MIN))
        .replace("${TABLE_COUNT_MAX}", str(TABLE_COUNT_MAX))
    )


def bake_project(project_id: str, spec: dict[str, Any], db_name: str) -> Path:
    """复制 baseline，再叠加 domains/<domain>，写入 spec / SQL。"""
    settings = get_settings()
    src = settings.skeletons_dir / "baseline"
    dest = settings.workspace_dir / project_id
    if dest.exists():
        from app.services.runtime import detach_frontend_deps

        detach_frontend_deps(dest)
        shutil.rmtree(dest)
    if not src.exists():
        raise FileNotFoundError(f"骨架不存在: {src}")
    shutil.copytree(src, dest)

    domain = spec.get("domain", "DOM-GENERIC")
    overlay = settings.skeletons_dir / "domains" / domain
    if overlay.exists():
        _merge_tree(overlay, dest)

    _write(dest / "spec.json", json.dumps(spec, ensure_ascii=False, indent=2))
    sql = domain_sql(
        domain,
        db_name,
        spec.get("archetype"),
        archetypes=spec.get("archetypes"),
    )
    assert_table_budget(sql, domain)
    _write(dest / "sql" / "schema.sql", sql)

    from app.bake.domain_schema import product_name_from_title

    title = spec.get("title", "毕设系统")
    schema = spec.get("schema") or {}
    app_name = (
        ((schema.get("labels") or {}).get("appName") or "").strip()
        or product_name_from_title(title)
    )

    app_yml = dest / "backend" / "src" / "main" / "resources" / "application.yml"
    if app_yml.exists():
        text = app_yml.read_text(encoding="utf-8")
        text = text.replace("${DB_NAME}", db_name)
        # thesis.title / meta 用短产品名，避免登录页显示「毕设系统」或整段开题题名
        text = text.replace("${PROJECT_TITLE}", app_name)
        text = _patch_thesis_yml(text, domain, spec)
        app_yml.write_text(text, encoding="utf-8")

    env_fe = dest / "frontend" / ".env"
    auth_tpl = normalize_auth_template(spec.get("auth_template"))
    theme = spec.get("theme", "lib-ink")
    env_fe.write_text(
        f"VITE_APP_TITLE={app_name}\n"
        f"VITE_THEME={theme}\n"
        f"VITE_AUTH_TEMPLATE={auth_tpl}\n",
        encoding="utf-8",
    )

    from app.bake.auth_hero import auth_hero_public_path, fetch_auth_hero
    from app.bake.portal_banners import fetch_portal_banners

    fetch_auth_hero(dest, domain, theme)
    portal_banners = fetch_portal_banners(dest, domain, theme, schema)
    _write_factory_delivered(
        dest,
        title,
        theme,
        auth_tpl,
        schema,
        spec.get("accept"),
        auth_hero=auth_hero_public_path(dest),
        portal_banners=portal_banners,
        domain=domain,
    )

    # 保留 Home.vue：Vite 会静态分析同文件内所有 import()，删掉会导致报修壳也编译失败
    return dest


def _patch_thesis_yml(text: str, domain: str, spec: dict[str, Any]) -> str:
    """写入 domain / register-role / ticket-mode（薄领域 runtime 来自 catalog）。"""
    from app.bake.catalog import DOMAINS
    from app.bake.domain_schema import DOMAIN_CAPABILITIES

    # GENERIC 等域的 runtime 写在 spec 上（按 ARCH-* 绑壳）
    runtime = dict(spec.get("runtime") or {})
    if not runtime:
        runtime = dict((DOMAINS.get(domain) or {}).get("runtime") or {})
    roles = spec.get("roles") or (DOMAINS.get(domain) or {}).get("roles") or ["user", "admin"]
    register_role = runtime.get("register_role") or (roles[0] if roles else "user")
    ticket_mode = runtime.get("ticket_mode") or "archive"
    ticket_table = runtime.get("ticket_table") or "borrow"
    caps = set(spec.get("capabilities") or DOMAIN_CAPABILITIES.get(domain) or [])
    use_quota = runtime.get("use_quota")
    if use_quota is None:
        use_quota = "quota" in caps
    use_deadline = runtime.get("use_deadline")
    if use_deadline is None:
        use_deadline = "deadline" in caps

    def _set_key(src: str, key: str, value: str) -> str:
        import re

        pat = re.compile(rf"(?m)^(\s*{re.escape(key)}:\s*).*$")
        if pat.search(src):
            return pat.sub(rf"\g<1>{value}", src, count=1)
        # 插在 thesis: 块末（简单追加到文件 thesis 段）
        if "thesis:" in src:
            return src.replace(
                "thesis:\n",
                f"thesis:\n  {key}: {value}\n",
                1,
            )
        return src + f"\nthesis:\n  {key}: {value}\n"

    text = _set_key(text, "domain", domain)
    text = _set_key(text, "register-role", str(register_role))
    text = _set_key(text, "ticket-mode", str(ticket_mode))
    text = _set_key(text, "ticket-table", str(ticket_table))
    text = _set_key(text, "use-quota", "true" if use_quota else "false")
    text = _set_key(text, "use-deadline", "true" if use_deadline else "false")
    allow_multi = runtime.get("allow_multi_ticket")
    if allow_multi is None:
        allow_multi = False
    text = _set_key(text, "allow-multi-ticket", "true" if allow_multi else "false")
    check_conflict = runtime.get("check_time_conflict")
    if check_conflict is None:
        check_conflict = "time_conflict" in caps
    text = _set_key(text, "check-time-conflict", "true" if check_conflict else "false")
    enable_ticket = runtime.get("enable_ticket")
    if enable_ticket is None:
        enable_ticket = "ticket_flow" in caps
    text = _set_key(text, "enable-ticket", "true" if enable_ticket else "false")
    ticket_ent = ((spec.get("schema") or {}).get("entities") or {}).get("ticket") or {}
    text = _set_key(
        text,
        "ticket-two-level",
        "true" if ticket_ent.get("twoLevelApprove") else "false",
    )
    text = _set_key(
        text,
        "ticket-require-attach",
        "true" if ticket_ent.get("requireAttach") else "false",
    )
    text = _set_key(
        text,
        "ticket-allow-rating",
        "true" if ticket_ent.get("allowRating") else "false",
    )
    text = _set_key(
        text,
        "ticket-check-mutex",
        "true" if ticket_ent.get("checkMutex") else "false",
    )
    cat_limit = ticket_ent.get("categoryLimit")
    try:
        cat_limit_n = int(cat_limit) if cat_limit is not None else 0
    except (TypeError, ValueError):
        cat_limit_n = 0
    text = _set_key(text, "ticket-category-limit", str(max(0, cat_limit_n)))
    text = _set_key(
        text,
        "ticket-week-calendar",
        "true" if ticket_ent.get("weekCalendar") else "false",
    )
    text = _set_key(
        text,
        "ticket-allow-checkin",
        "true" if ticket_ent.get("allowCheckin") else "false",
    )
    text = _set_key(
        text,
        "ticket-pick-loan-period",
        "true" if ticket_ent.get("pickLoanPeriod") else "false",
    )
    text = _set_key(
        text,
        "ticket-allow-qty",
        "true" if ticket_ent.get("allowQty") else "false",
    )
    text = _set_key(
        text,
        "ticket-require-remark",
        "true" if ticket_ent.get("requireRemark") else "false",
    )
    text = _set_key(
        text,
        "ticket-pick-date-range",
        "true" if ticket_ent.get("pickDateRange") else "false",
    )
    resv_ent = ((spec.get("schema") or {}).get("entities") or {}).get("reservation") or {}
    text = _set_key(
        text,
        "slot-require-remark",
        "true" if resv_ent.get("requireRemark") else "false",
    )
    archive_ent = ((spec.get("schema") or {}).get("entities") or {}).get("archive") or {}
    text = _set_key(
        text,
        "archive-soft-delete",
        "true" if archive_ent.get("softDelete") else "false",
    )
    ph = spec.get("password_hash") or "none"
    text = _set_key(text, "password-hash", str(ph))
    for yml_key, runtime_key in (
        ("archive-category-table", "archive_category_table"),
        ("archive-item-table", "archive_item_table"),
        ("archive-tag-table", "archive_tag_table"),
        ("archive-item-tag-table", "archive_item_tag_table"),
        ("lookup-site-table", "lookup_site_table"),
        ("lookup-unit-table", "lookup_unit_table"),
        ("lookup-type-table", "lookup_type_table"),
        ("lookup-site-label", "lookup_site_label"),
        ("lookup-unit-label", "lookup_unit_label"),
        ("lookup-type-label", "lookup_type_label"),
        ("order-cart-table", "order_cart_table"),
        ("order-table", "order_table"),
        ("order-line-table", "order_line_table"),
        ("slot-table", "slot_table"),
        ("reservation-table", "reservation_table"),
    ):
        val = runtime.get(runtime_key)
        if val:
            text = _set_key(text, yml_key, str(val))
    if "order_lines" not in caps:
        text = _set_key(text, "order-cart-table", '""')
        text = _set_key(text, "order-table", '""')
        text = _set_key(text, "order-line-table", '""')
    if "slot_reserve" not in caps:
        text = _set_key(text, "slot-table", '""')
        text = _set_key(text, "reservation-table", '""')
    if not runtime.get("archive_tag_table"):
        text = _set_key(text, "archive-tag-table", '""')
        text = _set_key(text, "archive-item-tag-table", '""')
    return text


def _write_profile_fields_resource(dest: Path, schema: dict[str, Any]) -> None:
    """学生端后端读取，注册/资料必填校验。"""
    fields = schema.get("profileFields") or []
    path = dest / "backend" / "src" / "main" / "resources" / "domain-profile-fields.json"
    _write(path, json.dumps(fields, ensure_ascii=False, indent=2))


def _write_factory_delivered(
    dest: Path,
    title: str,
    theme: str,
    auth_tpl: str,
    schema: dict[str, Any],
    accept: str | None = None,
    auth_hero: str = "",
    portal_banners: list | None = None,
    domain: str = "DOM-GENERIC",
) -> None:
    delivered = dest / "frontend" / "src" / "factoryDelivered.js"
    if not auth_hero:
        from app.bake.auth_hero import auth_hero_public_path

        auth_hero = auth_hero_public_path(dest)
    if portal_banners is None:
        from app.bake.portal_banners import portal_banners_from_workspace

        portal_banners = portal_banners_from_workspace(dest, schema)
    from app.bake.catalog import DOMAINS

    domain_label = (DOMAINS.get(domain) or {}).get("label") or "通用"
    payload = {
        "title": title,
        "theme": theme,
        "domain": domain,
        "domainLabel": domain_label,
        "authTemplate": auth_tpl,
        "authHero": auth_hero or "",
        "portalBanners": portal_banners or [],
        "accept": accept or schema.get("accept") or "reject",
        "schema": schema,
    }
    delivered.write_text(
        "/**\n"
        " * 工厂 bake 写入的交付配置（会打进 ZIP）。\n"
        " * 含 Domain Schema（文案/菜单/能力）；勿手改。\n"
        " */\n"
        f"export const FACTORY_DELIVERED = {json.dumps(payload, ensure_ascii=False, indent=2)}\n",
        encoding="utf-8",
    )
    _write_profile_fields_resource(dest, schema)


def emit_schema_to_workspace(workspace: Path, spec: dict[str, Any]) -> list[str]:
    """把已合并的 schema 写入 islands / factoryDelivered / spec.json。"""
    merged = spec.get("schema") or {}
    ok, errors = validate_schema(merged)
    if not ok:
        raise RuntimeError("schema 校验失败: " + "; ".join(errors))
    written = write_schema_artifacts(workspace, merged)
    _write(workspace / "spec.json", json.dumps(spec, ensure_ascii=False, indent=2))
    auth_tpl = normalize_auth_template(spec.get("auth_template"))
    _write_factory_delivered(
        workspace,
        spec.get("title", "毕设系统"),
        spec.get("theme", "lib-ink"),
        auth_tpl,
        merged,
        spec.get("accept"),
        domain=spec.get("domain", "DOM-GENERIC"),
    )
    return written


def llm_fill_islands(workspace: Path, spec: dict[str, Any], enabled: bool) -> list[str]:
    """确定性填岛（无 LLM）。真填岛走 app.llm.agents.run_island_agent。"""
    base = spec.get("schema") or {}
    patch = deterministic_llm_patch(spec, enabled)
    merged = merge_schema(base, patch)
    for k in ("accept", "missing_capabilities", "out_of_mvp_signals", "capabilities"):
        if k in base:
            merged[k] = base[k]
    spec["schema"] = merged
    return emit_schema_to_workspace(workspace, spec)

