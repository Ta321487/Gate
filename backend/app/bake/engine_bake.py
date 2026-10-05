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
    normalize_portal_home_style,
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
        from app.services.projects import remove_tree_reliable
        from app.services.runtime import detach_frontend_deps

        # Windows：旧预览 JVM 常短时锁住 application.yml，裸 rmtree 会 WinError 32
        detach_frontend_deps(dest)
        remove_tree_reliable(dest)
    if not src.exists():
        raise FileNotFoundError(f"骨架不存在: {src}")
    # 骨架若残留 node_modules / target / dist，禁止整树拷进工作区：
    # Windows 上大目录 copytree 曾出现 backend 被拷成空壳，导致后续写 yml / AppPolicy 全灭。
    # 前端依赖由 prepare_frontend_deps 挂共享缓存；Maven target 由编译再生。
    def _bake_copy_ignore(directory: str, names: list[str]) -> set[str]:
        skip = {"node_modules", "target", "dist", ".vite"}
        return {n for n in names if n in skip}

    shutil.copytree(src, dest, ignore=_bake_copy_ignore)

    # 对账孤儿清盘每轮会扫 workspace/：bake 中必须挂牌，否则半截目录被掏空
    from app.services.project_disk import clear_bake_in_progress, mark_bake_in_progress

    mark_bake_in_progress(dest)
    try:
        return _bake_project_body(project_id, spec, db_name, dest)
    finally:
        clear_bake_in_progress(dest)


