"""Bake：SQL 装载与表数量门禁。"""

from __future__ import annotations

import json
import logging
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

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
TABLE_COUNT_MIN = 6
# 舒适区上沿。超过只警告，不拦出包（含 L0 平台表 sys_message）
TABLE_COUNT_MAX = 15
# 超过此数打回。选题必需业务表不计入这一档（见 ESSENTIAL_CAP_TABLES）
TABLE_COUNT_HARD = 18
# 借用族（BORROW_FAMILY_DOMAINS，与级联展示分组无关）：薄壳 6～7 张不够答辩，族内下限 10
BORROW_TABLE_MIN = 10

# 开题扫入后才会有的业务表。缺了论文主路径或答辩场景会变浅，故不计入「超过 18 打回」。
# 已写进该域 DOMAIN_CAPABILITIES 的默认能力不算：那是域壳本身，仍占预算。
ESSENTIAL_CAP_TABLES: dict[str, frozenset[str]] = {
    "wallet": frozenset({"user_ledger"}),
    "coupon": frozenset({"promo_coupon", "user_coupon"}),
    "guestbook": frozenset({"sys_guestbook"}),
    "dm": frozenset({"sys_dm_message"}),
    "item_comment": frozenset({"item_comment"}),
    "ai_assistant": frozenset({"sys_ai_knowledge", "sys_ai_message", "sys_ai_feedback"}),
    "exam": frozenset({
        "exam_question", "exam_paper", "exam_paper_question",
        "exam_attempt", "exam_answer", "exam_wrongbook",
    }),
    "vote": frozenset({"vote_campaign", "vote_candidate", "vote_ballot"}),
    "favorites": frozenset({"user_favorite"}),
    "post_like": frozenset({"user_post_like"}),
    "content_report": frozenset({"content_report"}),
    "staff_roster": frozenset({"staff_roster"}),
    "message_template": frozenset({"sys_message_template"}),
    "book_suggest": frozenset({"book_suggest"}),
    "audit_log": frozenset({"sys_audit_log"}),
    "browse_history": frozenset({"user_browse_history"}),
    "archive_log": frozenset({"archive_log"}),
    "room_equipment": frozenset({"sys_equipment_dict"}),
    "line_custom": frozenset({"line_spec_option"}),
    "delivery_window": frozenset({"delivery_slot", "price_span"}),
    "purchase_gate": frozenset({"purchase_permit"}),
    "group_buy": frozenset({"group_campaign", "group_member"}),
    "blind_box": frozenset({"blind_pool", "blind_pity"}),
    "consign": frozenset({"consign_item", "consign_ledger"}),
    "weigh_sale": frozenset({"loss_policy", "loss_claim"}),
    "shoot": frozenset({"service_bundle", "deliverable"}),
    "boarding": frozenset({"stay_log"}),
    "room_board": frozenset({"room_instance", "room_status_log"}),
    "front_desk": frozenset({"checkin", "checkout", "consumption"}),
    "digital_goods": frozenset({"digital_code", "digital_delivery"}),
    "buyback": frozenset({"buyback_slot", "buyback_order"}),
    "lesson_pack": frozenset({"lesson_pack", "lesson_wallet"}),
    "order_review": frozenset({"order_review"}),
    "stock_io": frozenset({"stock_move"}),
    "e_sign": frozenset({"e_sign_record"}),
    "balance_ledger": frozenset({"balance_subject", "balance_account", "balance_ledger"}),
    "occupy_span": frozenset({"resource_occupy", "occupy_block", "occupy_day_stat"}),
    "material_check": frozenset({"material_checklist", "ticket_material", "material_template"}),
    "loan_renew": frozenset({"renew_log", "fine_record"}),
}

_CREATE_TABLE_NAME = re.compile(
    r"(?i)create\s+table(?:\s+if\s+not\s+exists)?\s+`?([A-Za-z_][A-Za-z0-9_]*)`?"
)

# GENERIC 壳：bake/sql/DOM-GENERIC*.sql；具名域：sql_domain_templates（唯一路径，无散文件）
_SQL_DIR = Path(__file__).resolve().parent / "sql"
_FALLBACK_SQL = "DOM-GENERIC.sql"

