"""跨域 SQL 共享片段：bake 时幂等补列，避免各 DOM-*.sql 手改漏列。

预约/订单/单据扩展列均按域（及能力开关）注入并剔除跨域超集；
运行时禁止再 ALTER 补全套。
"""

from __future__ import annotations

import re

from app.bake.sql.ddl_edit import (
    CREATE_TABLE_RE as _CREATE_TABLE_RE,
    inject_missing_columns as _inject_missing_columns,
    prune_columns as _prune_columns,
    strip_trailing_comma_before_close as _strip_trailing_comma,
)

# 预约扩展列全集（仅作剔除名单；注入按域拆分，禁止跨域超集）
from app.bake.sql.shared_columns import RESERVATION_EXTRA_COLUMNS  # re-export

from app.bake.sql.shared_columns import _RESERVATION_EXTRA_NAMES  # re-export

# 具名预约域各自只保留本域字段；GENERIC / 未登记域不加扩展列
from app.bake.sql.shared_columns import RESERVATION_COLUMNS_BY_DOMAIN  # re-export

# 订单履约扩展列全集（剔除名单）；注入按域拆分，禁止餐饮/商城/酒店串味
from app.bake.sql.shared_columns import ORDER_ADDRESS_COLUMNS  # re-export

from app.bake.sql.shared_columns import ORDER_FOOD_COLUMNS  # re-export

from app.bake.sql.shared_columns import ORDER_SHOP_FULFILL_COLUMNS  # re-export

from app.bake.sql.shared_columns import ORDER_RESERVATION_LINK_COLUMNS  # re-export

# 兼容旧名：曾作「全交易域超集」；现仅作已知列目录
from app.bake.sql.shared_columns import ORDER_SHIP_COLUMNS  # re-export

from app.bake.sql.shared_columns import _ORDER_FULFILL_NAMES  # re-export

# 子管/业务员工岗位（任命与登录分流）
from app.bake.sql.shared_columns import SYS_USER_STAFF_COLUMNS  # re-export

# 忠诚度：余额 / 积分 / 会员（运行时按能力使用）
from app.bake.sql.shared_columns import SYS_USER_LOYALTY_COLUMNS  # re-export

from app.bake.sql.shared_columns import ORDER_LOYALTY_COLUMNS  # re-export

from app.bake.sql.shared_columns import ORDER_REFUND_COLUMNS  # re-export

from app.bake.sql.shared_columns import _USER_LEDGER_DDL  # re-export


from app.bake.sql.shared_columns import _SYS_USER_LOYALTY_NAMES  # re-export
from app.bake.sql.shared_columns import _ORDER_LOYALTY_NAMES  # re-export


def order_fulfill_columns_for(
    domain: str,
    archetypes: list[str] | None = None,
) -> list[tuple[str, str]]:
    from app.bake.sql.shared_columns import order_fulfill_columns_for as _impl
    return _impl(domain, archetypes)


# 预约办结评价列（由 schema.entities.reservation.allowRating 注入，不进域固有超集）
from app.bake.sql.shared_columns import RESERVATION_RATING_COLUMNS  # re-export
from app.bake.sql.shared_columns import _RESERVATION_RATING_NAMES  # re-export


def ensure_shared_sql_columns(
    sql: str,
    *,
    domain: str = "",
    archetypes: list[str] | None = None,
    staff: bool = True,
    loyalty: bool = False,
    reservation_flags: dict | None = None,
) -> str:
    from app.bake.sql.shared_columns import ensure_shared_sql_columns as _impl
    return _impl(sql, domain=domain, archetypes=archetypes, staff=staff, loyalty=loyalty, reservation_flags=reservation_flags)


from app.bake.sql.ticket_optional_columns import _TICKET_PROGRESS_DDL  # re-export


from app.bake.features.guestbook import _GUESTBOOK_DDL  # re-export

from app.bake.features.dm import _DM_DDL  # re-export

# 私信演示：补第二用户 + 几条互发（幂等；依赖已有 user 账号）
from app.bake.features.dm import _DM_SEED  # re-export


