"""engine_bake.py"""

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
    normalize_layout,
    normalize_typeface,
)
from app.bake.domain_schema import (
    deterministic_llm_patch,
    merge_schema,
    product_name_from_title,
    validate_schema,
    write_schema_artifacts,
)

# 答辩/开题常见硬约束：交付库表不宜过少或灌水过多
from app.bake.engine_resources import (  # noqa: F401
    _write_archive_columns_resource,
    _write_factory_delivered,
    _write_loyalty_resource,
    _write_profile_fields_resource,
    _write_ticket_columns_resource,
    _write_ticket_copy_resource,
)
from app.bake.engine_sql import (  # noqa: F401
    TABLE_COUNT_MAX,
    TABLE_COUNT_MIN,
    _SQL_DIR,
    _FALLBACK_SQL,
    _load_named_domain_sql,
    _merge_tree,
    _patch_student_readme,
    _sql_template_path,
    _write,
    assert_table_budget,
    count_create_tables,
    domain_sql,
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
    schema_pre = spec.get("schema") if isinstance(spec.get("schema"), dict) else {}
    roles_pre = schema_pre.get("roles") if isinstance(schema_pre.get("roles"), dict) else {}
    staff_posts_pre = roles_pre.get("staff_posts") if isinstance(roles_pre.get("staff_posts"), list) else None
    proposal_for_sql = str(spec.get("proposal_text") or "").strip()
    if not proposal_for_sql:
        prop = spec.get("proposal")
        if isinstance(prop, dict):
            proposal_for_sql = str(
                prop.get("excerpt")
                or prop.get("text")
                or prop.get("summary")
                or prop.get("background")
                or ""
            ).strip()
        elif isinstance(prop, str):
            proposal_for_sql = prop.strip()
    if not proposal_for_sql:
        proposal_for_sql = str(spec.get("title") or "")
    sql = domain_sql(
        domain,
        db_name,
        spec.get("archetype"),
        archetypes=spec.get("archetypes"),
        ticket_table=((spec.get("runtime") or {}).get("ticket_table")),
        capabilities=spec.get("capabilities"),
        proposal_text=proposal_for_sql,
        ticket_flags=((spec.get("schema") or {}).get("entities") or {}).get("ticket"),
        staff_posts=staff_posts_pre,
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

    from app.bake.api_style import apply_api_style_to_workspace, normalize_api_style

    apply_api_style_to_workspace(dest, normalize_api_style(spec.get("api_style")))

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
    layout = normalize_layout(spec.get("layout"))
    typeface = normalize_typeface(spec.get("typeface"))
    theme = spec.get("theme", "lib-ink")
    env_fe.write_text(
        f"VITE_APP_TITLE={app_name}\n"
        f"VITE_THEME={theme}\n"
        f"VITE_CHROME={chrome}\n"
        f"VITE_LAYOUT={layout}\n"
        f"VITE_TYPEFACE={typeface}\n"
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
        layout=layout,
        typeface=typeface,
        seed=dest.name,
    )

    # 保留 Home.vue：Vite 会静态分析同文件内所有 import()，删掉会导致报修壳也编译失败
    return dest

def _patch_thesis_yml(text: str, domain: str, spec: dict[str, Any]) -> str:
    """按本项目能力重写 thesis 段：只保留用到的键，去掉空开关与工厂话术。"""
    from app.bake.catalog import DOMAINS
    from app.bake.domains import DOMAIN_CAPABILITIES
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
            ("ticket-auto-approve", bool(ticket_ent.get("autoApprove"))),
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
        if archive_ent.get("userPublish"):
            lines.append("  archive-user-publish: true")
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
    if "archive_log" in caps:
        lines.append("  archive-log-enabled: true")
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