def _bake_project_body(
    project_id: str, spec: dict[str, Any], db_name: str, dest: Path
) -> Path:
    """bake_project 主体（已 copytree + 挂牌）。"""
    settings = get_settings()
    domain = spec.get("domain", "DOM-GENERIC")
    overlay = settings.skeletons_dir / "domains" / domain
    if overlay.exists():
        _merge_tree(overlay, dest)

    from app.bake.addons import apply_addons_overlays
    from app.bake.match_path_axes import match_path_override_scope
    from app.bake.persistence import apply_persistence_overlay

    apply_persistence_overlay(dest, spec, merge_tree=_merge_tree)
    apply_addons_overlays(dest, spec, merge_tree=_merge_tree)

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
    path = spec.get("match_path") if isinstance(spec.get("match_path"), dict) else {}
    with match_path_override_scope(
        str(spec.get("domain") or domain or ""),
        path.get("scene"),
        path.get("entry"),
    ):
        sql = domain_sql(
            domain,
            db_name,
            spec.get("archetype"),
            archetypes=spec.get("archetypes"),
            ticket_table=((spec.get("runtime") or {}).get("ticket_table")),
            capabilities=spec.get("capabilities"),
            proposal_text=proposal_for_sql,
            title=str(spec.get("title") or ""),
            ticket_flags=((spec.get("schema") or {}).get("entities") or {}).get("ticket"),
            staff_posts=staff_posts_pre,
            reservation_flags=((spec.get("schema") or {}).get("entities") or {}).get(
                "reservation"
            ),
        )
        from app.bake.gates.schema_nf import assert_schema_nf

        assert_schema_nf(sql)
        assert_table_budget(sql, domain, caps=list(spec.get("capabilities") or []))

        from app.bake.archive_seed_guard import assert_archive_demo_seed

        runtime = spec.get("runtime") if isinstance(spec.get("runtime"), dict) else {}
        gate = spec.get("gate") if isinstance(spec.get("gate"), dict) else {}
        assert_archive_demo_seed(
            sql,
            item_table=runtime.get("archive_item_table"),
            flow_api=gate.get("flow_api"),
            ticket_mode=runtime.get("ticket_mode"),
        )

        from app.bake.domain_schema import product_name_from_title
        from app.bake.identity_align import assert_identity_aligned
        from app.bake.menu_routes import assert_menu_routes_aligned

        title = spec.get("title", "毕设系统")
        schema = spec.get("schema") or {}
        # 身份/壳穿帮直接失败，禁止带病包出炉
        assert_identity_aligned(
            domain,
            title=str(title or ""),
            proposal_text=proposal_for_sql,
            sql=sql,
            schema=schema if isinstance(schema, dict) else None,
            profile_fields=(schema.get("profileFields") if isinstance(schema, dict) else None),
        )
        # 菜单 key 必须能落到本包有效路由，禁止导航 404
        from app.bake.domain_skin import traits_for_domain

        assert_menu_routes_aligned(
            schema if isinstance(schema, dict) else None,
            domain=domain,
            capabilities=list(spec.get("capabilities") or []),
            traits=dict(spec.get("traits") or traits_for_domain(domain)),
            proposal_text=proposal_for_sql,
        )
        from app.bake.skin_invariants import assert_skin_invariants

        assert_skin_invariants(
            schema if isinstance(schema, dict) else None,
            domain=domain,
            title=str(title or ""),
            proposal_text=proposal_for_sql,
            frontend_src=dest / "frontend" / "src",
        )
        # 论文用例图必有：生成期即校验，禁止缺图/坏关系（画法跟客户样式 / spec.usecase_style）
        from app.bake.schema.usecases import list_usecase_actors, usecase_model
        from app.bake.schema.usecase_style import resolve_usecase_style

        _sch = schema if isinstance(schema, dict) else {}
        _uc_style = resolve_usecase_style(spec=spec if isinstance(spec, dict) else None)
        for _a in list_usecase_actors(_sch):
            usecase_model(
                _sch,
                actor=_a["id"],
                proposal_text=proposal_for_sql,
                title_fallback=str(title or "管理系统"),
                style=_uc_style,
                spec=spec if isinstance(spec, dict) else None,
            )
    _write(dest / "sql" / "schema.sql", sql)

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
        # thesis 段重写后再次确保 persistence 块仍在（防旧正则误删；idempotent）
        pers = spec.get("persistence") or "jdbc"
        if pers == "mybatis":
            from app.bake.persistence import ensure_mybatis_application_yml

            ensure_mybatis_application_yml(dest)
        elif pers == "jpa":
            from app.bake.persistence import ensure_jpa_application_yml

            ensure_jpa_application_yml(dest)

    # 策略下沉：生成 TicketPolicy / AppPolicy（须在 java 包名 remap 之前，包名仍为 com.thesis）
    from app.bake.runtime_policy import write_policy as write_app_policy
    from app.bake.ticket_policy import write_policy as write_ticket_policy

    write_ticket_policy(dest, domain, spec)
    write_app_policy(dest, domain, spec)

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
    portal_home = normalize_portal_home_style(spec.get("portal_home_style"))
    theme = spec.get("theme", "lib-ink")
    env_fe.write_text(
        f"VITE_APP_TITLE={app_name}\n"
        f"VITE_THEME={theme}\n"
        f"VITE_CHROME={chrome}\n"
        f"VITE_LAYOUT={layout}\n"
        f"VITE_TYPEFACE={typeface}\n"
        f"VITE_PORTAL_HOME_STYLE={portal_home}\n"
        f"VITE_AUTH_TEMPLATE={auth_tpl}\n"
        f"VITE_AUTH_ENTRY_MODE={auth_entry}\n"
        f"VITE_AUTH_ROLE_WIDGET={auth_widget}\n",
        encoding="utf-8",
    )

    _patch_student_readme(
        dest,
        app_name=app_name,
        db_name=db_name,
        java_package=new_pkg,
        persistence=spec.get("persistence") or "jdbc",
        spring_security=bool(spec.get("spring_security")),
        ai_assistant=bool(spec.get("ai_assistant"))
        or "ai_assistant" in (spec.get("capabilities") or []),
        schema_sql=sql,
        spec=spec,
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
        auth_entry_mode=auth_entry,
        auth_role_widget=auth_widget,
        chrome=chrome,
        layout=layout,
        typeface=typeface,
        portal_home_style=portal_home,
        seed=dest.name,
    )

    # 保留 Home.vue：Vite 会静态分析同文件内所有 import()，删掉会导致报修壳也编译失败

    # 论文图默认视图预热落盘：打开 = 读 islands/diagram_cache
    try:
        from app.bake.schema.diagram_pack import warm_default_diagrams

        warm_default_diagrams(
            dest,
            title_fallback=str(spec.get("title") or title or "管理系统"),
            proposal_text="",
        )
    except Exception as e:
        import logging

        logging.getLogger("app.bake").warning("diagram warm skipped: %s", e)

    return dest