def count_create_tables(sql: str) -> int:
    return len(re.findall(r"(?i)create\s+table\b", sql))


def list_create_table_names(sql: str) -> list[str]:
    """按出现顺序返回 CREATE TABLE 名（小写）。"""
    return [m.group(1).lower() for m in _CREATE_TABLE_NAME.finditer(sql or "")]


def table_budget_floor(domain: str) -> int:
    from app.bake.domains import is_borrow_family_domain

    return BORROW_TABLE_MIN if is_borrow_family_domain(domain) else TABLE_COUNT_MIN


def table_budget_bounds(
    domain: str, caps: list[str] | None = None
) -> tuple[int, int]:
    """舒适区上下限：全厂 6～15；借用/占用族 10～15。

    ``caps`` 保留兼容调用方；硬顶与选题例外见 ``evaluate_table_budget``。
    """
    del caps  # 硬顶/例外不再用 caps 抬高舒适区
    return table_budget_floor(domain), TABLE_COUNT_MAX


def _domain_default_caps(domain: str) -> set[str]:
    from app.bake.domains import DOMAIN_CAPABILITIES

    return {str(c) for c in (DOMAIN_CAPABILITIES.get(domain or "") or [])}


def essential_scanned_tables(
    domain: str, caps: list[str] | None, sql: str
) -> frozenset[str]:
    """开题扫入（非域默认）能力对应、且 SQL 里确实存在的表名。"""
    present = set(list_create_table_names(sql))
    defaults = _domain_default_caps(domain)
    out: set[str] = set()
    for cap in caps or []:
        c = str(cap)
        if c in defaults:
            continue
        for t in ESSENTIAL_CAP_TABLES.get(c, ()):
            if t.lower() in present:
                out.add(t.lower())
    return frozenset(out)


@dataclass(frozen=True)
class TableBudgetResult:
    count: int
    floor: int
    soft_max: int
    hard_max: int
    charged: int
    essential_tables: tuple[str, ...]
    ok: bool
    warn: bool
    message: str


def evaluate_table_budget(
    sql: str, domain: str, caps: list[str] | None = None
) -> TableBudgetResult:
    """表预算：低于下限打回；超过 soft_max 警告；超过 hard_max 打回。

    选题扫入的必需业务表不计入 hard 档（仍计 soft 警告）。
    """
    names = list_create_table_names(sql)
    n = len(names)
    lo = table_budget_floor(domain)
    soft = TABLE_COUNT_MAX
    hard = TABLE_COUNT_HARD
    essential = essential_scanned_tables(domain, caps, sql)
    charged = max(0, n - len(essential))

    if n < lo:
        return TableBudgetResult(
            count=n,
            floor=lo,
            soft_max=soft,
            hard_max=hard,
            charged=charged,
            essential_tables=tuple(sorted(essential)),
            ok=False,
            warn=False,
            message=f"{domain} schema 表数量={n}，低于下限 {lo}",
        )
    if charged > hard:
        ess = "、".join(sorted(essential)) or "无"
        return TableBudgetResult(
            count=n,
            floor=lo,
            soft_max=soft,
            hard_max=hard,
            charged=charged,
            essential_tables=tuple(sorted(essential)),
            ok=False,
            warn=False,
            message=(
                f"{domain} schema 表数量={n}（计费 {charged}，"
                f"选题必需表 {ess}），超过硬顶 {hard}"
            ),
        )
    warn = n > soft
    if warn:
        ess = "、".join(sorted(essential))
        tip = f"；选题必需表 {ess} 未计入硬顶" if ess else ""
        msg = f"当前 {n} 张，超过舒适区 {soft}{tip}"
    else:
        msg = f"当前 {n} 张"
    return TableBudgetResult(
        count=n,
        floor=lo,
        soft_max=soft,
        hard_max=hard,
        charged=charged,
        essential_tables=tuple(sorted(essential)),
        ok=True,
        warn=warn,
        message=msg,
    )