from app.bake.features.guestbook import GUESTBOOK_CHANNEL_COLUMNS  # re-export


def ensure_guestbook_sql(
    sql: str,
    *,
    enabled: bool,
    with_channel: bool = False,
) -> str:
    from app.bake.features.guestbook import ensure_guestbook_sql as _impl
    return _impl(sql, enabled=enabled, with_channel=with_channel)


from app.bake.features.item_comment import _ITEM_COMMENT_DDL  # re-export


def ensure_item_comment_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.item_comment import ensure_item_comment_sql as _impl
    return _impl(sql, enabled=enabled)


from app.bake.features.ai_assistant import _AI_KNOWLEDGE_DDL  # re-export


def ensure_ai_assistant_sql(
    sql: str,
    *,
    enabled: bool,
    domain: str = "",
    title: str = "",
    proposal_text: str = "",
    capabilities: list | None = None,
) -> str:
    from app.bake.features.ai_assistant import ensure_ai_assistant_sql as _impl
    return _impl(sql, enabled=enabled, domain=domain, title=title, proposal_text=proposal_text, capabilities=capabilities)


from app.bake.features.exam import _EXAM_WRONGBOOK_DDL  # re-export

from app.bake.features.exam import _EXAM_CORE_DDL  # re-export

from app.bake.features.exam import _EXAM_LABSAFE_GATE_SEED  # re-export


def ensure_exam_wrongbook_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.exam import ensure_exam_wrongbook_sql as _impl
    return _impl(sql, enabled=enabled)


from app.bake.features.vote import _VOTE_CORE_DDL  # re-export

from app.bake.features.vote import _VOTE_ACTIVITY_SEED  # re-export


from app.bake.features.vote import VOTE_CANDIDATE_COLUMNS  # re-export


def ensure_vote_sql(sql: str, *, enabled: bool, seed_activity: bool = False) -> str:
    from app.bake.features.vote import ensure_vote_sql as _impl
    return _impl(sql, enabled=enabled, seed_activity=seed_activity)


def ensure_exam_core_sql(sql: str, *, enabled: bool, gate_ticket: bool = False) -> str:
    from app.bake.features.exam import ensure_exam_core_sql as _impl
    return _impl(sql, enabled=enabled, gate_ticket=gate_ticket)


def ensure_dm_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.dm import ensure_dm_sql as _impl
    return _impl(sql, enabled=enabled)


from app.bake.features.favorites import _FAVORITE_DDL  # re-export

from app.bake.features.favorites import _POST_LIKE_DDL  # re-export

from app.bake.features.favorites import _CONTENT_REPORT_DDL  # re-export


def ensure_favorites_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.favorites import ensure_favorites_sql as _impl
    return _impl(sql, enabled=enabled)


def ensure_post_like_sql(sql: str, *, enabled: bool, item_table: str | None = None) -> str:
    from app.bake.features.favorites import ensure_post_like_sql as _impl
    return _impl(sql, enabled=enabled, item_table=item_table)


def ensure_content_report_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.favorites import ensure_content_report_sql as _impl
    return _impl(sql, enabled=enabled)


from app.bake.features.staff_roster import _STAFF_ROSTER_DDL  # re-export

from app.bake.features.staff_roster import _STAFF_ROSTER_SEED  # re-export


def ensure_staff_roster_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.staff_roster import ensure_staff_roster_sql as _impl
    return _impl(sql, enabled=enabled)


from app.bake.features.message_template import _MESSAGE_TEMPLATE_DDL  # re-export

from app.bake.features.message_template import _MESSAGE_TEMPLATE_SEED  # re-export


def ensure_message_template_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.message_template import ensure_message_template_sql as _impl
    return _impl(sql, enabled=enabled)


from app.bake.features.book_suggest import _BOOK_SUGGEST_DDL  # re-export

from app.bake.features.book_suggest import _BOOK_SUGGEST_SEED  # re-export


def ensure_book_suggest_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.book_suggest import ensure_book_suggest_sql as _impl
    return _impl(sql, enabled=enabled)


