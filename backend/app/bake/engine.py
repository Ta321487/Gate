"""确定性 bake：复制骨架 + 领域叠加 + SQL / Spec。"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.bake.catalog import (
    normalize_auth_entry_mode,
    normalize_auth_role_widget,
    normalize_auth_template,
    normalize_chrome,
)
from app.bake.domain_schema import (
    deterministic_llm_patch,
    merge_schema,
    product_name_from_title,
    validate_schema,
    write_schema_artifacts,
)

# 答辩/开题常见硬约束：交付库表不宜过少或灌水过多
TABLE_COUNT_MIN = 6
# 含 L0 平台表 sys_message；论坛等顶格域可达 15
TABLE_COUNT_MAX = 15

# GENERIC 壳：bake/sql/DOM-GENERIC*.sql；具名域：sql_domain_templates（唯一路径，无散文件）
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


def _patch_student_readme(
    dest: Path, *, app_name: str, db_name: str, java_package: str = "com.thesis"
) -> None:
    """ZIP 根目录 README：写入课题名、库名与 Java 包路径。"""
    path = dest / "README.md"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    text = text.replace("${APP_NAME}", app_name or "毕设系统")
    text = text.replace("${DB_NAME}", db_name or "thesis_app")
    text = text.replace("${JAVA_PACKAGE_PATH}", java_package.replace(".", "/"))
    text = text.replace("${JAVA_PACKAGE}", java_package)
    path.write_text(text, encoding="utf-8")


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
    """GENERIC 壳仍读 bake/sql/DOM-GENERIC*.sql；具名域见 DOMAIN_SQL_TEMPLATES。"""
    if domain == "DOM-GENERIC":
        from app.bake.archetype_shells import shell_sql_filename

        path = _SQL_DIR / shell_sql_filename(archetype)
        if path.is_file():
            return path
    fallback = _SQL_DIR / _FALLBACK_SQL
    if not fallback.is_file():
        raise FileNotFoundError(f"缺少 SQL 模板: {_FALLBACK_SQL}")
    return fallback


def _load_named_domain_sql(domain: str) -> str:
    """具名域唯一路径：见 sql_compose.compose_named_domain_sql。"""
    from app.bake.sql_compose import compose_named_domain_sql

    return compose_named_domain_sql(domain)


def domain_sql(
    domain: str,
    db_name: str,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
    *,
    ticket_table: str | None = None,
    capabilities: list[str] | None = None,
    proposal_text: str = "",
) -> str:
    """按领域加载 SQL；GENERIC 多主路径从已有模板拼装。"""
    if domain == "DOM-GENERIC":
        from app.bake.archetype_shells import path_flags, shell_sql_filename
        from app.bake.sql_compose import compose_generic_sql

        arches = list(archetypes or ([archetype] if archetype else ["ARCH-CRUD"]))
        need_flow, need_trade, need_reserve = path_flags(arches)
        if sum([need_flow, need_trade, need_reserve]) >= 2:
            text = compose_generic_sql(
                need_flow=need_flow,
                need_trade=need_trade,
                need_reserve=need_reserve,
                db_name=db_name,
                table_min=TABLE_COUNT_MIN,
                table_max=TABLE_COUNT_MAX,
            )
        else:
            fname = shell_sql_filename(archetypes=arches)
            path = _SQL_DIR / fname
            if not path.is_file():
                path = _sql_template_path(domain, archetype)
            text = path.read_text(encoding="utf-8")
    else:
        text = _load_named_domain_sql(domain)
    from app.bake.domains import DOMAINS
    from app.bake.favorites import favorites_wanted
    from app.bake.guestbook import guestbook_wanted
    from app.bake.ux_scan import (
        BROWSE_HISTORY_CAP,
        GALLERY_CAP,
        scan_browse_history,
        scan_gallery,
    )
    from app.bake.order_extras import ORDER_REVIEW_CAP, scan_order_review
    from app.bake.sql_fragments import (
        ensure_browse_history_sql,
        ensure_coupon_lifecycle_sql,
        ensure_favorites_sql,
        ensure_gallery_sql,
        ensure_guestbook_sql,
        ensure_order_review_sql,
        ensure_shared_sql_columns,
        ensure_ticket_progress_sql,
    )
    from app.bake.staff_posts import append_staff_seed_sql

    text = ensure_shared_sql_columns(text)
    runtime = ((DOMAINS.get(domain) or {}).get("runtime") or {})
    resolved_ticket = ticket_table or runtime.get("ticket_table")
    if not resolved_ticket and domain == "DOM-GENERIC":
        from app.bake.archetype_shells import shell_runtime

        resolved_ticket = (shell_runtime(archetype, archetypes=archetypes) or {}).get(
            "ticket_table"
        )
    resolved_item = runtime.get("archive_item_table")
    if not resolved_item and domain == "DOM-GENERIC":
        from app.bake.archetype_shells import shell_runtime

        resolved_item = (shell_runtime(archetype, archetypes=archetypes) or {}).get(
            "archive_item_table"
        ) or "biz_item"
    text = ensure_ticket_progress_sql(text, resolved_ticket)
    text = ensure_guestbook_sql(
        text,
        enabled=guestbook_wanted(
            domain=domain,
            archetype=archetype,
            archetypes=archetypes,
            capabilities=capabilities,
            proposal_text=proposal_text,
        ),
    )
    text = ensure_favorites_sql(
        text,
        enabled=favorites_wanted(
            domain=domain,
            capabilities=capabilities,
            proposal_text=proposal_text,
        ),
    )
    caps = list(capabilities or [])
    text = ensure_browse_history_sql(
        text,
        enabled=BROWSE_HISTORY_CAP in caps or scan_browse_history(proposal_text),
    )
    text = ensure_gallery_sql(
        text,
        enabled=GALLERY_CAP in caps or scan_gallery(proposal_text),
        item_table=resolved_item,
    )
    text = ensure_coupon_lifecycle_sql(
        text,
        enabled="coupon" in caps,
    )
    text = ensure_order_review_sql(
        text,
        enabled=ORDER_REVIEW_CAP in caps or scan_order_review(proposal_text),
    )
    text = append_staff_seed_sql(text, domain, archetype, archetypes)
    # 演示日历不在 bake 时写死「今天」：交付后隔月答辩仍靠启动时 SeedCalendarAligner 平移
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
        ticket_table=((spec.get("runtime") or {}).get("ticket_table")),
        capabilities=spec.get("capabilities"),
        proposal_text=str(spec.get("proposal_text") or spec.get("title") or ""),
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
        # 支持 ${PROJECT_TITLE} 与 ${PROJECT_TITLE:默认值}
        text = re.sub(
            r"\$\{PROJECT_TITLE(?::[^}]*)?\}",
            app_name.replace("\\", "\\\\"),
            text,
            count=1,
        )
        text = _patch_thesis_yml(text, domain, spec)
        app_yml.write_text(text, encoding="utf-8")

    from app.bake.java_package import remap_student_java_package, rewrite_gate_file_paths
    from app.bake.naming import resolve_slug_from_spec

    delivery_slug = resolve_slug_from_spec(spec, domain)
    new_pkg = remap_student_java_package(dest, domain, delivery_slug, project_id)
    # 门禁契约文件路径随包名改写（写入工作区 spec）
    gate = spec.get("gate")
    if isinstance(gate, dict) and gate.get("files"):
        gate = dict(gate)
        gate["files"] = rewrite_gate_file_paths(list(gate["files"] or []), new_pkg)
        spec["gate"] = gate
    # 回写 Maven 坐标到 spec，便于产物页展示
    from app.bake.java_package import java_coords_for_delivery
    from app.bake.naming import zip_download_name

    pkg, app_cls, artifact = java_coords_for_delivery(domain, delivery_slug, project_id)
    spec["delivery_slug"] = delivery_slug
    spec["java_package"] = pkg
    spec["java_application"] = app_cls
    spec["maven_artifact"] = artifact
    spec["zip_name"] = zip_download_name(delivery_slug, project_id)
    meta = spec.get("match_meta")
    if isinstance(meta, dict):
        meta["zip_name"] = spec["zip_name"]
    _write(dest / "spec.json", json.dumps(spec, ensure_ascii=False, indent=2))

    env_fe = dest / "frontend" / ".env"
    auth_tpl = normalize_auth_template(spec.get("auth_template"))
    auth_entry = normalize_auth_entry_mode(spec.get("auth_entry_mode"))
    auth_widget = normalize_auth_role_widget(spec.get("auth_role_widget"))
    chrome = normalize_chrome(spec.get("chrome"))
    theme = spec.get("theme", "lib-ink")
    env_fe.write_text(
        f"VITE_APP_TITLE={app_name}\n"
        f"VITE_THEME={theme}\n"
        f"VITE_CHROME={chrome}\n"
        f"VITE_AUTH_TEMPLATE={auth_tpl}\n"
        f"VITE_AUTH_ENTRY_MODE={auth_entry}\n"
        f"VITE_AUTH_ROLE_WIDGET={auth_widget}\n",
        encoding="utf-8",
    )

    _patch_student_readme(dest, app_name=app_name, db_name=db_name, java_package=new_pkg)

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
        auth_entry_mode=auth_entry,
        auth_role_widget=auth_widget,
        chrome=chrome,
        seed=dest.name,
    )

    # 保留 Home.vue：Vite 会静态分析同文件内所有 import()，删掉会导致报修壳也编译失败
    return dest


def _patch_thesis_yml(text: str, domain: str, spec: dict[str, Any]) -> str:
    """按本项目能力重写 thesis 段：只保留用到的键，去掉空开关与工厂话术。"""
    from app.bake.catalog import DOMAINS
    from app.bake.domain_schema import DOMAIN_CAPABILITIES
    from app.bake.guest_cta import GUEST_TEASER_LIMIT, portal_guest_browse_enabled

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
    allow_multi = bool(runtime.get("allow_multi_ticket") or False)
    check_conflict = runtime.get("check_time_conflict")
    if check_conflict is None:
        check_conflict = "time_conflict" in caps
    enable_ticket = runtime.get("enable_ticket")
    if enable_ticket is None:
        enable_ticket = "ticket_flow" in caps

    ticket_ent = ((spec.get("schema") or {}).get("entities") or {}).get("ticket") or {}
    resv_ent = ((spec.get("schema") or {}).get("entities") or {}).get("reservation") or {}
    archive_ent = ((spec.get("schema") or {}).get("entities") or {}).get("archive") or {}
    guest_on = portal_guest_browse_enabled(domain, DOMAINS.get(domain) or {})
    ph = str(spec.get("password_hash") or "none")

    # 保留已替换的 title（${PROJECT_TITLE} → 产品名）
    title_m = re.search(r"(?m)^\s*title:\s*(.+?)\s*$", text)
    title_val = (title_m.group(1).strip() if title_m else "").strip("'\"")
    if not title_val or title_val.startswith("${"):
        from app.bake.domain_schema import product_name_from_title

        title_val = product_name_from_title(spec.get("title") or "毕设系统")

    lines: list[str] = ["thesis:", f"  title: {title_val}", f"  register-role: {register_role}"]
    lines.append("  # 密码存储：none（明文）| bcrypt | md5 | sha256")
    lines.append(f"  password-hash: {ph}")

    lines.append("  # 门户未登录是否可浏览")
    lines.append(f"  portal-guest-browse: {'true' if guest_on else 'false'}")
    if guest_on:
        lines.append(f"  guest-teaser-limit: {GUEST_TEASER_LIMIT}")

    roles = ((spec.get("schema") or {}).get("roles") or {}) if isinstance(spec.get("schema"), dict) else {}
    from app.bake.staff_posts import allow_appoint_from_users as _allow_appoint

    appoint_ok = roles.get("allowAppointFromUsers")
    if appoint_ok is None:
        appoint_ok = _allow_appoint(
            domain,
            spec.get("archetype"),
            spec.get("archetypes") if isinstance(spec.get("archetypes"), list) else None,
        )
    lines.append(
        "  # 是否允许把门户业务用户任命为岗位（挂号等域关闭，岗靠种子账号）"
    )
    lines.append(f"  allow-appoint-from-users: {'true' if appoint_ok else 'false'}")

    if enable_ticket:
        lines.append("  # 单据主流程")
        lines.append("  enable-ticket: true")
        lines.append(f"  ticket-mode: {ticket_mode}")
        lines.append(f"  ticket-table: {ticket_table}")
        lines.append(f"  use-quota: {'true' if use_quota else 'false'}")
        lines.append(f"  use-deadline: {'true' if use_deadline else 'false'}")
        if allow_multi:
            lines.append("  allow-multi-ticket: true")
        if check_conflict:
            lines.append("  check-time-conflict: true")
        # 仅写出开启的单据能力，避免一排 false
        flag_map = (
            ("ticket-two-level", bool(ticket_ent.get("twoLevelApprove"))),
            ("ticket-require-attach", bool(ticket_ent.get("requireAttach"))),
            ("ticket-allow-rating", bool(ticket_ent.get("allowRating"))),
            ("ticket-check-mutex", bool(ticket_ent.get("checkMutex"))),
            ("ticket-week-calendar", bool(ticket_ent.get("weekCalendar"))),
            ("ticket-allow-checkin", bool(ticket_ent.get("allowCheckin"))),
            ("ticket-pick-loan-period", bool(ticket_ent.get("pickLoanPeriod"))),
            ("ticket-allow-qty", bool(ticket_ent.get("allowQty"))),
            ("ticket-require-remark", bool(ticket_ent.get("requireRemark"))),
            ("ticket-pick-date-range", bool(ticket_ent.get("pickDateRange"))),
            ("ticket-approve-ends-flow", bool(ticket_ent.get("approveEndsFlow"))),
        )
        on_flags = [(k, v) for k, v in flag_map if v]
        if on_flags:
            lines.append("  # 单据扩展能力")
            for k, _ in on_flags:
                lines.append(f"  {k}: true")
        try:
            cat_limit_n = int(ticket_ent.get("categoryLimit") or 0)
        except (TypeError, ValueError):
            cat_limit_n = 0
        if cat_limit_n > 0:
            lines.append(f"  ticket-category-limit: {cat_limit_n}")
        if ticket_ent.get("noShowAfterEnd") and ticket_ent.get("allowCheckin"):
            lines.append("  ticket-no-show-after-end: true")
            try:
                pen = float(ticket_ent.get("noShowPenaltyYuan") or 0)
            except (TypeError, ValueError):
                pen = 0.0
            if pen > 0:
                lines.append(f"  ticket-no-show-penalty-yuan: {pen:g}")
    else:
        # Java 默认 enable-ticket=true，关闭时必须显式写出
        lines.append("  enable-ticket: false")

    if "archive" in caps:
        cat = str(runtime.get("archive_category_table") or "category")
        item = str(runtime.get("archive_item_table") or "book")
        lines.append("  # 档案主数据表")
        lines.append(f"  archive-category-table: {cat}")
        lines.append(f"  archive-item-table: {item}")
        if archive_ent.get("softDelete"):
            lines.append("  archive-soft-delete: true")
        tag = runtime.get("archive_tag_table")
        item_tag = runtime.get("archive_item_tag_table")
        if tag and item_tag:
            lines.append(f"  archive-tag-table: {tag}")
            lines.append(f"  archive-item-tag-table: {item_tag}")

    site = runtime.get("lookup_site_table")
    unit = runtime.get("lookup_unit_table")
    typ = runtime.get("lookup_type_table")
    if site or unit or typ:
        lines.append("  # 下拉主数据（楼栋 / 房间 / 类型等）")
        if site:
            lines.append(f"  lookup-site-table: {site}")
            lines.append(f"  lookup-site-label: {runtime.get('lookup_site_label') or '楼栋'}")
        if unit:
            lines.append(f"  lookup-unit-table: {unit}")
            lines.append(f"  lookup-unit-label: {runtime.get('lookup_unit_label') or '房间'}")
        if typ:
            lines.append(f"  lookup-type-table: {typ}")
            lines.append(f"  lookup-type-label: {runtime.get('lookup_type_label') or '类型'}")

    if "order_lines" in caps:
        cart = runtime.get("order_cart_table") or "cart_line"
        ot = runtime.get("order_table") or "biz_order"
        ol = runtime.get("order_line_table") or "order_line"
        lines.append("  # 购物车 / 订单")
        lines.append(f"  order-cart-table: {cart}")
        lines.append(f"  order-table: {ot}")
        lines.append(f"  order-line-table: {ol}")
        if use_quota and not enable_ticket:
            lines.append(f"  use-quota: {'true' if use_quota else 'false'}")

    loyalty = (spec.get("schema") or {}).get("loyalty") or {}
    if "wallet" in caps:
        lines.append("  wallet-enabled: true")
    if "points" in caps:
        lines.append("  points-enabled: true")
        pts = loyalty.get("points") if isinstance(loyalty.get("points"), dict) else {}
        try:
            epy = int(pts.get("earnPerYuan") or 1)
        except (TypeError, ValueError):
            epy = 1
        if epy > 0:
            lines.append(f"  points-earn-per-yuan: {epy}")
    if "spend_discount" in caps:
        lines.append("  spend-discount-enabled: true")
        sd = loyalty.get("spendDiscount") if isinstance(loyalty.get("spendDiscount"), dict) else {}
        try:
            th = float(sd.get("thresholdYuan") or 100)
            off = float(sd.get("offYuan") or 10)
        except (TypeError, ValueError):
            th, off = 100.0, 10.0
        lines.append(f"  spend-discount-threshold-yuan: {th:g}")
        lines.append(f"  spend-discount-off-yuan: {off:g}")
    if "member_tier" in caps:
        lines.append("  member-tier-enabled: true")
    if "coupon" in caps:
        lines.append("  coupon-enabled: true")
    if "order_review" in caps:
        lines.append("  order-review-enabled: true")
    timeout = 0
    try:
        timeout = int((spec.get("schema") or {}).get("orderTimeoutMinutes") or 0)
    except (TypeError, ValueError):
        timeout = 0
    if timeout > 0:
        lines.append(f"  order-timeout-minutes: {timeout}")
    if "favorites" in caps:
        lines.append("  favorites-enabled: true")
    if "browse_history" in caps:
        lines.append("  browse-history-enabled: true")
    if "gallery" in caps:
        lines.append("  gallery-enabled: true")
    if "search_assist" in caps:
        lines.append("  search-assist-enabled: true")

    if "slot_reserve" in caps:
        st = runtime.get("slot_table") or "resource_slot"
        rt = runtime.get("reservation_table") or "reservation"
        lines.append("  # 时段预约")
        lines.append(f"  slot-table: {st}")
        lines.append(f"  reservation-table: {rt}")
        if resv_ent.get("requireRemark"):
            lines.append("  slot-require-remark: true")
        if resv_ent.get("requireConfirm"):
            lines.append("  slot-require-confirm: true")

    block = "\n".join(lines) + "\n"
    if re.search(r"(?m)^thesis:\s*$", text):
        return re.sub(r"(?ms)^thesis:\s*\n.*\Z", block, text, count=1)
    return text.rstrip() + "\n\n" + block


def _write_profile_fields_resource(dest: Path, schema: dict[str, Any]) -> None:
    """学生端后端读取，注册/资料必填校验。"""
    fields = schema.get("profileFields") or []
    path = dest / "backend" / "src" / "main" / "resources" / "domain-profile-fields.json"
    _write(path, json.dumps(fields, ensure_ascii=False, indent=2))


def _write_loyalty_resource(dest: Path, schema: dict[str, Any]) -> None:
    """学生端 LoyaltyStore 读取会员档等配置。"""
    loyalty = schema.get("loyalty") or {}
    path = dest / "backend" / "src" / "main" / "resources" / "domain-loyalty.json"
    _write(path, json.dumps(loyalty, ensure_ascii=False, indent=2))


def _write_ticket_copy_resource(dest: Path, schema: dict[str, Any]) -> None:
    """学生端 TicketStore 进度/提示文案：来自 schema.entities.ticket（及 archive 名）。"""
    from app.bake.ticket_copy_text import sibling_reject_tip, stock_unavailable_label

    ticket = ((schema.get("entities") or {}).get("ticket") or {}) if isinstance(schema, dict) else {}
    archive = ((schema.get("entities") or {}).get("archive") or {}) if isinstance(schema, dict) else {}
    apply_deadline_label = "报名截止"
    stock_label = "库存"
    for f in archive.get("fields") or []:
        if not isinstance(f, dict):
            continue
        key = f.get("key")
        lab = str(f.get("label") or "").strip()
        if key == "applyDeadlineAt" and lab:
            apply_deadline_label = lab
        if key == "stock" and lab:
            stock_label = lab
    verbs = ticket.get("verbs") if isinstance(ticket.get("verbs"), dict) else {}
    apply_verb = str(verbs.get("apply") or "")
    archive_label = str(archive.get("label") or "")
    stock_gone = archive.get("stockUnavailableLabel") or stock_unavailable_label(stock_label)
    payload = {
        "states": ticket.get("states") if isinstance(ticket.get("states"), dict) else {},
        "verbs": verbs,
        "checkinLabel": ticket.get("checkinLabel") or "签到",
        "finePaidLabel": ticket.get("finePaidLabel") or "费用已结清",
        "archiveLabel": archive_label,
        "applyDeadlineLabel": apply_deadline_label,
        "stockLabel": stock_label,
        "stockUnavailableLabel": stock_gone,
        "siblingRejectTip": sibling_reject_tip(archive_label, apply_verb),
    }
    path = dest / "backend" / "src" / "main" / "resources" / "domain-ticket-copy.json"
    _write(path, json.dumps(payload, ensure_ascii=False, indent=2))


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
    auth_entry_mode: str = "role_pick",
    auth_role_widget: str = "radio",
    chrome: str = "soft",
    seed: str = "",
) -> None:
    if not auth_hero:
        from app.bake.auth_hero import auth_hero_public_path

        auth_hero = auth_hero_public_path(dest)
    if portal_banners is None:
        from app.bake.portal_banners import portal_banners_from_workspace

        portal_banners = portal_banners_from_workspace(dest, schema)
    from app.bake.catalog import DOMAINS
    from app.bake.guest_cta import (
        GUEST_TEASER_LIMIT,
        pick_guest_login_cta,
        portal_guest_browse_enabled,
    )

    from app.bake.domain_skin import student_skin_payload

    domain_label = (DOMAINS.get(domain) or {}).get("label") or "通用"
    dom_meta = DOMAINS.get(domain) or {}
    guest_on = portal_guest_browse_enabled(domain, dom_meta)
    guest_cta = pick_guest_login_cta(domain, seed or dest.name or title)
    # 便于页面用 schemaLabels 读取
    labels = dict((schema.get("labels") or {}))
    if guest_on and guest_cta:
        labels["guestLoginCta"] = guest_cta
        schema = {**schema, "labels": labels}
    skin = student_skin_payload(domain, domain_label)
    payload = {
        "title": title,
        "theme": theme,
        "chrome": normalize_chrome(chrome),
        "flavor": skin["flavor"],
        "domainLabel": skin["domainLabel"],
        "traits": skin["traits"],
        "authTemplate": auth_tpl,
        "authEntryMode": normalize_auth_entry_mode(auth_entry_mode),
        "authRoleWidget": normalize_auth_role_widget(auth_role_widget),
        "authHero": auth_hero or "",
        "portalBanners": portal_banners or [],
        "portalGuestBrowse": guest_on,
        "guestTeaserLimit": GUEST_TEASER_LIMIT,
        "guestLoginCta": guest_cta if guest_on else "",
        "accept": accept or schema.get("accept") or "reject",
        "schema": schema,
    }
    delivered = dest / "frontend" / "src" / "appDelivered.js"
    # 兼容旧文件名（若存在则删掉，避免双份）
    legacy = dest / "frontend" / "src" / "factoryDelivered.js"
    if legacy.exists():
        legacy.unlink()
    delivered.write_text(
        "/**\n"
        " * 课题交付配置（文案 / 菜单 / 能力）。由生成写入，一般无需手改。\n"
        " */\n"
        f"export const APP_DELIVERED = {json.dumps(payload, ensure_ascii=False, indent=2)}\n",
        encoding="utf-8",
    )
    _write_profile_fields_resource(dest, schema)
    _write_loyalty_resource(dest, schema)
    _write_ticket_copy_resource(dest, schema)


def emit_schema_to_workspace(workspace: Path, spec: dict[str, Any]) -> list[str]:
    """把已合并的 schema 写入 islands / appDelivered / spec.json，并同步 thesis yml。"""
    merged = spec.get("schema") or {}
    ok, errors = validate_schema(merged)
    if not ok:
        raise RuntimeError("schema 校验失败: " + "; ".join(errors))
    written = write_schema_artifacts(workspace, merged)
    _write(workspace / "spec.json", json.dumps(spec, ensure_ascii=False, indent=2))
    auth_tpl = normalize_auth_template(spec.get("auth_template"))
    auth_entry = normalize_auth_entry_mode(spec.get("auth_entry_mode"))
    auth_widget = normalize_auth_role_widget(spec.get("auth_role_widget"))
    chrome = normalize_chrome(spec.get("chrome"))
    _write_factory_delivered(
        workspace,
        spec.get("title", "毕设系统"),
        spec.get("theme", "lib-ink"),
        auth_tpl,
        merged,
        spec.get("accept"),
        domain=spec.get("domain", "DOM-GENERIC"),
        auth_entry_mode=auth_entry,
        auth_role_widget=auth_widget,
        chrome=chrome,
        seed=workspace.name,
    )
    sync_workspace_thesis_yml(workspace, spec)
    return written


def sync_workspace_thesis_yml(workspace: Path, spec: dict[str, Any]) -> None:
    """与 bake 同一套 _patch_thesis_yml，避免只改 schema 导致 Java 默认值漂移。"""
    app_yml = workspace / "backend" / "src" / "main" / "resources" / "application.yml"
    if not app_yml.exists():
        return
    domain = str(spec.get("domain") or "DOM-GENERIC")
    text = app_yml.read_text(encoding="utf-8")
    app_yml.write_text(_patch_thesis_yml(text, domain, spec), encoding="utf-8")


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