def assert_table_budget(
    sql: str, domain: str, caps: list[str] | None = None
) -> TableBudgetResult:
    """硬失败抛 ValueError；超过舒适区只打日志警告。"""
    result = evaluate_table_budget(sql, domain, caps)
    if not result.ok:
        raise ValueError(result.message)
    if result.warn:
        log.warning("%s", result.message)
    return result

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def _demo_portal_from_sql(sql: str) -> tuple[str, str]:
    """从 schema.sql 种子行解析门户样例账号（用户名、密码）。"""
    for uname in ("student", "reader", "patient", "buyer", "user"):
        pwd = f"{uname}123"
        # ('student', 'student123', 'student' …) 或仅用户名+密码
        if f"('{uname}', '{pwd}'" in sql:
            return uname, pwd
    return "user", "user123"


def _demo_portal_desc(spec: dict[str, Any] | None, username: str) -> str:
    """门户账号说明：优先 schema.roles.user.label。"""
    schema = (spec or {}).get("schema") if isinstance((spec or {}).get("schema"), dict) else {}
    roles = schema.get("roles") if isinstance(schema.get("roles"), dict) else {}
    user_slot = roles.get("user") if isinstance(roles.get("user"), dict) else {}
    label = str(user_slot.get("label") or "").strip()
    if label:
        return f"{label}（门户用户）：发起/办理本人侧业务"
    fallback = {
        "student": "学生（门户用户）：发起/办理本人侧业务",
        "reader": "读者（门户用户）：发起/办理本人侧业务",
        "patient": "患者（门户用户）：发起/办理本人侧业务",
        "buyer": "买家（门户用户）：发起/办理本人侧业务",
    }
    return fallback.get(username, "普通用户（门户）：发起/办理本人侧业务")