from app.bake.features.parcel_ship import _PARCEL_SHIP_DDL  # re-export

from app.bake.features.parcel_ship import _PARCEL_SHIP_SEED  # re-export


def ensure_parcel_ship_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.parcel_ship import ensure_parcel_ship_sql as _impl
    return _impl(sql, enabled=enabled)


from app.bake.features.audit_log import _AUDIT_LOG_DDL  # re-export


def ensure_audit_log_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.audit_log import ensure_audit_log_sql as _impl
    return _impl(sql, enabled=enabled)

from app.bake.features.favorites import _BROWSE_HISTORY_DDL  # re-export


def ensure_browse_history_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.favorites import ensure_browse_history_sql as _impl
    return _impl(sql, enabled=enabled)


from app.bake.features.archive_log import _ARCHIVE_LOG_DDL  # re-export


def ensure_archive_log_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.archive_log import ensure_archive_log_sql as _impl
    return _impl(sql, enabled=enabled)


SOFT_DELETE_COLUMNS: list[tuple[str, str]] = [
    ("deleted_at", "DATETIME NULL"),
]


def ensure_soft_delete_columns(
    sql: str,
    *,
    enabled: bool,
    item_table: str | None,
) -> str:
    """archive.softDelete 开时档案主表须有 deleted_at（与 yml archive-soft-delete 对齐）。"""
    if not enabled:
        return sql
    t = (item_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != t.lower():
            return m.group(0)
        body = _inject_missing_columns(body, SOFT_DELETE_COLUMNS)
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, sql)


NOTICE_PINNED_COLUMNS: list[tuple[str, str]] = [
    ("pinned", "TINYINT NOT NULL DEFAULT 0"),
]