def _patch_thesis_yml(text: str, domain: str, spec: dict[str, Any]) -> str:
    """按本项目能力重写 thesis 段：只保留用到的键，去掉空开关。"""
    from app.bake.catalog import DOMAINS
    from app.bake.domains import DOMAIN_CAPABILITIES
    from app.bake.guest_cta import GUEST_TEASER_LIMIT, portal_guest_browse_enabled

    runtime = dict(spec.get("runtime") or {})
    if not runtime:
        runtime = dict((DOMAINS.get(domain) or {}).get("runtime") or {})
    roles = spec.get("roles") or (DOMAINS.get(domain) or {}).get("roles") or ["user", "admin"]
    register_role = runtime.get("register_role") or (roles[0] if roles else "user")
    caps = set(spec.get("capabilities") or DOMAIN_CAPABILITIES.get(domain) or [])
    # 单据参数/开关已下沉到生成的 TicketPolicy.java；yml 仅保留与订单共用的 use-quota
    use_quota = runtime.get("use_quota")
    if use_quota is None:
        use_quota = "quota" in caps
    enable_ticket = runtime.get("enable_ticket")
    if enable_ticket is None:
        enable_ticket = "ticket_flow" in caps

    resv_ent = ((spec.get("schema") or {}).get("entities") or {}).get("reservation") or {}
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

    # 与 domain.schema.json roles.allowAppointFromUsers 同真源；缺省按域规则重算并回写，避免 FE/yml 分叉
    appoint_ok = roles.get("allowAppointFromUsers")
    if not isinstance(appoint_ok, bool):
        prop_body = ""
        if isinstance(spec.get("proposal_text"), str):
            prop_body = spec["proposal_text"]
        appoint_ok = _allow_appoint(
            domain,
            spec.get("archetype"),
            spec.get("archetypes") if isinstance(spec.get("archetypes"), list) else None,
            proposal_text=prop_body,
            title=str(spec.get("title") or ""),
        )
        sch = spec.get("schema") if isinstance(spec.get("schema"), dict) else None
        if sch is not None:
            roles_w = dict(sch.get("roles") or {})
            roles_w["allowAppointFromUsers"] = bool(appoint_ok)
            sch["roles"] = roles_w
            spec["schema"] = sch
    lines.append("  # 是否允许从门户用户里任命岗位账号")
    lines.append(f"  allow-appoint-from-users: {'true' if appoint_ok else 'false'}")

    # 单据参数 → TicketPolicy；档案/订单/预约表位与非单据开关 → AppPolicy
    # yml 只保留启动期 / 门户 / 门禁 / 与订单共用的 use-quota（守卫勿放宽，防重复发键）
    if enable_ticket:
        lines.append(f"  use-quota: {'true' if use_quota else 'false'}")

    # archive / lookup / order 表位与多数能力开关已下沉到 AppPolicy（见 runtime_policy.py）
    if "order_lines" in caps:
        if use_quota and not enable_ticket:
            lines.append(f"  use-quota: {'true' if use_quota else 'false'}")

    loyalty = (spec.get("schema") or {}).get("loyalty") or {}
    if "points" in caps:
        pts = loyalty.get("points") if isinstance(loyalty.get("points"), dict) else {}
        # points-enabled / earn-per-yuan / pay-enabled → AppPolicy；其余积分子开关仍写 yml
        if pts.get("offsetEnabled"):
            lines.append("  points-offset-enabled: true")
        if pts.get("checkInEnabled"):
            lines.append("  points-checkin-enabled: true")
            try:
                cip = int(pts.get("checkInPoints") or 10)
            except (TypeError, ValueError):
                cip = 10
            lines.append(f"  points-checkin-amount: {cip}")
        if pts.get("expireEnabled"):
            lines.append("  points-expire-enabled: true")
            lines.append(f"  points-expire-period: {pts.get('expirePeriod') or 'year'}")
            lines.append(f"  points-expire-scope: {pts.get('expireScope') or 'all'}")
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
        mt = loyalty.get("memberTiers") if isinstance(loyalty.get("memberTiers"), dict) else {}
        basis = mt.get("basis") or "spend"
        lines.append(f"  member-tier-basis: {basis}")
    if "coupon" in caps:
        lines.append("  coupon-enabled: true")
    if "flash_price" in caps:
        lines.append("  flash-price-enabled: true")
    if "product_spec" in caps:
        lines.append("  product-spec-enabled: true")
    if "multi_category" in caps:
        lines.append("  multi-category-enabled: true")
        junc = runtime.get("archive_item_category_table") or "product_category"
        lines.append(f"  archive-item-category-table: {junc}")
    if "line_custom" in caps:
        lines.append("  line-custom-enabled: true")
        if (spec.get("schema") or {}).get("lineCustomPlaceConfirmed"):
            lines.append("  line-custom-place-confirmed: true")
    if "delivery_window" in caps:
        lines.append("  delivery-window-enabled: true")
    if "purchase_gate" in caps:
        lines.append("  purchase-gate-enabled: true")
    if "group_buy" in caps:
        lines.append("  group-buy-enabled: true")
    if "blind_box" in caps:
        lines.append("  blind-box-enabled: true")
    if "consign" in caps:
        lines.append("  consign-enabled: true")
    if "weigh_sale" in caps:
        lines.append("  weigh-sale-enabled: true")
    if "shoot" in caps:
        lines.append("  shoot-enabled: true")
    if "boarding" in caps:
        lines.append("  boarding-enabled: true")
    if "room_board" in caps:
        lines.append("  room-board-enabled: true")
    if "front_desk" in caps:
        lines.append("  front-desk-enabled: true")
    if "housekeeping" in caps:
        lines.append("  housekeeping-enabled: true")
    if "venue_clean" in caps:
        lines.append("  venue-clean-enabled: true")
    if "buyback" in caps:
        lines.append("  buyback-enabled: true")
    if "lesson_pack" in caps:
        lines.append("  lesson-pack-enabled: true")
    if "rental_bond" in caps:
        lines.append("  rental-bond-enabled: true")
    if "digital_goods" in caps:
        lines.append("  digital-goods-enabled: true")
    if (spec.get("schema") or {}).get("noCasualRefund") or "digital_goods" in caps:
        lines.append("  no-casual-refund: true")
    timeout = 0
    try:
        timeout = int((spec.get("schema") or {}).get("orderTimeoutMinutes") or 0)
    except (TypeError, ValueError):
        timeout = 0
    if timeout > 0:
        lines.append(f"  order-timeout-minutes: {timeout}")
    # favorites / dm-shop-cs / content-report / post-mute / parcel-shelf → AppPolicy
    if "post_like" in caps:
        lines.append("  post-like-enabled: true")
    if "book_suggest" in caps:
        lines.append("  book-suggest-enabled: true")
    if "parcel_ship" in caps:
        lines.append("  parcel-ship-enabled: true")
    if "book_lost" in caps:
        # allowBookLost 亦由 schema.ticket 写入 ticket-allow-book-lost
        pass
    if "audit_log" in caps:
        lines.append("  audit-log-enabled: true")
        # 仅写登录日志时补 login-only（此处必须在 audit_log 分支内，勿嵌进别的能力）
        if bool((spec.get("schema") or {}).get("auditLoginOnly")):
            lines.append("  audit-log-login-only: true")
    if "message_template" in caps:
        lines.append("  message-template-enabled: true")
    if "staff_roster" in caps:
        lines.append("  staff-roster-enabled: true")
    if "room_equipment" in caps:
        lines.append("  room-equipment-enabled: true")
    if "browse_history" in caps:
        lines.append("  browse-history-enabled: true")
    # archive-log-enabled → AppPolicy
    if "gallery" in caps:
        lines.append("  gallery-enabled: true")
    if "detail_attrs" in caps:
        lines.append("  detail-attrs-enabled: true")
        keys = (spec.get("schema") or {}).get("detailAttrKeys") or []
        if isinstance(keys, list) and keys:
            type_by_key: dict[str, str] = {}
            for field in (
                ((spec.get("schema") or {}).get("entities") or {}).get("archive") or {}
            ).get("fields") or []:
                if not isinstance(field, dict):
                    continue
                fk = str(field.get("key") or "")
                if fk:
                    type_by_key[fk] = str(field.get("type") or "string")
            parts: list[str] = []
            for raw in keys:
                k = str(raw)
                if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,31}", k):
                    continue
                ft = type_by_key.get(k, "string")
                if ft in ("number", "date"):
                    parts.append(f"{k}:{ft}")
                else:
                    parts.append(k)
            if parts:
                lines.append("  detail-attr-keys: " + ",".join(parts))
    if "search_assist" in caps:
        lines.append("  search-assist-enabled: true")
    if "exam" in caps:
        # exam-enabled → AppPolicy；子开关与门禁仍写 yml
        exam_opts = (spec.get("schema") or {}).get("examOpts") or {}
        if not isinstance(exam_opts, dict):
            exam_opts = {}
        # 兼容实体内 opts
        if not exam_opts:
            ent = ((spec.get("schema") or {}).get("entities") or {}).get("exam") or {}
            raw = ent.get("opts") if isinstance(ent, dict) else {}
            if isinstance(raw, dict):
                exam_opts = {
                    "practice": bool(raw.get("practice")),
                    "explain": bool(raw.get("explain")),
                    "timer": bool(raw.get("timer")),
                    "attempt_limit": bool(raw.get("attemptLimit") or raw.get("attempt_limit")),
                    "rank": bool(raw.get("rank")),
                    "wrongbook": bool(raw.get("wrongbook")),
                }
        flag_pairs = (
            ("exam-practice-enabled", "practice"),
            ("exam-explain-enabled", "explain"),
            ("exam-timer-enabled", "timer"),
            ("exam-attempt-limit-enabled", "attempt_limit"),
            ("exam-rank-enabled", "rank"),
            ("exam-wrongbook-enabled", "wrongbook"),
        )
        for yml_key, opt_key in flag_pairs:
            if exam_opts.get(opt_key):
                lines.append(f"  {yml_key}: true")
        sch = spec.get("schema") or {}
        gate_on = bool(sch.get("examGateTicket"))
        if not gate_on:
            t_ent = (sch.get("entities") or {}).get("ticket") or {}
            gate_on = bool(isinstance(t_ent, dict) and t_ent.get("requireExamPass"))
        if gate_on:
            lines.append("  exam-require-before-ticket: true")
    # survey / vote / doclib / timebank / seat-select / stock-io / e-sign /
    # balance-ledger / grade-scores / occupy-span / material-check / claim-proof /
    # lost-clue → AppPolicy
    if "stock_scrap" in caps:
        lines.append("  stock-scrap-enabled: true")
        scrap_opts = (spec.get("schema") or {}).get("stockScrapOpts") or {}
        if isinstance(scrap_opts, dict) and scrap_opts.get("approveFlow"):
            lines.append("  stock-scrap-approve-flow: true")
    if "stock_count" in caps:
        lines.append("  stock-count-enabled: true")
        opts = (spec.get("schema") or {}).get("stockCountOpts") or {}
        if isinstance(opts, dict):
            if opts.get("countLock"):
                lines.append("  stock-count-lock: true")
            if opts.get("blindCount"):
                lines.append("  stock-blind-count: true")
            if opts.get("requireDiffReason"):
                lines.append("  stock-require-diff-reason: true")

    if "slot_reserve" in caps:
        # slot-table / reservation-table → AppPolicy；预约侧开关仍写 yml
        if resv_ent.get("requireRemark"):
            lines.append("  slot-require-remark: true")
        if resv_ent.get("requireConfirm"):
            lines.append("  slot-require-confirm: true")
        if resv_ent.get("allowRating"):
            lines.append("  slot-allow-rating: true")

    block = "\n".join(lines) + "\n"
    if re.search(r"(?m)^thesis:\s*$", text):
        # 段前注释统一成学生口吻；只替换 thesis 缩进行，保留其后 mybatis 等顶层配置
        text = re.sub(
            r"(?m)^(?:#.*\n)*thesis:\s*$",
            "# 课题业务配置（按本系统启用的功能填写）\nthesis:",
            text,
            count=1,
        )
        return re.sub(r"(?ms)^thesis:\s*\n(?:[ \t].*\n?)*", block, text, count=1)
    return text.rstrip() + "\n\n" + block