def _patch_student_readme(
    dest: Path,
    *,
    app_name: str,
    db_name: str,
    java_package: str = "com.thesis",
    persistence: str = "jdbc",
    spring_security: bool = False,
    ai_assistant: bool = False,
    schema_sql: str = "",
    spec: dict[str, Any] | None = None,
) -> None:
    """ZIP 根目录 README：写入课题名、库名、Java 包、持久层/鉴权与样例账号。"""
    from app.bake.addons import ai_assistant_readme_bits, security_readme_bits
    from app.bake.persistence import persistence_readme_bits

    path = dest / "README.md"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    text = text.replace("${APP_NAME}", app_name or "毕设系统")
    text = text.replace("${DB_NAME}", db_name or "thesis_app")
    text = text.replace("${JAVA_PACKAGE_PATH}", java_package.replace(".", "/"))
    text = text.replace("${JAVA_PACKAGE}", java_package)
    portal_user, portal_pass = _demo_portal_from_sql(schema_sql or "")
    text = text.replace("${DEMO_PORTAL_USER}", portal_user)
    text = text.replace("${DEMO_PORTAL_PASS}", portal_pass)
    text = text.replace(
        "${DEMO_PORTAL_DESC}",
        _demo_portal_desc(spec, portal_user),
    )
    backend_cell, note, store_line, faq = persistence_readme_bits(persistence)
    backend_cell, auth_line, sec_faq = security_readme_bits(spring_security, backend_cell)
    text = text.replace("${PERSISTENCE_BACKEND}", backend_cell)
    text = text.replace("${PERSISTENCE_NOTE}", note)
    text = text.replace("${PERSISTENCE_STORE_LINE}", store_line)
    text = text.replace("${PERSISTENCE_FAQ}", faq)
    text = text.replace("${SECURITY_AUTH_LINE}", auth_line)
    text = text.replace("${SECURITY_FAQ}", sec_faq)
    text = text.replace("${AI_ASSISTANT_FAQ}", ai_assistant_readme_bits(ai_assistant))
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
    """具名域唯一路径：见 sql.compose.compose_named_domain_sql。"""
    from app.bake.sql.compose import compose_named_domain_sql

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
    title: str = "",
    ticket_flags: dict | None = None,
    staff_posts: list | None = None,
    reservation_flags: dict | None = None,
) -> str:
    """按领域加载 SQL；GENERIC 多主路径从已有模板拼装。"""
    if domain == "DOM-GENERIC":
        from app.bake.archetype_shells import path_flags, shell_sql_filename
        from app.bake.sql.compose import compose_generic_sql

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
    from app.bake.sql.domain_scene_seed import apply_domain_scene_seed

    text = apply_domain_scene_seed(
        domain,
        text,
        title=title or "",
        proposal_text=proposal_text or "",
    )
    from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
    from app.bake.features.dm import DM_CAP
    from app.bake.features.favorites import (
        CONTENT_REPORT_CAP,
        FAVORITES_CAP,
        POST_LIKE_CAP,
    )
    from app.bake.features.audit_log import AUDIT_LOG_CAP
    from app.bake.features.message_template import MESSAGE_TEMPLATE_CAP
    from app.bake.features.staff_roster import STAFF_ROSTER_CAP
    from app.bake.features.room_equipment import ROOM_EQUIPMENT_CAP
    from app.bake.features.book_suggest import BOOK_SUGGEST_CAP
    from app.bake.features.product_spec import PRODUCT_SPEC_CAP
    from app.bake.features.multi_category import (
        MULTI_CATEGORY_CAP,
        multi_category_axis_seed_sql,
        parse_category_axes,
    )
    from app.bake.features.detail_attrs import DETAIL_ATTRS_CAP
    from app.bake.features.product_tags import PRODUCT_TAGS_CAP
    from app.bake.features.line_custom import (
        LINE_CUSTOM_CAP,
        line_custom_wants_spec,
        merge_line_custom_capabilities,
    )
    from app.bake.features.delivery_window import (
        DELIVERY_WINDOW_CAP,
        merge_delivery_window_capabilities,
    )
    from app.bake.features.purchase_gate import (
        PURCHASE_GATE_CAP,
        merge_purchase_gate_capabilities,
    )
    from app.bake.features.group_buy import (
        GROUP_BUY_CAP,
        merge_group_buy_capabilities,
    )
    from app.bake.features.blind_box import (
        BLIND_BOX_CAP,
        merge_blind_box_capabilities,
    )
    from app.bake.features.exam import (
        EXAM_CAP,
        apply_exam_skin_sql,
        scan_exam_gate_ticket,
        scan_exam_opts,
        scan_exam_skin,
    )
    from app.bake.features.vote import VOTE_CAP
    from app.bake.features.guestbook import GUESTBOOK_CAP
    from app.bake.features.item_comment import ITEM_COMMENT_CAP
    from app.bake.features.ai_assistant import AI_ASSISTANT_CAP
    from app.bake.features.ux_scan import BROWSE_HISTORY_CAP, GALLERY_CAP
    from app.bake.features.archive_log import ARCHIVE_LOG_CAP
    from app.bake.features.order_extras import FLASH_PRICE_CAP, ORDER_REVIEW_CAP
    from app.bake.features.loyalty import LOYALTY_CAPS
    from app.bake.features.proposal_caps import merge_proposal_capabilities
    from app.bake.archive_columns import apply_archive_semantic_columns
    from app.bake.ticket_columns import apply_ticket_shell_sql
    from app.bake.sql.fragments import (
        ensure_archive_flag_columns,
        ensure_flash_price_columns,
        ensure_product_spec_columns,
        ensure_multi_category_sql,
        ensure_product_tags_sql,
        ensure_order_line_custom_columns,
        ensure_delivery_window_sql,
        ensure_purchase_gate_sql,
        ensure_group_buy_sql,
        ensure_blind_box_sql,
        ensure_consign_sql,
        ensure_weigh_sale_sql,
        ensure_shoot_sql,
        ensure_boarding_sql,
        ensure_room_board_sql,
        ensure_front_desk_sql,
        ensure_venue_clean_sql,
        ensure_buyback_sql,
        ensure_lesson_pack_sql,
        ensure_rental_bond_sql,
        ensure_digital_goods_sql,
        ensure_archive_log_sql,
        ensure_browse_history_sql,
        ensure_coupon_lifecycle_sql,
        ensure_dm_sql,
        ensure_exam_core_sql,
        ensure_exam_wrongbook_sql,
        ensure_vote_sql,
        ensure_favorites_sql,
        ensure_post_like_sql,
        ensure_content_report_sql,
        ensure_audit_log_sql,
        ensure_message_template_sql,
        ensure_staff_roster_sql,
        ensure_room_equipment_sql,
        ensure_book_suggest_sql,
        ensure_gallery_sql,
        ensure_detail_attrs_sql,
        ensure_guestbook_sql,
        ensure_item_comment_sql,
        ensure_soft_delete_columns,
        ensure_notice_pinned_column,
        ensure_ai_assistant_sql,
        ensure_order_review_sql,
        ensure_shared_sql_columns,
        ensure_stock_io_sql,
        ensure_e_sign_sql,
        ensure_balance_ledger_sql,
        ensure_occupy_span_sql,
        ensure_material_check_sql,
        ensure_borrow_structural_sql,
        ensure_ticket_extra_sql,
        ensure_ticket_progress_sql,
        resolve_ticket_flags,
    )
    from app.bake.features.stock_io import STOCK_IO_CAP
    from app.bake.features.e_sign import E_SIGN_CAP
    from app.bake.features.core_cap_scan import OCCUPY_SPAN_CAP
    from app.bake.features.timebank import BALANCE_LEDGER_CAP
    from app.bake.features.ticket_flow_opts import MATERIAL_CHECK_CAP
    from app.bake.features.lostfound import (
        CLAIM_PROOF_CAP,
        LOST_CLUE_CAP,
        ensure_lostfound_sql,
    )
    from app.bake.staff_posts import append_staff_seed_sql

    arches_for_sql = list(
        archetypes or ([archetype] if archetype else [])
    )
    # 与 attach_accept 同一条能力合并链（避免 schema/SQL 双轨）
    caps = merge_proposal_capabilities(
        capabilities
        if capabilities is not None
        else (DOMAIN_CAPABILITIES.get(domain) or []),
        proposal_text or "",
        domain=domain,
        archetype=archetype,
        archetypes=arches_for_sql,
        title=title or "",
    )
    loyalty_on = bool(set(caps) & set(LOYALTY_CAPS))
    # 预约评价开关：优先 bake 传入；否则回落域默认 schema
    resv_flags: dict = {}
    if isinstance(reservation_flags, dict) and reservation_flags:
        resv_flags = reservation_flags
    else:
        try:
            from app.bake.schema.templates import SCHEMA_BUILDERS

            b = SCHEMA_BUILDERS.get(domain or "")
            if b:
                ent = ((b("thesis").get("entities") or {}).get("reservation") or {})
                if isinstance(ent, dict):
                    resv_flags = ent
        except Exception:
            pass
    # 有子管/岗位任命的域保留 staff 列；预约/订单履约列按域拆分；忠诚度按能力
    text = ensure_shared_sql_columns(
        text,
        domain=domain or "",
        archetypes=arches_for_sql,
        staff=True,
        loyalty=loyalty_on,
        reservation_flags=resv_flags,
    )
    runtime = ((DOMAINS.get(domain) or {}).get("runtime") or {})
    resolved_ticket = ticket_table or runtime.get("ticket_table")
    resolved_item = runtime.get("archive_item_table")
    if domain == "DOM-GENERIC" and (not resolved_ticket or not resolved_item):
        from app.bake.archetype_shells import shell_runtime

        shell_rt = shell_runtime(archetype, archetypes=archetypes) or {}
        if not resolved_ticket:
            resolved_ticket = shell_rt.get("ticket_table")
        if not resolved_item:
            resolved_item = shell_rt.get("archive_item_table") or "biz_item"
    flags = resolve_ticket_flags(
        domain or "",
        archetype=archetype,
        archetypes=archetypes,
        ticket_flags=ticket_flags,
    )
    from app.bake.features.core_cap_scan import (
        TIME_CONFLICT_CAP,
        enrich_loan_deadline_flags,
    )
    from app.bake.features.ticket_flow_opts import (
        enrich_ticket_flags_from_proposal,
        scan_apply_deadline,
    )

    flags = enrich_ticket_flags_from_proposal(flags, proposal_text or "")
    flags = enrich_loan_deadline_flags(
        flags,
        proposal_text or "",
        capabilities=caps,
    )
    text = ensure_ticket_extra_sql(
        text,
        domain=domain or "",
        ticket_table=resolved_ticket,
        ticket_flags=flags,
    )
    text = apply_ticket_shell_sql(
        text,
        domain=domain or "",
        ticket_table=resolved_ticket,
        ticket_flags=flags,
    )
    user_publish = False
    shop_marketplace = False
    soft_delete = False
    try:
        from app.bake.schema.templates import SCHEMA_BUILDERS

        builder = SCHEMA_BUILDERS.get(domain or "")
        if builder:
            built = builder(title or "thesis", proposal_text or "")
            arch = ((built.get("entities") or {}).get("archive") or {})
            user_publish = bool(arch.get("userPublish"))
            soft_delete = bool(arch.get("softDelete"))
            shop_marketplace = bool(built.get("shopMarketplace"))
    except Exception:
        user_publish = False
        shop_marketplace = False
        soft_delete = False
    if not shop_marketplace and (domain or "") == "DOM-SHOP":
        from app.bake.scene_scan import scan_shop_marketplace

        shop_marketplace = scan_shop_marketplace(title or "", proposal_text or "")
    text = ensure_archive_flag_columns(
        text,
        item_table=resolved_item,
        allow_checkin=bool(flags.get("allowCheckin")),
        peer_accept=bool(flags.get("peerAccept")),
        user_publish=user_publish,
        shop_marketplace=shop_marketplace,
        check_mutex=bool(flags.get("checkMutex")),
        apply_deadline=scan_apply_deadline(proposal_text or ""),
        schedule=TIME_CONFLICT_CAP in caps or bool(flags.get("allowCheckin")),
    )
    text = ensure_soft_delete_columns(
        text,
        enabled=soft_delete,
        item_table=resolved_item,
    )
    text = ensure_flash_price_columns(
        text,
        enabled=FLASH_PRICE_CAP in caps,
        item_table=resolved_item,
    )
    text = apply_archive_semantic_columns(
        text,
        domain=domain or "",
        item_table=resolved_item,
        archetypes=arches_for_sql,
    )
    text = ensure_product_spec_columns(
        text,
        enabled=PRODUCT_SPEC_CAP in caps,
        item_table=resolved_item,
    )
    axis_seed = ""
    if MULTI_CATEGORY_CAP in caps:
        axis_seed = multi_category_axis_seed_sql(
            parse_category_axes(proposal_text or "", title or ""),
            resolved_item or "product",
            "product_category",
        )
    text = ensure_multi_category_sql(
        text,
        enabled=MULTI_CATEGORY_CAP in caps,
        item_table=resolved_item,
        junction_table="product_category",
        axis_seed_sql=axis_seed,
    )
    text = ensure_product_tags_sql(
        text,
        enabled=PRODUCT_TAGS_CAP in caps,
    )
    caps = merge_line_custom_capabilities(
        caps,
        f"{title or ''}\n{proposal_text or ''}",
        domain=domain,
    )
    text = ensure_order_line_custom_columns(
        text,
        enabled=LINE_CUSTOM_CAP in caps,
        with_spec=line_custom_wants_spec(proposal_text or "", title or ""),
    )
    caps = merge_delivery_window_capabilities(
        caps,
        proposal_text or "",
        domain=domain,
        title=title or "",
    )
    text = ensure_delivery_window_sql(
        text,
        enabled=DELIVERY_WINDOW_CAP in caps,
    )
    caps = merge_purchase_gate_capabilities(
        caps,
        proposal_text or "",
        domain=domain,
        title=title or "",
    )
    text = ensure_purchase_gate_sql(
        text,
        enabled=PURCHASE_GATE_CAP in caps,
        item_table=resolved_item,
    )
    caps = merge_group_buy_capabilities(
        caps,
        proposal_text or "",
        domain=domain,
        title=title or "",
    )
    text = ensure_group_buy_sql(
        text,
        enabled=GROUP_BUY_CAP in caps,
    )
    caps = merge_blind_box_capabilities(
        caps,
        proposal_text or "",
        domain=domain,
        title=title or "",
    )
    text = ensure_blind_box_sql(
        text,
        enabled=BLIND_BOX_CAP in caps,
        item_table=resolved_item,
    )
    from app.bake.features.consign import CONSIGN_CAP, merge_consign_capabilities

    caps = merge_consign_capabilities(
        caps,
        proposal_text or "",
        domain=domain,
        title=title or "",
    )
    text = ensure_consign_sql(
        text,
        enabled=CONSIGN_CAP in caps,
        item_table=resolved_item,
    )
    from app.bake.features.weigh_sale import WEIGH_SALE_CAP, merge_weigh_sale_capabilities

    caps = merge_weigh_sale_capabilities(
        caps,
        proposal_text or "",
        domain=domain,
        title=title or "",
    )
    if WEIGH_SALE_CAP in caps:
        text = ensure_delivery_window_sql(text, enabled=True)
    text = ensure_weigh_sale_sql(
        text,
        enabled=WEIGH_SALE_CAP in caps,
        item_table=resolved_item,
    )
    from app.bake.features.shoot import SHOOT_CAP, merge_shoot_capabilities

    caps = merge_shoot_capabilities(
        caps,
        proposal_text or "",
        domain=domain,
        title=title or "",
    )
    text = ensure_shoot_sql(text, enabled=SHOOT_CAP in caps)
    from app.bake.features.boarding import BOARDING_CAP, merge_boarding_capabilities

    caps = merge_boarding_capabilities(
        caps,
        proposal_text or "",
        domain=domain,
        title=title or "",
    )
    text = ensure_boarding_sql(text, enabled=BOARDING_CAP in caps)
    from app.bake.features.room_board import ROOM_BOARD_CAP, merge_room_board_capabilities

    caps = merge_room_board_capabilities(
        caps,
        proposal_text or "",
        domain=domain,
        title=title or "",
    )
    from app.bake.features.front_desk import FRONT_DESK_CAP, merge_front_desk_capabilities

    caps = merge_front_desk_capabilities(
        caps,
        proposal_text or "",
        domain=domain,
        title=title or "",
    )
    from app.bake.features.housekeeping_cap import (
        HOUSEKEEPING_CAP,
        merge_housekeeping_capabilities,
    )

    caps = merge_housekeeping_capabilities(
        caps,
        proposal_text or "",
        domain=domain,
        title=title or "",
    )
    text = ensure_room_board_sql(text, enabled=ROOM_BOARD_CAP in caps)
    text = ensure_front_desk_sql(text, enabled=FRONT_DESK_CAP in caps)
    from app.bake.features.venue_clean import (
        VENUE_CLEAN_CAP,
        merge_venue_clean_capabilities,
    )

    caps = merge_venue_clean_capabilities(
        caps,
        proposal_text or "",
        domain=domain,
        title=title or "",
    )
    text = ensure_venue_clean_sql(
        text,
        enabled=VENUE_CLEAN_CAP in caps,
        item_table=resolved_item,
    )
    from app.bake.features.buyback import BUYBACK_CAP, merge_buyback_capabilities

    caps = merge_buyback_capabilities(
        caps,
        proposal_text or "",
        domain=domain,
        title=title or "",
    )
    text = ensure_buyback_sql(text, enabled=BUYBACK_CAP in caps)
    from app.bake.features.lesson_pack import LESSON_PACK_CAP, merge_lesson_pack_capabilities

    caps = merge_lesson_pack_capabilities(
        caps,
        proposal_text or "",
        domain=domain,
        title=title or "",
    )
    text = ensure_lesson_pack_sql(text, enabled=LESSON_PACK_CAP in caps)
    from app.bake.features.rental_bond import RENTAL_BOND_CAP, merge_rental_bond_capabilities

    caps = merge_rental_bond_capabilities(
        caps,
        proposal_text or "",
        domain=domain,
        title=title or "",
    )
    text = ensure_rental_bond_sql(
        text,
        enabled=RENTAL_BOND_CAP in caps,
        item_table=resolved_item or "vehicle",
    )
    from app.bake.features.digital_goods import DIGITAL_GOODS_CAP, merge_digital_goods_capabilities

    caps = merge_digital_goods_capabilities(
        caps,
        proposal_text or "",
        domain=domain,
        title=title or "",
    )
    text = ensure_digital_goods_sql(
        text,
        enabled=DIGITAL_GOODS_CAP in caps,
        item_table=resolved_item,
    )
    text = ensure_ticket_progress_sql(text, resolved_ticket)
    if EXAM_CAP in caps:
        gate_ticket = scan_exam_gate_ticket(proposal_text or "", domain)
        skin = "safety" if gate_ticket else scan_exam_skin(proposal_text or "")
        text = ensure_exam_core_sql(text, enabled=True, gate_ticket=gate_ticket)
        text = apply_exam_skin_sql(text, skin)
        opts = scan_exam_opts(proposal_text or "")
        text = ensure_exam_wrongbook_sql(text, enabled=bool(opts.get("wrongbook")))
    if VOTE_CAP in caps:
        text = ensure_vote_sql(
            text,
            enabled=True,
            seed_activity=(domain or "") == "DOM-ACTIVITY",
        )
    text = ensure_guestbook_sql(
        text,
        enabled=GUESTBOOK_CAP in caps,
        with_channel=shop_marketplace and GUESTBOOK_CAP in caps,
    )
    text = ensure_item_comment_sql(text, enabled=ITEM_COMMENT_CAP in caps)
    text = ensure_notice_pinned_column(text)
    text = ensure_ai_assistant_sql(
        text,
        enabled=AI_ASSISTANT_CAP in caps,
        domain=domain or "",
        title=title or "",
        proposal_text=proposal_text or "",
        capabilities=list(caps or []),
    )
    text = ensure_dm_sql(
        text,
        enabled=DM_CAP in caps,
    )
    text = ensure_favorites_sql(
        text,
        enabled=FAVORITES_CAP in caps,
    )
    text = ensure_post_like_sql(
        text,
        enabled=POST_LIKE_CAP in caps,
        item_table=resolved_item,
    )
    text = ensure_content_report_sql(
        text,
        enabled=CONTENT_REPORT_CAP in caps,
    )
    text = ensure_audit_log_sql(
        text,
        enabled=AUDIT_LOG_CAP in caps,
    )
    text = ensure_message_template_sql(
        text,
        enabled=MESSAGE_TEMPLATE_CAP in caps,
    )
    text = ensure_staff_roster_sql(
        text,
        enabled=STAFF_ROSTER_CAP in caps,
    )
    text = ensure_room_equipment_sql(
        text,
        enabled=ROOM_EQUIPMENT_CAP in caps,
        item_table=resolved_item,
    )
    text = ensure_book_suggest_sql(
        text,
        enabled=BOOK_SUGGEST_CAP in caps,
    )
    text = ensure_browse_history_sql(
        text,
        enabled=BROWSE_HISTORY_CAP in caps,
    )
    text = ensure_archive_log_sql(
        text,
        enabled=ARCHIVE_LOG_CAP in caps,
    )
    text = ensure_gallery_sql(
        text,
        enabled=GALLERY_CAP in caps,
        item_table=resolved_item,
    )
    text = ensure_detail_attrs_sql(
        text,
        enabled=DETAIL_ATTRS_CAP in caps,
        item_table=resolved_item,
    )
    text = ensure_coupon_lifecycle_sql(
        text,
        enabled="coupon" in caps,
    )
    text = ensure_order_review_sql(
        text,
        enabled=ORDER_REVIEW_CAP in caps,
    )
    text = ensure_stock_io_sql(
        text,
        enabled=STOCK_IO_CAP in caps,
    )
    text = ensure_e_sign_sql(
        text,
        enabled=E_SIGN_CAP in caps,
    )
    text = ensure_balance_ledger_sql(
        text,
        enabled=BALANCE_LEDGER_CAP in caps,
        domain=domain or "",
    )
    text = ensure_occupy_span_sql(
        text,
        enabled=OCCUPY_SPAN_CAP in caps,
    )
    text = ensure_material_check_sql(
        text,
        enabled=MATERIAL_CHECK_CAP in caps,
    )
    text = ensure_lostfound_sql(
        text,
        claim_proof=CLAIM_PROOF_CAP in caps,
        lost_clue=LOST_CLUE_CAP in caps,
    )
    text = ensure_borrow_structural_sql(
        text,
        domain=domain or "",
        capabilities=list(caps or []),
    )
    text = append_staff_seed_sql(
        text,
        domain,
        archetype,
        archetypes,
        proposal_text=proposal_text or "",
        title=title or "",
        posts=staff_posts,
    )
    # 演示日历不在 bake 时写死「今天」：交付后隔月答辩仍靠启动时 SeedCalendarAligner 平移
    return (
        text.replace("${DB_NAME}", db_name)
        .replace("${DOMAIN}", domain)
        .replace("${TABLE_COUNT_MIN}", str(TABLE_COUNT_MIN))
        .replace("${TABLE_COUNT_MAX}", str(TABLE_COUNT_MAX))
    )