def ensure_notice_pinned_column(sql: str, *, enabled: bool = True) -> str:
    """公告表幂等补 pinned，避免依赖学生包运行时 ALTER。"""
    if not enabled:
        return sql
    if not re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?sys_notice`?\b", sql):
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != "sys_notice":
            return m.group(0)
        body = _inject_missing_columns(body, NOTICE_PINNED_COLUMNS)
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, sql)


from app.bake.features.detail_attrs import GALLERY_COLUMNS  # re-export

# 借用组浅档案列（馆藏/货架/批次/床位约束等）
BORROW_ARCHIVE_COLUMNS: list[tuple[str, str]] = [
    ("holding_loc", "VARCHAR(128) DEFAULT ''"),
    ("campus_zone", "VARCHAR(64) DEFAULT ''"),
    ("shelf_no", "VARCHAR(64) DEFAULT ''"),
    ("batch_no", "VARCHAR(64) DEFAULT ''"),
    ("expire_on", "VARCHAR(32) DEFAULT ''"),
    ("supplier_contact", "VARCHAR(64) DEFAULT ''"),
    ("allowed_gender", "VARCHAR(16) DEFAULT ''"),
    ("allowed_grades", "VARCHAR(64) DEFAULT ''"),
    ("maintain_due", "VARCHAR(32) DEFAULT ''"),
    ("loan_org", "VARCHAR(128) DEFAULT ''"),
    ("clc_code", "VARCHAR(32) DEFAULT ''"),
    ("calib_cert_url", "VARCHAR(255) DEFAULT ''"),
    ("calib_due", "VARCHAR(32) DEFAULT ''"),
    ("repair_ticket_no", "VARCHAR(64) DEFAULT ''"),
    ("slot_status", "VARCHAR(16) DEFAULT ''"),
    ("building_zone", "VARCHAR(64) DEFAULT ''"),
]

_BORROW_ARCHIVE_DOMAINS = frozenset({
    "DOM-LIBRARY",
    "DOM-EQUIP",
    "DOM-ASSET",
    "DOM-PARCEL",
    "DOM-BED",
})


FOLLOW_ARCHIVE_COLUMNS: list[tuple[str, str]] = [
    ("tags", "VARCHAR(255) DEFAULT ''"),
    ("lead_source", "VARCHAR(64) DEFAULT ''"),
    ("payment_plan", "VARCHAR(255) DEFAULT ''"),
    ("location_desc", "VARCHAR(255) DEFAULT ''"),
    ("fund_form", "VARCHAR(32) DEFAULT ''"),
    ("expire_on", "VARCHAR(32) DEFAULT ''"),
    ("hire_dept", "VARCHAR(64) DEFAULT ''"),
    ("price_history", "VARCHAR(255) DEFAULT ''"),
    ("vr_url", "VARCHAR(255) DEFAULT ''"),
]

_FOLLOW_ARCHIVE_DOMAINS = frozenset({
    "DOM-CRM",
    "DOM-EVENT",
    "DOM-ATTEND",
    "DOM-FUND",
    "DOM-RECRUIT",
    "DOM-GRADE",
    "DOM-INTERN",
    "DOM-LISTING",
})


def ensure_borrow_archive_columns(
    sql: str,
    *,
    domain: str | None,
    item_table: str | None,
) -> str:
    """借用/占用组档案浅字段注入（只增不减）。"""
    if (domain or "") not in _BORROW_ARCHIVE_DOMAINS:
        return sql
    t = (item_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != t.lower():
            return m.group(0)
        body = _inject_missing_columns(body, BORROW_ARCHIVE_COLUMNS)
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, sql)


def ensure_follow_archive_columns(
    sql: str,
    *,
    domain: str | None,
    item_table: str | None,
) -> str:
    """跟进组档案浅字段注入（只增不减）。"""
    if (domain or "") not in _FOLLOW_ARCHIVE_DOMAINS:
        return sql
    t = (item_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != t.lower():
            return m.group(0)
        body = _inject_missing_columns(body, FOLLOW_ARCHIVE_COLUMNS)
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, sql)


# 报名/申请组浅档案列（按域子集注入）
APPLY_ARCHIVE_COLUMNS_BY_DOMAIN: dict[str, list[tuple[str, str]]] = {
    "DOM-ACTIVITY": [
        ("checkin_place", "VARCHAR(128) DEFAULT ''"),
        ("session_group", "VARCHAR(64) DEFAULT ''"),
        ("apply_invite_code", "VARCHAR(64) DEFAULT ''"),
        ("sponsor_note", "VARCHAR(255) DEFAULT ''"),
        ("group_price_note", "TEXT NULL"),
        ("fee_yuan", "DECIMAL(10,2) NULL"),
        ("allowed_gender", "VARCHAR(16) DEFAULT ''"),
        ("allowed_grades", "VARCHAR(64) DEFAULT ''"),
    ],
    "DOM-LOST": [
        ("expire_on", "VARCHAR(32) DEFAULT ''"),
        ("bounty_note", "VARCHAR(128) DEFAULT ''"),
        ("stage", "VARCHAR(32) DEFAULT '招领中'"),
        ("lost_category", "VARCHAR(32) DEFAULT ''"),
        ("view_count", "INT NOT NULL DEFAULT 0"),
        ("fee_yuan", "DECIMAL(10,2) NULL"),
    ],
    "DOM-COURSE": [
        ("textbook", "VARCHAR(255) DEFAULT ''"),
        ("course_kind", "VARCHAR(16) DEFAULT ''"),
        ("prereq_code", "VARCHAR(64) DEFAULT ''"),
        ("college", "VARCHAR(64) DEFAULT ''"),
        ("plan_url", "VARCHAR(255) DEFAULT ''"),
        ("allowed_gender", "VARCHAR(16) DEFAULT ''"),
        ("allowed_grades", "VARCHAR(64) DEFAULT ''"),
    ],
    "DOM-TOUR": [
        ("day_itinerary", "TEXT NULL"),
        ("leader_contact", "VARCHAR(128) DEFAULT ''"),
        ("meeting_point", "VARCHAR(128) DEFAULT ''"),
        ("min_group_size", "INT NULL"),
        ("single_room_note", "TEXT NULL"),
        ("group_price_note", "TEXT NULL"),
        ("fee_yuan", "DECIMAL(10,2) NULL"),
        ("min_age", "INT NULL"),
        ("max_age", "INT NULL"),
    ],
}


def ensure_apply_archive_columns(
    sql: str,
    *,
    domain: str | None,
    item_table: str | None,
) -> str:
    """报名/申请组档案浅字段注入（只增不减）。"""
    cols = APPLY_ARCHIVE_COLUMNS_BY_DOMAIN.get(domain or "")
    if not cols:
        return sql
    t = (item_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != t.lower():
            return m.group(0)
        body = _inject_missing_columns(body, cols)
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, sql)


def ensure_detail_attrs_sql(
    sql: str,
    *,
    enabled: bool,
    item_table: str | None,
    attr_fields: list[dict[str, str]] | list[str] | None = None,
    attr_keys: list[str] | None = None,
) -> str:
    from app.bake.features.detail_attrs import ensure_detail_attrs_sql as _impl
    return _impl(sql, enabled=enabled, item_table=item_table, attr_fields=attr_fields, attr_keys=attr_keys)


def ensure_gallery_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    from app.bake.features.detail_attrs import ensure_gallery_sql as _impl
    return _impl(sql, enabled=enabled, item_table=item_table)


from app.bake.features.room_equipment import ROOM_EQUIPMENT_COLUMNS  # re-export

from app.bake.features.room_equipment import _EQUIPMENT_DICT_DDL  # re-export

from app.bake.features.room_equipment import _EQUIPMENT_DICT_SEED  # re-export


def ensure_room_equipment_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    from app.bake.features.room_equipment import ensure_room_equipment_sql as _impl
    return _impl(sql, enabled=enabled, item_table=item_table)


CHECKIN_CODE_COLUMNS: list[tuple[str, str]] = [
    ("checkin_code", "VARCHAR(16) NOT NULL DEFAULT ''"),
]

OWNER_USERNAME_COLUMNS: list[tuple[str, str]] = [
    ("owner_username", "VARCHAR(64) NOT NULL DEFAULT ''"),
]

MUTEX_CODE_COLUMNS: list[tuple[str, str]] = [
    ("mutex_code", "VARCHAR(32) NOT NULL DEFAULT ''"),
]


APPLY_DEADLINE_COLUMNS: list[tuple[str, str]] = [
    ("apply_deadline_at", "DATETIME NULL"),
]

SCHEDULE_COLUMNS: list[tuple[str, str]] = [
    ("start_at", "DATETIME NULL"),
    ("end_at", "DATETIME NULL"),
]


from app.bake.features.order_extras import FLASH_PRICE_COLUMNS  # re-export


def ensure_flash_price_columns(sql: str, *, enabled: bool, item_table: str | None) -> str:
    from app.bake.features.order_extras import ensure_flash_price_columns as _impl
    return _impl(sql, enabled=enabled, item_table=item_table)


from app.bake.features.product_spec import PRODUCT_SPEC_COLUMNS  # re-export


def ensure_product_spec_columns(sql: str, *, enabled: bool, item_table: str | None) -> str:
    from app.bake.features.product_spec import ensure_product_spec_columns as _impl
    return _impl(sql, enabled=enabled, item_table=item_table)


from app.bake.features.multi_category import CATEGORY_DIMENSION_COLUMNS  # re-export


def ensure_multi_category_sql(
    sql: str,
    *,
    enabled: bool,
    item_table: str | None = "product",
    junction_table: str = "product_category",
    axis_seed_sql: str = "",
) -> str:
    from app.bake.features.multi_category import ensure_multi_category_sql as _impl
    return _impl(sql, enabled=enabled, item_table=item_table, junction_table=junction_table, axis_seed_sql=axis_seed_sql)


def ensure_product_tags_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.product_tags import ensure_product_tags_sql as _impl
    return _impl(sql, enabled=enabled)


from app.bake.features.line_custom import ORDER_LINE_CUSTOM_COLUMNS  # re-export


def ensure_order_line_custom_columns(sql: str, *, enabled: bool, with_spec: bool = False) -> str:
    from app.bake.features.line_custom import ensure_order_line_custom_columns as _impl
    return _impl(sql, enabled=enabled, with_spec=with_spec)


from app.bake.features.delivery_window import ORDER_WINDOW_COLUMNS  # re-export

from app.bake.features.delivery_window import _DELIVERY_WINDOW_DDL  # re-export

from app.bake.features.delivery_window import _DELIVERY_WINDOW_SEED  # re-export


def ensure_delivery_window_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.delivery_window import ensure_delivery_window_sql as _impl
    return _impl(sql, enabled=enabled)


from app.bake.features.purchase_gate import PRODUCT_GATE_COLUMNS  # re-export

from app.bake.features.purchase_gate import _PURCHASE_GATE_DDL  # re-export


def ensure_purchase_gate_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    from app.bake.features.purchase_gate import ensure_purchase_gate_sql as _impl
    return _impl(sql, enabled=enabled, item_table=item_table)


from app.bake.features.group_buy import _GROUP_BUY_DDL  # re-export

from app.bake.features.group_buy import _GROUP_BUY_SEED  # re-export


def ensure_group_buy_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.group_buy import ensure_group_buy_sql as _impl
    return _impl(sql, enabled=enabled)


from app.bake.features.blind_box import PRODUCT_PITY_COLUMNS  # re-export

from app.bake.features.blind_box import ORDER_LINE_DRAW_COLUMNS  # re-export

from app.bake.features.blind_box import _BLIND_BOX_DDL  # re-export


def ensure_blind_box_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    from app.bake.features.blind_box import ensure_blind_box_sql as _impl
    return _impl(sql, enabled=enabled, item_table=item_table)


from app.bake.features.consign import _CONSIGN_DDL  # re-export


def ensure_consign_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    from app.bake.features.consign import ensure_consign_sql as _impl
    return _impl(sql, enabled=enabled, item_table=item_table)


from app.bake.features.weigh_sale import PRODUCT_WEIGH_COLUMNS  # re-export

from app.bake.features.weigh_sale import ORDER_LINE_WEIGHT_COLUMNS  # re-export

from app.bake.features.weigh_sale import _WEIGH_SALE_DDL  # re-export


def ensure_weigh_sale_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    from app.bake.features.weigh_sale import ensure_weigh_sale_sql as _impl
    return _impl(sql, enabled=enabled, item_table=item_table)


from app.bake.features.shoot import _SHOOT_DDL  # re-export


def ensure_shoot_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.shoot import ensure_shoot_sql as _impl
    return _impl(sql, enabled=enabled)


from app.bake.features.boarding import _BOARDING_DDL  # re-export


def ensure_boarding_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.boarding import ensure_boarding_sql as _impl
    return _impl(sql, enabled=enabled)


from app.bake.features.room_board import _ROOM_BOARD_DDL  # re-export

from app.bake.features.front_desk import _FRONT_DESK_DDL  # re-export


from app.bake.features.venue_clean import _VENUE_CLEAN_COLUMNS  # re-export


def ensure_venue_clean_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    from app.bake.features.venue_clean import ensure_venue_clean_sql as _impl
    return _impl(sql, enabled=enabled, item_table=item_table)


def ensure_room_board_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.room_board import ensure_room_board_sql as _impl
    return _impl(sql, enabled=enabled)


def ensure_front_desk_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.front_desk import ensure_front_desk_sql as _impl
    return _impl(sql, enabled=enabled)


from app.bake.features.rental_bond import ORDER_RENTAL_BOND_COLUMNS  # re-export

from app.bake.features.rental_bond import VEHICLE_RENTAL_BOND_COLUMNS  # re-export


def ensure_rental_bond_sql(sql: str, *, enabled: bool, item_table: str | None = "vehicle") -> str:
    from app.bake.features.rental_bond import ensure_rental_bond_sql as _impl
    return _impl(sql, enabled=enabled, item_table=item_table)


from app.bake.features.digital_goods import _DIGITAL_GOODS_DDL  # re-export

from app.bake.features.digital_goods import PRODUCT_DIGITAL_COLUMNS  # re-export


def ensure_digital_goods_sql(sql: str, *, enabled: bool, item_table: str | None = "product") -> str:
    from app.bake.features.digital_goods import ensure_digital_goods_sql as _impl
    return _impl(sql, enabled=enabled, item_table=item_table)


from app.bake.features.buyback import _BUYBACK_DDL  # re-export


def ensure_buyback_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.buyback import ensure_buyback_sql as _impl
    return _impl(sql, enabled=enabled)


from app.bake.features.lesson_pack import _LESSON_PACK_DDL  # re-export


def ensure_lesson_pack_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.lesson_pack import ensure_lesson_pack_sql as _impl
    return _impl(sql, enabled=enabled)


def ensure_archive_flag_columns(
    sql: str,
    *,
    item_table: str | None,
    allow_checkin: bool = False,
    peer_accept: bool = False,
    user_publish: bool = False,
    shop_marketplace: bool = False,
    check_mutex: bool = False,
    apply_deadline: bool = False,
    schedule: bool = False,
) -> str:
    """档案表按单据能力补签到码 / 确认人 / 互斥码 / 申报截止 / 起止时间列（禁止运行时再 ALTER）。"""
    t = (item_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql
    cols: list[tuple[str, str]] = []
    if allow_checkin:
        cols.extend(CHECKIN_CODE_COLUMNS)
    # 互选确认人、门户发布归属均用 owner_username；商城多店商品归属亦复用
    if peer_accept or user_publish or shop_marketplace:
        cols.extend(OWNER_USERNAME_COLUMNS)
    if check_mutex:
        cols.extend(MUTEX_CODE_COLUMNS)
    if apply_deadline:
        cols.extend(APPLY_DEADLINE_COLUMNS)
    if schedule:
        cols.extend(SCHEDULE_COLUMNS)
    if not cols:
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != t.lower():
            return m.group(0)
        body = _inject_missing_columns(body, cols)
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, sql)


from app.bake.features.order_extras import _PROMO_COUPON_DDL  # re-export

from app.bake.features.order_extras import _USER_COUPON_DDL  # re-export

from app.bake.features.order_extras import _ORDER_REVIEW_DDL  # re-export


def ensure_coupon_lifecycle_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.order_extras import ensure_coupon_lifecycle_sql as _impl
    return _impl(sql, enabled=enabled)


def _ensure_create_table_ddl(sql: str, *, table: str, ddl: str) -> str:
    """幂等补 CREATE TABLE；种子若已 INSERT/UPDATE 该表，则插到首条引用之前。"""
    if re.search(
        rf"(?i)CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?{re.escape(table)}`?\b",
        sql,
    ):
        return sql
    block = ddl if ddl.endswith("\n") else ddl + "\n"
    m = re.search(
        rf"(?i)(?:INSERT\s+(?:IGNORE\s+)?INTO|UPDATE|ALTER\s+TABLE|DELETE\s+FROM)\s+`?{re.escape(table)}`?\b",
        sql,
    )
    if m:
        return sql[: m.start()] + block + sql[m.start() :]
    return sql.rstrip() + "\n" + block


def ensure_order_review_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.order_extras import ensure_order_review_sql as _impl
    return _impl(sql, enabled=enabled)


from app.bake.features.stock_io import _STOCK_IO_DDL  # re-export


def ensure_stock_io_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.stock_io import ensure_stock_io_sql as _impl
    return _impl(sql, enabled=enabled)


from app.bake.features.stock_scrap import _SCRAP_REQUEST_DDL  # re-export


def ensure_scrap_request_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.stock_scrap import ensure_scrap_request_sql as _impl
    return _impl(sql, enabled=enabled)


from app.bake.features.e_sign import _E_SIGN_DDL  # re-export


def ensure_e_sign_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.e_sign import ensure_e_sign_sql as _impl
    return _impl(sql, enabled=enabled)


from app.bake.features.timebank import _BALANCE_LEDGER_DDL  # re-export


def ensure_balance_ledger_sql(sql: str, *, enabled: bool, domain: str = "") -> str:
    from app.bake.features.timebank import ensure_balance_ledger_sql as _impl
    return _impl(sql, enabled=enabled, domain=domain)


from app.bake.features.ticket_flow_opts import _OCCUPY_SPAN_DDL  # re-export


def ensure_occupy_span_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.ticket_flow_opts import ensure_occupy_span_sql as _impl
    return _impl(sql, enabled=enabled)


from app.bake.features.ticket_flow_opts import _MATERIAL_CHECK_DDL  # re-export


def ensure_material_check_sql(sql: str, *, enabled: bool) -> str:
    from app.bake.features.ticket_flow_opts import ensure_material_check_sql as _impl
    return _impl(sql, enabled=enabled)


# 亮点域结构补表：只补 ER 缺实体，规则仍走已有 cap
from app.bake.features.borrow_structural import _STRUCTURAL_DDL  # re-export


def _append_ddl_if_missing(sql: str, table: str, ddl: str) -> str:
    from app.bake.features.borrow_structural import _append_ddl_if_missing as _impl
    return _impl(sql, table, ddl)


def ensure_borrow_structural_sql(
    sql: str,
    *,
    domain: str,
    capabilities: list[str] | None = None,
) -> str:
    from app.bake.features.borrow_structural import ensure_borrow_structural_sql as _impl
    return _impl(sql, domain=domain, capabilities=capabilities)


# 单据可选扩展列全集（剔除名单）；注入按域 + schema.ticket 能力
from app.bake.sql.ticket_optional_columns import TICKET_OPTIONAL_COLUMNS  # re-export

from app.bake.sql.ticket_optional_columns import _TICKET_OPTIONAL_NAMES  # re-export
from app.bake.sql.ticket_optional_columns import _TICKET_COL_DDL  # re-export

# 域固有业务列（不含 attach/rating 等能力开关列）
from app.bake.sql.ticket_optional_columns import TICKET_DOMAIN_COLUMNS  # re-export


def _ticket_flag_column_names(flags: dict | None) -> list[str]:
    from app.bake.sql.ticket_optional_columns import _ticket_flag_column_names as _impl
    return _impl(flags)


def resolve_ticket_flags(
    domain: str,
    *,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
    ticket_flags: dict | None = None,
) -> dict:
    from app.bake.sql.ticket_optional_columns import resolve_ticket_flags as _impl
    return _impl(domain, archetype=archetype, archetypes=archetypes, ticket_flags=ticket_flags)


def ticket_optional_columns_for(
    domain: str,
    *,
    ticket_flags: dict | None = None,
) -> list[tuple[str, str]]:
    from app.bake.sql.ticket_optional_columns import ticket_optional_columns_for as _impl
    return _impl(domain, ticket_flags=ticket_flags)


def ensure_ticket_extra_sql(
    sql: str,
    *,
    domain: str,
    ticket_table: str | None,
    ticket_flags: dict | None = None,
) -> str:
    from app.bake.sql.ticket_optional_columns import ensure_ticket_extra_sql as _impl
    return _impl(sql, domain=domain, ticket_table=ticket_table, ticket_flags=ticket_flags)


from app.bake.sql.ticket_optional_columns import _CREDIT_LEDGER_DDL  # re-export

from app.bake.sql.ticket_optional_columns import SYS_USER_CREDIT_COLUMNS  # re-export


def ensure_borrow_credit_sql(
    sql: str,
    *,
    enabled: bool,
    initial: int = 100,
) -> str:
    from app.bake.sql.ticket_optional_columns import ensure_borrow_credit_sql as _impl
    return _impl(sql, enabled=enabled, initial=initial)


def ensure_ticket_progress_sql(sql: str, ticket_table: str | None) -> str:
    from app.bake.sql.ticket_optional_columns import ensure_ticket_progress_sql as _impl
    return _impl(sql, ticket_table)
