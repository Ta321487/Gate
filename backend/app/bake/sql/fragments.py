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
RESERVATION_EXTRA_COLUMNS: list[tuple[str, str]] = [
    ("plate_no", "VARCHAR(16) DEFAULT ''"),
    ("patient_name", "VARCHAR(32) DEFAULT ''"),
    ("visit_type", "VARCHAR(16) DEFAULT ''"),
    ("symptom_note", "VARCHAR(255) DEFAULT ''"),
    ("subject", "VARCHAR(128) DEFAULT ''"),
    ("party_size", "INT DEFAULT 0"),
    ("guest_name", "VARCHAR(32) DEFAULT ''"),
    ("guest_count", "INT DEFAULT 0"),
    ("preferred_stylist", "VARCHAR(32) DEFAULT ''"),
    ("queue_no", "INT DEFAULT 0"),
    ("entry_at", "DATETIME NULL"),
]

_RESERVATION_EXTRA_NAMES = {n.lower() for n, _ in RESERVATION_EXTRA_COLUMNS}

# 具名预约域各自只保留本域字段；GENERIC / 未登记域不加扩展列
RESERVATION_COLUMNS_BY_DOMAIN: dict[str, list[tuple[str, str]]] = {
    "DOM-PARKING": [
        ("plate_no", "VARCHAR(16) DEFAULT ''"),
        ("entry_at", "DATETIME NULL"),
    ],
    "DOM-HOSPITAL": [
        ("patient_name", "VARCHAR(32) DEFAULT ''"),
        ("visit_type", "VARCHAR(16) DEFAULT ''"),
        ("symptom_note", "VARCHAR(255) DEFAULT ''"),
        ("queue_no", "INT DEFAULT 0"),
    ],
    "DOM-MEETING": [
        ("subject", "VARCHAR(128) DEFAULT ''"),
        ("party_size", "INT DEFAULT 0"),
    ],
    "DOM-HOTEL": [
        ("guest_name", "VARCHAR(32) DEFAULT ''"),
        ("guest_count", "INT DEFAULT 0"),
    ],
    "DOM-CARRENT": [
        ("guest_name", "VARCHAR(32) DEFAULT ''"),
        ("guest_count", "INT DEFAULT 0"),
    ],
    "DOM-SALON": [
        ("preferred_stylist", "VARCHAR(32) DEFAULT ''"),
        ("queue_no", "INT DEFAULT 0"),
    ],
}

# 订单履约扩展列全集（剔除名单）；注入按域拆分，禁止餐饮/商城/酒店串味
ORDER_ADDRESS_COLUMNS: list[tuple[str, str]] = [
    ("receiver_name", "VARCHAR(64) DEFAULT ''"),
    ("receiver_phone", "VARCHAR(32) DEFAULT ''"),
    ("address_line", "VARCHAR(255) DEFAULT ''"),
    ("delivery_type", "VARCHAR(32) DEFAULT ''"),
]

ORDER_FOOD_COLUMNS: list[tuple[str, str]] = [
    ("taste_note", "VARCHAR(255) DEFAULT ''"),
    ("pickup_code", "VARCHAR(32) DEFAULT ''"),
    ("shipped_at", "DATETIME NULL"),
]

ORDER_SHOP_FULFILL_COLUMNS: list[tuple[str, str]] = [
    ("tracking_no", "VARCHAR(64) DEFAULT ''"),
    ("pickup_code", "VARCHAR(32) DEFAULT ''"),
    ("shipped_at", "DATETIME NULL"),
]

ORDER_RESERVATION_LINK_COLUMNS: list[tuple[str, str]] = [
    ("reservation_id", "BIGINT NULL"),
]

# 兼容旧名：曾作「全交易域超集」；现仅作已知列目录
ORDER_SHIP_COLUMNS: list[tuple[str, str]] = [
    *ORDER_ADDRESS_COLUMNS,
    ("taste_note", "VARCHAR(255) DEFAULT ''"),
    ("tracking_no", "VARCHAR(64) DEFAULT ''"),
    ("pickup_code", "VARCHAR(32) DEFAULT ''"),
    ("shipped_at", "DATETIME NULL"),
    ("reservation_id", "BIGINT NULL"),
]

_ORDER_FULFILL_NAMES = {n.lower() for n, _ in ORDER_SHIP_COLUMNS}

# 子管/业务员工岗位（任命与登录分流）
SYS_USER_STAFF_COLUMNS: list[tuple[str, str]] = [
    ("staff_post", "VARCHAR(64) DEFAULT ''"),
    ("staff_kind", "VARCHAR(16) DEFAULT ''"),
]

# 忠诚度：按 cap 拆列（wallet 默认 ≠ 整包灌积分/会员/券）
SYS_USER_LOYALTY_BY_CAP: dict[str, list[tuple[str, str]]] = {
    "wallet": [("balance_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0")],
    "points": [("points", "INT NOT NULL DEFAULT 0")],
    "member_tier": [("member_tier", "VARCHAR(32) DEFAULT ''")],
    "spend_discount": [("spend_total_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0")],
}
ORDER_LOYALTY_BY_CAP: dict[str, list[tuple[str, str]]] = {
    "wallet": [("pay_balance_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0")],
    "points": [("points_earned", "INT NOT NULL DEFAULT 0")],
    "spend_discount": [("discount_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0")],
    "coupon": [("coupon_code", "VARCHAR(32) DEFAULT ''")],
}
SYS_USER_LOYALTY_COLUMNS: list[tuple[str, str]] = [
    c for cols in SYS_USER_LOYALTY_BY_CAP.values() for c in cols
]
ORDER_LOYALTY_COLUMNS: list[tuple[str, str]] = [
    c for cols in ORDER_LOYALTY_BY_CAP.values() for c in cols
]

# 订单完结列（生命周期，非售后专属）
ORDER_LIFECYCLE_COLUMNS: list[tuple[str, str]] = [
    ("completed_at", "DATETIME NULL"),
]
# 售后核心 + 分流/退货单号（交易域 A 壳）；非交易有单域只落完结列
ORDER_REFUND_CORE_COLUMNS: list[tuple[str, str]] = [
    ("refund_status", "VARCHAR(16) DEFAULT ''"),
    ("refund_reason", "VARCHAR(255) DEFAULT ''"),
    ("refund_at", "DATETIME NULL"),
    ("refund_requested_at", "DATETIME NULL"),
]
ORDER_REFUND_EXTRA_COLUMNS: list[tuple[str, str]] = [
    ("refund_type", "VARCHAR(32) DEFAULT ''"),
    ("refund_tracking_no", "VARCHAR(64) DEFAULT ''"),
]
ORDER_REFUND_COLUMNS: list[tuple[str, str]] = (
    list(ORDER_REFUND_CORE_COLUMNS)
    + list(ORDER_REFUND_EXTRA_COLUMNS)
    + list(ORDER_LIFECYCLE_COLUMNS)
)
_TRADE_REFUND_DOMAINS = frozenset({"DOM-SHOP", "DOM-FOOD", "DOM-CINEMA"})

ORDER_TRADE_EXTRA_COLUMNS: list[tuple[str, str]] = [
    ("share_token", "VARCHAR(16) DEFAULT ''"),
    ("warranty_until", "DATE NULL"),
    ("partial_ship", "TINYINT NOT NULL DEFAULT 0"),
    ("receive_verified_at", "DATETIME NULL"),
    ("invoice_title", "VARCHAR(128) DEFAULT ''"),
    ("invoice_status", "VARCHAR(16) DEFAULT ''"),
    ("packaging_fee_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
]

_USER_LEDGER_DDL = """
CREATE TABLE IF NOT EXISTS user_ledger (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  kind VARCHAR(16) NOT NULL,
  delta DECIMAL(12,2) NOT NULL,
  balance_after DECIMAL(12,2) NOT NULL DEFAULT 0,
  reason VARCHAR(64) DEFAULT '',
  ref_type VARCHAR(32) DEFAULT '',
  ref_id BIGINT NULL,
  operator VARCHAR(64) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_ledger_user (username, id)
);
"""


_SYS_USER_LOYALTY_NAMES = {n.lower() for n, _ in SYS_USER_LOYALTY_COLUMNS}
_ORDER_LOYALTY_NAMES = {n.lower() for n, _ in ORDER_LOYALTY_COLUMNS}
_ORDER_REFUND_NAMES = {n.lower() for n, _ in ORDER_REFUND_COLUMNS}

_ORDER_TRADE_EXTRA_NAMES = {n.lower() for n, _ in ORDER_TRADE_EXTRA_COLUMNS}


def _loyalty_caps_set(
    loyalty: bool,
    loyalty_caps: set[str] | frozenset[str] | None,
) -> set[str]:
    if loyalty_caps is not None:
        return {str(c).strip() for c in loyalty_caps if str(c).strip()}
    if loyalty:
        return {"wallet", "points", "member_tier", "spend_discount", "coupon"}
    return set()


def loyalty_user_columns_for(caps: set[str]) -> list[tuple[str, str]]:
    cols: list[tuple[str, str]] = []
    for key in ("wallet", "points", "member_tier", "spend_discount"):
        if key in caps:
            cols.extend(SYS_USER_LOYALTY_BY_CAP[key])
    return cols


def loyalty_order_columns_for(caps: set[str]) -> list[tuple[str, str]]:
    cols: list[tuple[str, str]] = []
    for key in ("wallet", "points", "spend_discount", "coupon"):
        if key in caps:
            cols.extend(ORDER_LOYALTY_BY_CAP[key])
    return cols


def order_refund_columns_for(domain: str) -> list[tuple[str, str]]:
    """交易三域售后 A 壳全列；其它有单域只保留 completed_at。"""
    if (domain or "").strip() in _TRADE_REFUND_DOMAINS:
        return list(ORDER_REFUND_COLUMNS)
    return list(ORDER_LIFECYCLE_COLUMNS)


def order_fulfill_columns_for(
    domain: str,
    archetypes: list[str] | None = None,
) -> list[tuple[str, str]]:
    """按域返回订单履约列（不含退款/忠诚度）。"""
    d = (domain or "").strip()
    arches = {a for a in (archetypes or []) if a}

    if d == "DOM-FOOD":
        return list(ORDER_ADDRESS_COLUMNS) + list(ORDER_FOOD_COLUMNS)
    if d == "DOM-SHOP":
        return list(ORDER_ADDRESS_COLUMNS) + list(ORDER_SHOP_FULFILL_COLUMNS)
    if d == "DOM-HOTEL":
        return list(ORDER_RESERVATION_LINK_COLUMNS)
    if d == "DOM-CARRENT":
        return list(ORDER_RESERVATION_LINK_COLUMNS)
    if d == "DOM-GENERIC":
        cols = list(ORDER_ADDRESS_COLUMNS) + list(ORDER_SHOP_FULFILL_COLUMNS)
        if "ARCH-RESERVE" in arches:
            cols = cols + list(ORDER_RESERVATION_LINK_COLUMNS)
        return cols
    # 其他带订单的域：按商城履约，不含餐饮口味/预约外键
    return list(ORDER_ADDRESS_COLUMNS) + list(ORDER_SHOP_FULFILL_COLUMNS)


# 预约办结评价列（由 schema.entities.reservation.allowRating 注入，不进域固有超集）
RESERVATION_RATING_COLUMNS: list[tuple[str, str]] = [
    ("rating", "INT NULL"),
    ("rating_remark", "VARCHAR(255) NOT NULL DEFAULT ''"),
    ("rated_at", "DATETIME NULL"),
]
_RESERVATION_RATING_NAMES = {n.lower() for n, _ in RESERVATION_RATING_COLUMNS}


def ensure_shared_sql_columns(
    sql: str,
    *,
    domain: str = "",
    archetypes: list[str] | None = None,
    staff: bool = True,
    loyalty: bool = False,
    loyalty_caps: set[str] | frozenset[str] | None = None,
    reservation_flags: dict | None = None,
    trade_extra_columns: list[tuple[str, str]] | None = None,
) -> str:
    """对 reservation / 订单表 / sys_user 补齐共享列。

    预约/订单履约列均按 domain（及 GENERIC 的 archetype）注入并剔除跨域字段。
    交易加厚列由调用方按扫词闸传入 trade_extra_columns。
    忠诚度列按 cap 拆：仅 wallet 默认时不灌 points/会员/券列。
    售后宽列：交易三域 A 壳全套；其它有单域只保留 completed_at。
    """
    caps = _loyalty_caps_set(loyalty, loyalty_caps)
    user_loyalty_cols = loyalty_user_columns_for(caps)
    order_loyalty_cols = loyalty_order_columns_for(caps)
    refund_cols = order_refund_columns_for(domain)
    want_ledger = "wallet" in caps

    resv_cols = list(RESERVATION_COLUMNS_BY_DOMAIN.get(domain or "", []))
    resv_allow = {n.lower() for n, _ in resv_cols}
    rf = reservation_flags if isinstance(reservation_flags, dict) else {}
    if rf.get("allowRating"):
        resv_cols = list(resv_cols) + list(RESERVATION_RATING_COLUMNS)
        resv_allow |= _RESERVATION_RATING_NAMES
    known_resv = _RESERVATION_EXTRA_NAMES | _RESERVATION_RATING_NAMES
    order_fulfill = order_fulfill_columns_for(domain, archetypes)
    trade_extra = list(trade_extra_columns or [])
    order_allow = {n.lower() for n, _ in order_fulfill} | {
        n.lower() for n, _ in refund_cols
    } | {n.lower() for n, _ in order_loyalty_cols} | {
        n.lower() for n, _ in trade_extra
    }
    user_loyalty_allow = {n.lower() for n, _ in user_loyalty_cols}

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        t = table.lower()
        if t == "reservation":
            body = _prune_columns(
                body, allow=resv_allow, known=known_resv
            )
            if resv_cols:
                body = _inject_missing_columns(body, resv_cols)
        elif t in ("biz_order", "shop_order", "food_order", "hotel_order", "orders"):
            body = _prune_columns(
                body,
                allow=order_allow,
                known=(
                    _ORDER_FULFILL_NAMES
                    | _ORDER_LOYALTY_NAMES
                    | _ORDER_REFUND_NAMES
                    | _ORDER_TRADE_EXTRA_NAMES
                ),
            )
            cols = list(order_fulfill) + list(refund_cols)
            if order_loyalty_cols:
                cols = cols + list(order_loyalty_cols)
            if trade_extra:
                cols = cols + list(trade_extra)
            body = _inject_missing_columns(body, cols)
        elif t == "sys_user":
            body = _prune_columns(
                body, allow=user_loyalty_allow, known=_SYS_USER_LOYALTY_NAMES
            )
            cols: list[tuple[str, str]] = []
            if staff:
                cols.extend(SYS_USER_STAFF_COLUMNS)
            if user_loyalty_cols:
                cols.extend(user_loyalty_cols)
            if cols:
                body = _inject_missing_columns(body, cols)
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(repl, sql)
    if not want_ledger:
        out = re.sub(
            r"CREATE TABLE IF NOT EXISTS\s+`?user_ledger`?\s*\((?:.|\n)*?\);\s*",
            "",
            out,
            flags=re.IGNORECASE,
        )
    elif "user_ledger" not in out.lower():
        out = out.rstrip() + "\n" + _USER_LEDGER_DDL
    return out


_TICKET_PROGRESS_DDL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  status VARCHAR(32) NOT NULL,
  operator VARCHAR(64),
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_progress_ticket (ticket_id, id)
);
"""

def ensure_guestbook_sql(
    sql: str,
    *,
    enabled: bool,
    with_channel: bool = False,
) -> str:
    """委托 features.guestbook.ensure_guestbook_sql（正文只在 features）。"""
    from app.bake.features.guestbook import ensure_guestbook_sql as _ensure

    return _ensure(sql, enabled=enabled, with_channel=with_channel)

def ensure_item_comment_sql(sql: str, *, enabled: bool) -> str:
    """委托 features.item_comment.ensure_item_comment_sql（正文只在 features）。"""
    from app.bake.features.item_comment import ensure_item_comment_sql as _ensure

    return _ensure(sql, enabled=enabled)

def ensure_ai_assistant_sql(
    sql: str,
    *,
    enabled: bool,
    domain: str = "",
    title: str = "",
    proposal_text: str = "",
    capabilities: list | None = None,
) -> str:
    """委托 features.ai_assistant（FAQ 与 category/ticket_type 同字）。"""
    from app.bake.features.ai_assistant import ensure_ai_assistant_sql as _ensure

    return _ensure(
        sql,
        enabled=enabled,
        domain=domain,
        title=title,
        proposal_text=proposal_text,
        capabilities=capabilities,
    )

def ensure_exam_wrongbook_sql(sql: str, *, enabled: bool) -> str:
    """委托 features.exam.ensure_exam_wrongbook_sql（正文只在 features）。"""
    from app.bake.features.exam import ensure_exam_wrongbook_sql as _ensure

    return _ensure(sql, enabled=enabled)

def ensure_vote_sql(sql: str, *, enabled: bool, seed_activity: bool = False) -> str:
    """委托 features.vote.ensure_vote_sql（正文只在 features）。"""
    from app.bake.features.vote import ensure_vote_sql as _ensure

    return _ensure(sql, enabled=enabled, seed_activity=seed_activity)


def ensure_exam_core_sql(sql: str, *, enabled: bool, gate_ticket: bool = False) -> str:
    """委托 features.exam.ensure_exam_core_sql（正文只在 features）。"""
    from app.bake.features.exam import ensure_exam_core_sql as _ensure

    return _ensure(sql, enabled=enabled, gate_ticket=gate_ticket)


def ensure_dm_sql(sql: str, *, enabled: bool) -> str:
    """委托 features.dm.ensure_dm_sql（正文只在 features）。"""
    from app.bake.features.dm import ensure_dm_sql as _ensure

    return _ensure(sql, enabled=enabled)

def ensure_favorites_sql(sql: str, *, enabled: bool) -> str:
    """委托 features.favorites.ensure_favorites_sql（正文只在 features）。"""
    from app.bake.features.favorites import ensure_favorites_sql as _ensure

    return _ensure(sql, enabled=enabled)


def ensure_post_like_sql(sql: str, *, enabled: bool, item_table: str | None = None) -> str:
    """委托 features.favorites.ensure_post_like_sql（正文只在 features）。"""
    from app.bake.features.favorites import ensure_post_like_sql as _ensure

    return _ensure(sql, enabled=enabled, item_table=item_table)


def ensure_content_report_sql(sql: str, *, enabled: bool) -> str:
    """委托 features.favorites.ensure_content_report_sql（正文只在 features）。"""
    from app.bake.features.favorites import ensure_content_report_sql as _ensure

    return _ensure(sql, enabled=enabled)

def ensure_staff_roster_sql(sql: str, *, enabled: bool) -> str:
    """委托 features.staff_roster.ensure_staff_roster_sql（正文只在 features）。"""
    from app.bake.features.staff_roster import ensure_staff_roster_sql as _ensure

    return _ensure(sql, enabled=enabled)

def ensure_message_template_sql(sql: str, *, enabled: bool) -> str:
    """委托 features.message_template.ensure_message_template_sql（正文只在 features）。"""
    from app.bake.features.message_template import ensure_message_template_sql as _ensure

    return _ensure(sql, enabled=enabled)

def ensure_book_suggest_sql(sql: str, *, enabled: bool) -> str:
    """委托 features.book_suggest.ensure_book_suggest_sql（正文只在 features）。"""
    from app.bake.features.book_suggest import ensure_book_suggest_sql as _ensure

    return _ensure(sql, enabled=enabled)

def ensure_parcel_ship_sql(sql: str, *, enabled: bool) -> str:
    """委托 features.parcel_ship.ensure_parcel_ship_sql（正文只在 features）。"""
    from app.bake.features.parcel_ship import ensure_parcel_ship_sql as _ensure

    return _ensure(sql, enabled=enabled)

def ensure_audit_log_sql(sql: str, *, enabled: bool) -> str:
    """委托 features.audit_log.ensure_audit_log_sql（正文只在 features）。"""
    from app.bake.features.audit_log import ensure_audit_log_sql as _ensure

    return _ensure(sql, enabled=enabled)

def ensure_browse_history_sql(sql: str, *, enabled: bool) -> str:
    """委托 features.favorites.ensure_browse_history_sql（正文只在 features）。"""
    from app.bake.features.favorites import ensure_browse_history_sql as _ensure

    return _ensure(sql, enabled=enabled)

def ensure_archive_log_sql(sql: str, *, enabled: bool) -> str:
    """委托 features.archive_log.ensure_archive_log_sql（正文只在 features）。"""
    from app.bake.features.archive_log import ensure_archive_log_sql as _ensure

    return _ensure(sql, enabled=enabled)


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

# LISTING 专用：挂牌价列（API 键 priceYuan/priceUnit，禁止其它跟进域乱挂）
FOLLOW_LISTING_EXTRA_COLUMNS: list[tuple[str, str]] = [
    ("price", "DECIMAL(12,2) NULL"),
    ("price_unit", "VARCHAR(16) DEFAULT ''"),
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
        cols = list(FOLLOW_ARCHIVE_COLUMNS)
        if (domain or "") == "DOM-LISTING":
            cols.extend(FOLLOW_LISTING_EXTRA_COLUMNS)
        body = _inject_missing_columns(body, cols)
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
        ("volunteer_role", "VARCHAR(64) DEFAULT ''"),
        ("admit_mode", "VARCHAR(32) DEFAULT '先到先得'"),
        ("seat_zones", "VARCHAR(255) DEFAULT ''"),
        ("pin_top", "TINYINT NOT NULL DEFAULT 0"),
        ("survey_form_id", "BIGINT NULL"),
    ],
    "DOM-LOST": [
        ("expire_on", "VARCHAR(32) DEFAULT ''"),
        ("bounty_note", "VARCHAR(128) DEFAULT ''"),
        ("stage", "VARCHAR(32) DEFAULT '招领中'"),
        ("lost_category", "VARCHAR(32) DEFAULT ''"),
        ("view_count", "INT NOT NULL DEFAULT 0"),
        ("fee_yuan", "DECIMAL(10,2) NULL"),
        ("pin_top", "TINYINT NOT NULL DEFAULT 0"),
    ],
    "DOM-COURSE": [
        ("textbook", "VARCHAR(255) DEFAULT ''"),
        ("course_kind", "VARCHAR(16) DEFAULT ''"),
        ("prereq_code", "VARCHAR(64) DEFAULT ''"),
        ("college", "VARCHAR(64) DEFAULT ''"),
        ("plan_url", "VARCHAR(255) DEFAULT ''"),
        ("allowed_gender", "VARCHAR(16) DEFAULT ''"),
        ("allowed_grades", "VARCHAR(64) DEFAULT ''"),
        ("stage", "VARCHAR(32) DEFAULT '开放'"),
        ("admit_mode", "VARCHAR(32) DEFAULT '先到先得'"),
        ("pin_top", "TINYINT NOT NULL DEFAULT 0"),
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
        ("weather_note", "TEXT NULL"),
        ("pin_top", "TINYINT NOT NULL DEFAULT 0"),
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
    """委托 features.detail_attrs.ensure_detail_attrs_sql（正文只在 features）。"""
    from app.bake.features.detail_attrs import ensure_detail_attrs_sql as _ensure

    return _ensure(sql, enabled=enabled, item_table=item_table, attr_fields=attr_fields, attr_keys=attr_keys)


def ensure_gallery_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    """委托 features.detail_attrs.ensure_gallery_sql（正文只在 features）。"""
    from app.bake.features.detail_attrs import ensure_gallery_sql as _ensure

    return _ensure(sql, enabled=enabled, item_table=item_table)


def ensure_room_equipment_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    """委托 features.room_equipment.ensure_room_equipment_sql（正文只在 features）。"""
    from app.bake.features.room_equipment import ensure_room_equipment_sql as _ensure

    return _ensure(sql, enabled=enabled, item_table=item_table)


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

def ensure_flash_price_columns(sql: str, *, enabled: bool, item_table: str | None) -> str:
    """委托 features.order_extras.ensure_flash_price_columns（正文只在 features）。"""
    from app.bake.features.order_extras import ensure_flash_price_columns as _ensure

    return _ensure(sql, enabled=enabled, item_table=item_table)

def ensure_product_spec_columns(sql: str, *, enabled: bool, item_table: str | None) -> str:
    """委托 features.product_spec.ensure_product_spec_columns（正文只在 features）。"""
    from app.bake.features.product_spec import ensure_product_spec_columns as _ensure

    return _ensure(sql, enabled=enabled, item_table=item_table)

def ensure_multi_category_sql(
    sql: str,
    *,
    enabled: bool,
    item_table: str | None = "product",
    junction_table: str = "product_category",
    axis_seed_sql: str = "",
) -> str:
    """委托 features.multi_category.ensure_multi_category_sql（正文只在 features）。"""
    from app.bake.features.multi_category import ensure_multi_category_sql as _ensure

    return _ensure(sql, enabled=enabled, item_table=item_table, junction_table=junction_table, axis_seed_sql=axis_seed_sql)


def ensure_product_tags_sql(sql: str, *, enabled: bool) -> str:
    """委托 features.product_tags.ensure_product_tags_sql（正文只在 features）。"""
    from app.bake.features.product_tags import ensure_product_tags_sql as _ensure

    return _ensure(sql, enabled=enabled)

def ensure_order_line_custom_columns(sql: str, *, enabled: bool, with_spec: bool = False) -> str:
    """委托 features.line_custom.ensure_order_line_custom_columns（正文只在 features）。"""
    from app.bake.features.line_custom import ensure_order_line_custom_columns as _ensure

    return _ensure(sql, enabled=enabled, with_spec=with_spec)

def ensure_delivery_window_sql(sql: str, *, enabled: bool) -> str:
    """委托 features.delivery_window.ensure_delivery_window_sql（正文只在 features）。"""
    from app.bake.features.delivery_window import ensure_delivery_window_sql as _ensure

    return _ensure(sql, enabled=enabled)

def ensure_purchase_gate_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    """委托 features.purchase_gate.ensure_purchase_gate_sql（正文只在 features）。"""
    from app.bake.features.purchase_gate import ensure_purchase_gate_sql as _ensure

    return _ensure(sql, enabled=enabled, item_table=item_table)

def ensure_group_buy_sql(sql: str, *, enabled: bool) -> str:
    """委托 features.group_buy.ensure_group_buy_sql（正文只在 features）。"""
    from app.bake.features.group_buy import ensure_group_buy_sql as _ensure

    return _ensure(sql, enabled=enabled)

def ensure_blind_box_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    """委托 features.blind_box.ensure_blind_box_sql（正文只在 features）。"""
    from app.bake.features.blind_box import ensure_blind_box_sql as _ensure

    return _ensure(sql, enabled=enabled, item_table=item_table)

def ensure_consign_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    """委托 features.consign.ensure_consign_sql（正文只在 features）。"""
    from app.bake.features.consign import ensure_consign_sql as _ensure

    return _ensure(sql, enabled=enabled, item_table=item_table)

def ensure_weigh_sale_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    """委托 features.weigh_sale.ensure_weigh_sale_sql（正文只在 features）。"""
    from app.bake.features.weigh_sale import ensure_weigh_sale_sql as _ensure

    return _ensure(sql, enabled=enabled, item_table=item_table)

def ensure_shoot_sql(sql: str, *, enabled: bool) -> str:
    """委托 features.shoot.ensure_shoot_sql（正文只在 features）。"""
    from app.bake.features.shoot import ensure_shoot_sql as _ensure

    return _ensure(sql, enabled=enabled)

def ensure_boarding_sql(sql: str, *, enabled: bool) -> str:
    """委托 features.boarding.ensure_boarding_sql（正文只在 features）。"""
    from app.bake.features.boarding import ensure_boarding_sql as _ensure

    return _ensure(sql, enabled=enabled)

def ensure_venue_clean_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    """委托 features.venue_clean.ensure_venue_clean_sql（正文只在 features）。"""
    from app.bake.features.venue_clean import ensure_venue_clean_sql as _ensure

    return _ensure(sql, enabled=enabled, item_table=item_table)


def ensure_room_board_sql(sql: str, *, enabled: bool) -> str:
    """委托 features.room_board.ensure_room_board_sql（正文只在 features）。"""
    from app.bake.features.room_board import ensure_room_board_sql as _ensure

    return _ensure(sql, enabled=enabled)


def ensure_front_desk_sql(sql: str, *, enabled: bool) -> str:
    """委托 features.front_desk.ensure_front_desk_sql（正文只在 features）。"""
    from app.bake.features.front_desk import ensure_front_desk_sql as _ensure

    return _ensure(sql, enabled=enabled)

def ensure_rental_bond_sql(sql: str, *, enabled: bool, item_table: str | None = "vehicle") -> str:
    """委托 features.rental_bond.ensure_rental_bond_sql（正文只在 features）。"""
    from app.bake.features.rental_bond import ensure_rental_bond_sql as _ensure

    return _ensure(sql, enabled=enabled, item_table=item_table)


# 正文在 features/digital_goods.py；此处只转发，避免双份 ensure。
from app.bake.features.digital_goods import (  # noqa: E402
    PRODUCT_DIGITAL_COLUMNS,
    ensure_digital_goods_sql,
)

def ensure_buyback_sql(sql: str, *, enabled: bool) -> str:
    """委托 features.buyback.ensure_buyback_sql（正文只在 features）。"""
    from app.bake.features.buyback import ensure_buyback_sql as _ensure

    return _ensure(sql, enabled=enabled)

def ensure_lesson_pack_sql(sql: str, *, enabled: bool) -> str:
    """委托 features.lesson_pack.ensure_lesson_pack_sql（正文只在 features）。"""
    from app.bake.features.lesson_pack import ensure_lesson_pack_sql as _ensure

    return _ensure(sql, enabled=enabled)


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

def ensure_coupon_lifecycle_sql(sql: str, *, enabled: bool) -> str:
    """委托 features.order_extras.ensure_coupon_lifecycle_sql（正文只在 features）。"""
    from app.bake.features.order_extras import ensure_coupon_lifecycle_sql as _ensure

    return _ensure(sql, enabled=enabled)


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
    """委托 features.order_extras.ensure_order_review_sql（正文只在 features）。"""
    from app.bake.features.order_extras import ensure_order_review_sql as _ensure

    return _ensure(sql, enabled=enabled)

def ensure_stock_io_sql(sql: str, *, enabled: bool) -> str:
    """委托 features.stock_io.ensure_stock_io_sql（正文只在 features）。"""
    from app.bake.features.stock_io import ensure_stock_io_sql as _ensure

    return _ensure(sql, enabled=enabled)

def ensure_scrap_request_sql(sql: str, *, enabled: bool) -> str:
    """委托 features.stock_scrap.ensure_scrap_request_sql（正文只在 features）。"""
    from app.bake.features.stock_scrap import ensure_scrap_request_sql as _ensure

    return _ensure(sql, enabled=enabled)

def ensure_e_sign_sql(sql: str, *, enabled: bool) -> str:
    """委托 features.e_sign.ensure_e_sign_sql（正文只在 features）。"""
    from app.bake.features.e_sign import ensure_e_sign_sql as _ensure

    return _ensure(sql, enabled=enabled)

def ensure_balance_ledger_sql(sql: str, *, enabled: bool, domain: str = "") -> str:
    """委托 features.timebank.ensure_balance_ledger_sql（正文只在 features）。"""
    from app.bake.features.timebank import ensure_balance_ledger_sql as _ensure

    return _ensure(sql, enabled=enabled, domain=domain)


_OCCUPY_SPAN_DDL = """
CREATE TABLE IF NOT EXISTS resource_occupy (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  item_id BIGINT NULL,
  ticket_id BIGINT NULL,
  title VARCHAR(200) DEFAULT '',
  period_start DATETIME NOT NULL,
  period_end DATETIME NOT NULL,
  status VARCHAR(32) DEFAULT 'active',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_occupy_user (username, period_start),
  KEY idx_occupy_ticket (ticket_id)
);

CREATE TABLE IF NOT EXISTS occupy_block (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  period_start DATETIME NOT NULL,
  period_end DATETIME NOT NULL,
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS occupy_day_stat (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  day_key VARCHAR(16) NOT NULL,
  occupy_count INT NOT NULL DEFAULT 0,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_occupy_day (day_key)
);
"""


def ensure_occupy_span_sql(sql: str, *, enabled: bool) -> str:
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?resource_occupy`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _OCCUPY_SPAN_DDL


_MATERIAL_CHECK_DDL = """
CREATE TABLE IF NOT EXISTS material_checklist (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(120) NOT NULL,
  required TINYINT NOT NULL DEFAULT 1,
  sort_order INT NOT NULL DEFAULT 0,
  status VARCHAR(32) DEFAULT 'available',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ticket_material (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  checklist_id BIGINT NOT NULL,
  file_url VARCHAR(255) NOT NULL DEFAULT '',
  uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_ticket_material_ticket (ticket_id)
);

CREATE TABLE IF NOT EXISTS material_template (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(120) NOT NULL,
  sample_url VARCHAR(255) DEFAULT '',
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT IGNORE INTO material_checklist (id, title, required, sort_order, status) VALUES
(1, '身份证明', 1, 1, 'available'),
(2, '申请说明附件', 1, 2, 'available');
INSERT IGNORE INTO material_template (id, title, remark) VALUES
(1, '材料模板说明', '按清单上传清晰扫描件');
"""


def ensure_material_check_sql(sql: str, *, enabled: bool) -> str:
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?material_checklist`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _MATERIAL_CHECK_DDL


_APPLY_BLACKLIST_DDL = """
CREATE TABLE IF NOT EXISTS apply_blacklist (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  reason VARCHAR(255) DEFAULT '',
  status VARCHAR(32) NOT NULL DEFAULT 'blocked',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_apply_blacklist_user (username)
);
"""


def ensure_apply_blacklist_sql(sql: str, *, enabled: bool) -> str:
    """报名黑名单轻表：管理维护，报名时拦截。"""
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?apply_blacklist`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _APPLY_BLACKLIST_DDL

def _append_ddl_if_missing(sql: str, table: str, ddl: str) -> str:
    if re.search(
        rf"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?{re.escape(table)}`?\b",
        sql,
    ):
        return sql
    return sql.rstrip() + "\n" + ddl


def ensure_borrow_structural_sql(
    sql: str,
    *,
    domain: str,
    capabilities: list[str] | None = None,
) -> str:
    """委托 features.borrow_structural.ensure_borrow_structural_sql（正文只在 features）。"""
    from app.bake.features.borrow_structural import ensure_borrow_structural_sql as _ensure

    return _ensure(sql, domain=domain, capabilities=capabilities)


# 单据可选扩展列全集（剔除名单）；注入按域 + schema.ticket 能力
TICKET_OPTIONAL_COLUMNS: list[tuple[str, str]] = [
    ("attach_url", "VARCHAR(255) NOT NULL DEFAULT ''"),
    ("rating", "INT NULL"),
    ("rating_remark", "VARCHAR(255) NOT NULL DEFAULT ''"),
    ("rated_at", "DATETIME NULL"),
    ("rating_anonymous", "TINYINT NOT NULL DEFAULT 0"),
    ("priority", "VARCHAR(16) DEFAULT '普通'"),
    ("contact_phone", "VARCHAR(20) DEFAULT ''"),
    ("fine_status", "VARCHAR(16) DEFAULT 'none'"),
    ("pickup_at", "DATETIME NULL"),
    ("pickup_place", "VARCHAR(128) DEFAULT ''"),
    ("actual_qty", "INT NULL"),
    ("contact_channel", "VARCHAR(32) DEFAULT ''"),
    ("next_follow_at", "DATETIME NULL"),
    ("meet_intent", "VARCHAR(32) DEFAULT ''"),
    ("seat_locked", "TINYINT NOT NULL DEFAULT 0"),
    ("no_show", "TINYINT NOT NULL DEFAULT 0"),
    ("cancel_reason", "VARCHAR(255) NOT NULL DEFAULT ''"),
    ("checked_in_at", "DATETIME NULL"),
    ("pass_code", "VARCHAR(32) DEFAULT ''"),
    ("renew_count", "INT NOT NULL DEFAULT 0"),
    ("hold_expire_at", "DATETIME NULL"),
    ("qty", "INT NOT NULL DEFAULT 1"),
    ("period_start", "DATETIME NULL"),
    ("period_end", "DATETIME NULL"),
    ("leave_days", "INT NULL"),
    ("week_no", "INT NULL"),
    ("interview_place", "VARCHAR(128) DEFAULT ''"),
    ("proxy_name", "VARCHAR(64) DEFAULT ''"),
    ("proxy_phone", "VARCHAR(20) DEFAULT ''"),
    ("exception_reason", "VARCHAR(128) DEFAULT ''"),
    ("damage_claim_note", "VARCHAR(255) DEFAULT ''"),
    ("deposit_yuan", "DECIMAL(10,2) NULL"),
    ("notice_ack", "TINYINT NOT NULL DEFAULT 0"),
    ("emergency_contact", "VARCHAR(64) DEFAULT ''"),
    ("emergency_phone", "VARCHAR(20) DEFAULT ''"),
    ("due_soon_notified_at", "DATETIME NULL"),
    ("ever_overdue", "TINYINT NOT NULL DEFAULT 0"),
    ("project_no", "VARCHAR(64) DEFAULT ''"),
    ("procure_ref_no", "VARCHAR(64) DEFAULT ''"),
    ("dual_reviewer_a", "VARCHAR(64) DEFAULT ''"),
    ("dual_reviewer_b", "VARCHAR(64) DEFAULT ''"),
    ("ship_fee_yuan", "DECIMAL(10,2) NULL"),
    ("utility_note", "VARCHAR(255) DEFAULT ''"),
    ("insurance_ack", "TINYINT NOT NULL DEFAULT 0"),
    ("meeting_ack", "TINYINT NOT NULL DEFAULT 0"),
    ("owner_meeting_ack", "TINYINT NOT NULL DEFAULT 0"),
    ("price_note_ack", "TINYINT NOT NULL DEFAULT 0"),
    ("sponsor_ack", "TINYINT NOT NULL DEFAULT 0"),
    ("plan_ack", "TINYINT NOT NULL DEFAULT 0"),
    ("prereq_ack", "TINYINT NOT NULL DEFAULT 0"),
    ("late_minutes", "INT NULL"),
    ("wish_order", "TINYINT NULL"),
    ("volunteer_role", "VARCHAR(64) DEFAULT ''"),
    ("tour_notice_ack", "TINYINT NOT NULL DEFAULT 0"),
    ("seat_zone", "VARCHAR(64) DEFAULT ''"),
    ("post_gallery_json", "TEXT NULL"),
    ("credit_writeback_ack", "TINYINT NOT NULL DEFAULT 0"),
    ("peer_username", "VARCHAR(64) DEFAULT ''"),
    ("peer_ack", "TINYINT NOT NULL DEFAULT 0"),
    ("interview_result", "VARCHAR(16) DEFAULT ''"),
    ("written_score", "DECIMAL(10,2) NULL"),
    ("bg_check_note", "VARCHAR(255) DEFAULT ''"),
    ("deal_amount_yuan", "DECIMAL(12,2) NULL"),
    ("next_action", "VARCHAR(255) DEFAULT ''"),
    ("next_action_done", "TINYINT NOT NULL DEFAULT 0"),
    ("return_date", "VARCHAR(32) DEFAULT ''"),
    ("defense_result", "VARCHAR(32) DEFAULT ''"),
    ("bank_account", "VARCHAR(64) DEFAULT ''"),
    ("disburse_batch", "VARCHAR(64) DEFAULT ''"),
    ("close_attach_url", "VARCHAR(255) DEFAULT ''"),
    ("assign_dept", "VARCHAR(64) DEFAULT ''"),
    ("confidential", "TINYINT NOT NULL DEFAULT 0"),
    ("appraisal_comment", "VARCHAR(512) DEFAULT ''"),
    ("appraisal_grade", "VARCHAR(16) DEFAULT ''"),
    ("company_eval", "VARCHAR(512) DEFAULT ''"),
    ("excellent_mark", "TINYINT NOT NULL DEFAULT 0"),
    ("revise_count", "INT NOT NULL DEFAULT 0"),
    ("feedback_interest", "VARCHAR(128) DEFAULT ''"),
    ("feedback_concern", "VARCHAR(255) DEFAULT ''"),
    ("feedback_next", "VARCHAR(255) DEFAULT ''"),
    ("record_url", "VARCHAR(255) DEFAULT ''"),
    ("follow_soon_notified_at", "DATETIME NULL"),
    ("urge_at", "DATETIME NULL"),
    ("urge_count", "INT NOT NULL DEFAULT 0"),
    ("urge_cancelled", "TINYINT NOT NULL DEFAULT 0"),
    ("fault_reason", "VARCHAR(64) DEFAULT ''"),
    ("close_summary", "VARCHAR(512) DEFAULT ''"),
    ("preferred_slot", "VARCHAR(64) DEFAULT ''"),
    ("response_due_at", "DATETIME NULL"),
    ("night_urgent", "TINYINT NOT NULL DEFAULT 0"),
    ("address_type", "VARCHAR(16) DEFAULT ''"),
    ("helper_username", "VARCHAR(64) DEFAULT ''"),
    ("quote_yuan", "DECIMAL(10,2) NULL"),
    ("quote_confirmed", "TINYINT NOT NULL DEFAULT 0"),
    ("material_fee_yuan", "DECIMAL(10,2) NULL"),
    ("material_paid", "TINYINT NOT NULL DEFAULT 0"),
    ("hold_reason", "VARCHAR(255) DEFAULT ''"),
    ("asset_code", "VARCHAR(64) DEFAULT ''"),
    ("remote_url", "VARCHAR(255) DEFAULT ''"),
    ("skill_tag", "VARCHAR(64) DEFAULT ''"),
    ("route_note", "VARCHAR(255) DEFAULT ''"),
    ("parent_ticket_id", "BIGINT NULL"),
    ("subscribe_progress", "TINYINT NOT NULL DEFAULT 0"),
    ("audio_url", "VARCHAR(255) DEFAULT ''"),
    ("rating_tags", "VARCHAR(255) DEFAULT ''"),
    ("follow_rated", "TINYINT NOT NULL DEFAULT 0"),
    ("parts_note", "VARCHAR(255) DEFAULT ''"),
    ("serial_no", "VARCHAR(64) DEFAULT ''"),
    ("visit_due_at", "DATETIME NULL"),
    ("knowledge_deposit", "TINYINT NOT NULL DEFAULT 0"),
    ("rank_scope", "VARCHAR(16) DEFAULT ''"),
    ("objection_due_at", "DATETIME NULL"),
    ("objection_note", "VARCHAR(255) DEFAULT ''"),
    ("objection_at", "DATETIME NULL"),
    ("cc_usernames", "VARCHAR(512) DEFAULT ''"),
    ("approve_attach_url", "VARCHAR(255) DEFAULT ''"),
    ("pickup_method", "VARCHAR(16) DEFAULT ''"),
    ("mail_address", "VARCHAR(255) DEFAULT ''"),
    ("express_no", "VARCHAR(64) DEFAULT ''"),
    ("cert_urgent", "TINYINT NOT NULL DEFAULT 0"),
    ("seal_copies", "INT NULL"),
    ("bind_note", "VARCHAR(255) DEFAULT ''"),
    ("seal_copy_nos", "VARCHAR(255) DEFAULT ''"),
    ("seal_witness_ack", "TINYINT NOT NULL DEFAULT 0"),
    ("mileage_km", "DECIMAL(10,1) NULL"),
    ("fuel_note", "VARCHAR(255) DEFAULT ''"),
    ("invoice_count", "INT NULL"),
    ("visitor_count", "INT NULL"),
    ("award_cert_no", "VARCHAR(64) DEFAULT ''"),
    ("vendor_quotes", "TEXT NULL"),
    ("comp_hours", "DECIMAL(10,1) NULL"),
    ("driver_name", "VARCHAR(64) DEFAULT ''"),
    ("passenger_names", "VARCHAR(255) DEFAULT ''"),
    ("pass_expire_at", "DATETIME NULL"),
    ("return_fuel", "DECIMAL(10,1) NULL"),
    ("labor_place", "VARCHAR(128) DEFAULT ''"),
    ("effective_on", "VARCHAR(32) DEFAULT ''"),
    ("cert_issue_no", "VARCHAR(64) DEFAULT ''"),
    ("doc_rev", "VARCHAR(32) DEFAULT ''"),
    ("work_start", "VARCHAR(8) DEFAULT ''"),
    ("work_end", "VARCHAR(8) DEFAULT ''"),
    ("issue_copies", "INT NULL"),
    ("sign_parties", "VARCHAR(255) DEFAULT ''"),
    ("train_hours", "DECIMAL(10,1) NULL"),
    ("member_change_note", "VARCHAR(512) DEFAULT ''"),
    ("procure_amount", "DECIMAL(12,2) NULL"),
    ("exception_type", "VARCHAR(32) DEFAULT ''"),
    ("visit_purpose", "VARCHAR(32) DEFAULT ''"),
    ("violation_person", "VARCHAR(64) DEFAULT ''"),
    ("rectify_note", "VARCHAR(512) DEFAULT ''"),
    ("return_fail", "TINYINT NOT NULL DEFAULT 0"),
    ("return_note", "VARCHAR(512) DEFAULT ''"),
    ("fund_use_yuan", "DECIMAL(12,2) NULL"),
    ("fund_use_note", "VARCHAR(512) DEFAULT ''"),
    ("visit_on", "VARCHAR(32) DEFAULT ''"),
    ("plagiarism_url", "VARCHAR(512) DEFAULT ''"),
    ("party_stage", "VARCHAR(32) DEFAULT ''"),
    ("stage_on", "VARCHAR(32) DEFAULT ''"),
    ("observe_on", "VARCHAR(32) DEFAULT ''"),
    ("observe_note", "VARCHAR(512) DEFAULT ''"),
    ("schedule_impact_note", "VARCHAR(512) DEFAULT ''"),
    ("contract_amount", "DECIMAL(12,2) NULL"),
    ("change_log_note", "VARCHAR(512) DEFAULT ''"),
    ("verify_code", "VARCHAR(32) DEFAULT ''"),
    ("walk_in", "TINYINT NOT NULL DEFAULT 0"),
    ("checkin_proxy_by", "VARCHAR(64) DEFAULT ''"),
    ("parking_on", "VARCHAR(32) DEFAULT ''"),
    ("renew_on", "VARCHAR(32) DEFAULT ''"),
    ("renew_note", "VARCHAR(512) DEFAULT ''"),
    ("pickup_redeem_code", "VARCHAR(32) DEFAULT ''"),
    ("pickup_redeemed", "TINYINT NOT NULL DEFAULT 0"),
]

_TICKET_OPTIONAL_NAMES = {n.lower() for n, _ in TICKET_OPTIONAL_COLUMNS}
# 域固有业务列（不含 attach/rating 等能力开关列）
TICKET_DOMAIN_COLUMNS: dict[str, list[str]] = {
    "DOM-LIBRARY": ["fine_status", "due_soon_notified_at", "ever_overdue", "notice_ack"],
    "DOM-EQUIP": ["fine_status", "deposit_yuan", "notice_ack", "due_soon_notified_at", "ever_overdue", "insurance_ack", "asset_code"],
    "DOM-ASSET": ["pickup_at", "pickup_place", "actual_qty", "project_no", "procure_ref_no", "dual_reviewer_a", "dual_reviewer_b"],
    "DOM-CRM": ["contact_channel", "next_follow_at", "deal_amount_yuan", "next_action", "next_action_done", "follow_soon_notified_at"],
    "DOM-ATTEND": ["contact_channel", "next_follow_at", "leave_days", "return_date", "proxy_name"],
    "DOM-FUND": ["contact_channel", "next_follow_at", "defense_result", "bank_account", "disburse_batch"],
    "DOM-LABSAFE": ["contact_channel", "next_follow_at"],
    "DOM-RECRUIT": ["contact_channel", "next_follow_at", "interview_place", "interview_result", "written_score", "bg_check_note"],
    "DOM-DATING": ["contact_channel", "next_follow_at", "meet_intent"],
    "DOM-GRADE": ["contact_channel", "next_follow_at", "notice_ack", "rank_scope"],
    "DOM-INTERN": [
        "contact_channel", "next_follow_at", "week_no",
        "appraisal_comment", "appraisal_grade", "company_eval", "excellent_mark", "revise_count",
    ],
    "DOM-SEAL": ["contact_channel", "next_follow_at"],
    "DOM-FLEET": ["contact_channel", "next_follow_at"],
    "DOM-CERT": ["contact_channel", "next_follow_at"],
    "DOM-PROMO": ["contact_channel", "next_follow_at"],
    "DOM-FITOUT": ["contact_channel", "next_follow_at"],
    "DOM-ACAD": ["contact_channel", "next_follow_at"],
    "DOM-TRIP": ["contact_channel", "next_follow_at"],
    "DOM-EXPENSE": ["contact_channel", "next_follow_at"],
    "DOM-CREDIT": ["contact_channel", "next_follow_at"],
    "DOM-LABOR": ["contact_channel", "next_follow_at"],
    "DOM-EVAL": [
        "contact_channel", "next_follow_at",
        "rating", "rating_remark", "rated_at", "rating_anonymous",
    ],
    "DOM-MORAL": ["contact_channel", "next_follow_at"],
    "DOM-AWARD": ["contact_channel", "next_follow_at"],
    "DOM-BED": [
        "contact_channel",
        "next_follow_at",
        "notice_ack",
        "deposit_yuan",
        "utility_note",
        "peer_username",
        "peer_ack",
    ],
    "DOM-CHECKIN": ["contact_channel", "next_follow_at"],
    "DOM-MUTUAL-TUTOR": ["contact_channel", "next_follow_at"],
    "DOM-MUTUAL-TOPIC": ["contact_channel", "next_follow_at"],
    "DOM-MUTUAL-TEAM": ["contact_channel", "next_follow_at"],
    "DOM-VISITOR": ["contact_channel", "next_follow_at"],
    "DOM-CARPASS": ["contact_channel", "next_follow_at"],
    "DOM-LISTING": [
        "contact_channel", "next_follow_at", "follow_soon_notified_at",
        "feedback_interest", "feedback_concern", "feedback_next", "record_url",
    ],
    "DOM-CARPOOL": ["contact_channel", "next_follow_at", "seat_locked", "no_show", "cancel_reason"],
    "DOM-TOUR": [
        "contact_channel",
        "next_follow_at",
        "notice_ack",
        "emergency_contact",
        "emergency_phone",
    ],
    "DOM-TIMEBANK": ["contact_channel", "next_follow_at"],
    "DOM-PROCURE": ["contact_channel", "next_follow_at"],
    "DOM-CLUB": ["contact_channel", "next_follow_at"],
    "DOM-PROJ": ["contact_channel", "next_follow_at"],
    "DOM-ETHIC": ["contact_channel", "next_follow_at"],
    "DOM-PARTY": ["contact_channel", "next_follow_at"],
    "DOM-CONTRACT": ["contact_channel", "next_follow_at"],
    "DOM-INSTRUMENT": ["contact_channel", "next_follow_at", "fine_status"],
    "DOM-EVENT": [
        "contact_channel", "next_follow_at", "close_attach_url", "assign_dept", "confidential",
    ],
    "DOM-DORM": [
        "priority", "contact_phone",
        "urge_at", "urge_count", "urge_cancelled",
        "fault_reason", "close_summary", "preferred_slot", "response_due_at",
        "night_urgent", "address_type", "helper_username",
        "hold_reason", "subscribe_progress", "audio_url", "rating_tags",
        "follow_rated", "route_note", "skill_tag", "visit_due_at",
        "close_attach_url",
    ],
    "DOM-PROPERTY": [
        "priority", "contact_phone",
        "urge_at", "urge_count", "urge_cancelled",
        "fault_reason", "close_summary", "preferred_slot", "response_due_at",
        "night_urgent", "address_type", "helper_username",
        "hold_reason", "subscribe_progress", "audio_url", "rating_tags",
        "follow_rated", "route_note", "skill_tag", "visit_due_at",
        "parts_note", "serial_no", "close_attach_url",
    ],
    "DOM-IT": [
        "priority", "contact_phone",
        "urge_at", "urge_count", "urge_cancelled",
        "fault_reason", "close_summary", "preferred_slot", "response_due_at",
        "night_urgent", "helper_username",
        "hold_reason", "subscribe_progress", "audio_url", "rating_tags",
        "follow_rated", "route_note", "skill_tag", "visit_due_at",
        "parts_note", "serial_no", "asset_code", "remote_url", "close_attach_url",
    ],
    "DOM-LOST": ["fine_status", "pickup_at", "pickup_place", "preferred_slot", "notice_ack"],
    "DOM-PARCEL": [
        "fine_status",
        "pickup_at",
        "pickup_place",
        "proxy_name",
        "proxy_phone",
        "exception_reason",
        "damage_claim_note",
        "notice_ack",
        "ship_fee_yuan",
    ],
    "DOM-ACTIVITY": ["notice_ack"],
    "DOM-COURSE": ["notice_ack"],
    "DOM-FORUM": [],
}


def _ticket_flag_column_names(flags: dict | None) -> list[str]:
    """由 schema.entities.ticket 能力开关推导列名。"""
    f = flags or {}
    names: list[str] = []
    if f.get("requireAttach"):
        names.append("attach_url")
    if f.get("allowRating"):
        names.extend(["rating", "rating_remark", "rated_at"])
        if f.get("ratingDims"):
            names.append("rating_anonymous")
    if f.get("allowQty"):
        names.append("qty")
    if f.get("pickDateRange"):
        names.extend(["period_start", "period_end"])
    if f.get("allowCheckin"):
        names.append("checked_in_at")
    if f.get("issuePassCode"):
        names.append("pass_code")
    if f.get("allowPassExpire"):
        names.append("pass_expire_at")
        if "pass_code" not in names:
            names.append("pass_code")
    if f.get("allowRenew"):
        names.append("renew_count")
    if f.get("allowBookHold"):
        names.append("hold_expire_at")
    if f.get("noShowAfterEnd") or f.get("fineLabel"):
        names.append("fine_status")
    if f.get("allowProxyPickup"):
        names.extend(["proxy_name", "proxy_phone"])
    if f.get("allowExceptionClose"):
        names.extend(["exception_reason", "damage_claim_note"])
    if f.get("allowDeposit"):
        names.append("deposit_yuan")
    if f.get("requireNoticeAck"):
        names.append("notice_ack")
    if f.get("preferredSlot"):
        names.append("preferred_slot")
    if f.get("allowEmergencyContact"):
        names.extend(["emergency_contact", "emergency_phone"])
    if f.get("requireInsuranceAck"):
        names.append("insurance_ack")
    if f.get("requireMeetingAck"):
        names.extend(["meeting_ack", "owner_meeting_ack"])
    if f.get("requirePriceNoteAck"):
        names.append("price_note_ack")
    if f.get("requireSponsorAck"):
        names.append("sponsor_ack")
    if f.get("requirePlanAck"):
        names.append("plan_ack")
    if f.get("requirePrereqAck"):
        names.append("prereq_ack")
    if f.get("allowLateMinutes"):
        names.append("late_minutes")
    if f.get("allowWishOrder"):
        names.append("wish_order")
    if f.get("allowVolunteerRole"):
        names.append("volunteer_role")
    if f.get("requireTourNoticeAck"):
        names.append("tour_notice_ack")
    if f.get("allowSeatZone"):
        names.append("seat_zone")
    if f.get("allowPostGallery"):
        names.append("post_gallery_json")
    if f.get("requireCreditWritebackAck"):
        names.append("credit_writeback_ack")
    if f.get("allowProjectNo"):
        names.append("project_no")
    if f.get("allowProcureRef"):
        names.append("procure_ref_no")
    if f.get("allowDualReview"):
        names.extend(["dual_reviewer_a", "dual_reviewer_b"])
    if f.get("allowShipFee"):
        names.append("ship_fee_yuan")
    if f.get("allowUtilityNote"):
        names.append("utility_note")
    if f.get("requirePeerConfirm"):
        names.extend(["peer_username", "peer_ack"])
    if int(f.get("dueSoonDays") or 0) > 0:
        names.append("due_soon_notified_at")
    if int(f.get("maxOverdueTimes") or 0) > 0:
        names.append("ever_overdue")
    if int(f.get("followRemindDays") or 0) > 0:
        names.append("follow_soon_notified_at")
    if f.get("allowDealAmount"):
        names.append("deal_amount_yuan")
    if f.get("allowNextAction"):
        names.extend(["next_action", "next_action_done"])
    if f.get("requireCloseAttach"):
        names.append("close_attach_url")
    if f.get("requireReturnDate"):
        names.append("return_date")
    if f.get("allowLeaveProxy"):
        names.append("proxy_name")
    if f.get("allowInterviewResult"):
        names.append("interview_result")
    if f.get("allowWrittenScore"):
        names.append("written_score")
    if f.get("allowBgCheckNote"):
        names.append("bg_check_note")
    if f.get("allowDefenseResult"):
        names.append("defense_result")
    if f.get("maskBankAccount"):
        names.append("bank_account")
    if f.get("allowDisburseBatch"):
        names.append("disburse_batch")
    if f.get("allowConfidential"):
        names.append("confidential")
    if f.get("allowAssignDept"):
        names.append("assign_dept")
    if f.get("requireAppraisal"):
        names.extend(["appraisal_comment", "appraisal_grade"])
    if f.get("allowCompanyEval"):
        names.append("company_eval")
    if f.get("allowExcellentMark"):
        names.append("excellent_mark")
    if int(f.get("maxReviseTimes") or 0) > 0:
        names.append("revise_count")
    if f.get("allowApproveCc") or f.get("approveThicken"):
        names.append("cc_usernames")
    if f.get("allowApproveRemarkAttach"):
        names.append("approve_attach_url")
    if f.get("allowCertPickup"):
        names.extend(["pickup_method", "mail_address", "express_no"])
    if f.get("allowCertUrgent"):
        names.append("cert_urgent")
    if f.get("allowSealCopies"):
        names.extend(["seal_copies", "bind_note", "seal_copy_nos", "seal_witness_ack"])
    if f.get("allowFleetMileage"):
        names.extend(["mileage_km", "fuel_note"])
    if f.get("allowExpenseInvoice"):
        names.append("invoice_count")
    if f.get("allowVisitorCount"):
        names.append("visitor_count")
    if f.get("allowAwardCertNo"):
        names.append("award_cert_no")
    if f.get("allowVendorQuotes") or int(f.get("minVendorQuotes") or 0) > 0:
        names.append("vendor_quotes")
    if f.get("allowCompHours"):
        names.append("comp_hours")
    if f.get("allowFleetCrew"):
        names.extend(["driver_name", "passenger_names"])
    if f.get("allowReturnFuel"):
        names.append("return_fuel")
    if f.get("allowLaborPlace"):
        names.append("labor_place")
    if f.get("allowEffectiveOn"):
        names.append("effective_on")
    if f.get("allowCertIssueNo"):
        names.append("cert_issue_no")
    if f.get("allowDocRev"):
        names.append("doc_rev")
    if f.get("allowFitoutQuiet"):
        names.extend(["work_start", "work_end"])
    if f.get("allowIssueCopies"):
        names.append("issue_copies")
    if f.get("allowSignParties"):
        names.append("sign_parties")
    if f.get("allowTrainHours"):
        names.append("train_hours")
    if f.get("allowMemberChange"):
        names.append("member_change_note")
    if f.get("allowProcureBudget"):
        names.append("procure_amount")
    if f.get("allowCheckinException"):
        names.append("exception_type")
    if f.get("allowVisitPurpose"):
        names.append("visit_purpose")
    if f.get("allowFleetViolation"):
        names.append("violation_person")
    if f.get("allowFitoutRectify"):
        names.append("rectify_note")
    if f.get("allowProcureReturn"):
        names.extend(["return_fail", "return_note"])
    if f.get("allowMoralObjection"):
        names.extend(["objection_due_at", "objection_note", "objection_at"])
    if f.get("allowProjFundUse"):
        names.extend(["fund_use_yuan", "fund_use_note"])
    if f.get("allowVisitSlotRemain"):
        names.append("visit_on")
    if f.get("allowPlagiarismUrl"):
        names.append("plagiarism_url")
    if f.get("allowPartyStage"):
        names.extend(["party_stage", "stage_on"])
    if f.get("allowEvalObserve"):
        names.extend(["observe_on", "observe_note"])
    if f.get("allowScheduleImpact"):
        names.append("schedule_impact_note")
    if f.get("allowContractAmount"):
        names.append("contract_amount")
    if f.get("allowProjChangeLog"):
        names.append("change_log_note")
    if f.get("allowCertVerify"):
        names.append("verify_code")
    if f.get("allowVisitWalkIn"):
        names.extend(["walk_in", "visit_on"])
    if f.get("allowCheckinProxy"):
        names.append("checkin_proxy_by")
    if f.get("allowCarpassParkingMutex"):
        names.append("parking_on")
    if f.get("allowContractRenew"):
        names.extend(["renew_on", "renew_note"])
    if f.get("allowCertPickupRedeem"):
        names.extend(["pickup_redeem_code", "pickup_redeemed"])
    if f.get("allowObjectionWindow") or int(f.get("objectionDays") or 0) > 0:
        names.extend(["objection_due_at", "objection_note", "objection_at"])
    if f.get("requireFeedbackSet"):
        names.extend(["feedback_interest", "feedback_concern", "feedback_next"])
    if f.get("allowRecordUrl"):
        names.append("record_url")
    if f.get("repairThicken") or f.get("allowUserUrge"):
        names.extend(
            [
                "urge_at",
                "urge_count",
                "urge_cancelled",
                "fault_reason",
                "close_summary",
                "preferred_slot",
                "response_due_at",
                "night_urgent",
                "address_type",
                "helper_username",
                "hold_reason",
                "subscribe_progress",
                "audio_url",
                "rating_tags",
                "follow_rated",
                "route_note",
                "skill_tag",
                "visit_due_at",
            ]
        )
    if f.get("allowPartsNote"):
        names.append("parts_note")
    if f.get("allowSerialNo"):
        names.append("serial_no")
    if f.get("allowQuote"):
        names.extend(["quote_yuan", "quote_confirmed", "material_fee_yuan", "material_paid"])
    if f.get("allowAssetCode"):
        names.append("asset_code")
    if f.get("allowRemoteUrl"):
        names.append("remote_url")
    if f.get("allowTicketMerge") or f.get("allowNestedReply"):
        names.append("parent_ticket_id")
    if f.get("allowKnowledgeDeposit"):
        names.append("knowledge_deposit")
    # 去重保序
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def resolve_ticket_flags(
    domain: str,
    *,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
    ticket_flags: dict | None = None,
) -> dict:
    """优先用 bake 传入的 ticket 实体；否则回落域默认 schema。"""
    if isinstance(ticket_flags, dict) and ticket_flags:
        return ticket_flags
    d = (domain or "").strip()
    try:
        from app.bake.schema.templates import SCHEMA_BUILDERS

        builder = SCHEMA_BUILDERS.get(d)
        if builder:
            schema = builder("thesis")
            ent = ((schema.get("entities") or {}).get("ticket") or {})
            if isinstance(ent, dict):
                return ent
    except Exception:
        pass
    if d == "DOM-GENERIC":
        try:
            from app.bake.archetype_shells import build_generic_shell_schema

            schema = build_generic_shell_schema(
                "thesis",
                archetype=archetype,
                archetypes=archetypes,
            )
            ent = ((schema.get("entities") or {}).get("ticket") or {})
            if isinstance(ent, dict):
                return ent
        except Exception:
            pass
    return {}


def ticket_optional_columns_for(
    domain: str,
    *,
    ticket_flags: dict | None = None,
) -> list[tuple[str, str]]:
    names: list[str] = []
    names.extend(TICKET_DOMAIN_COLUMNS.get(domain or "", []))
    names.extend(_ticket_flag_column_names(ticket_flags))
    seen: set[str] = set()
    cols: list[tuple[str, str]] = []
    for n in names:
        key = n.lower()
        if key in seen:
            continue
        for cat_name, cat_ddl in TICKET_OPTIONAL_COLUMNS:
            if cat_name.lower() == key:
                seen.add(key)
                cols.append((cat_name, cat_ddl))
                break
    return cols


def ensure_ticket_extra_sql(
    sql: str,
    *,
    domain: str,
    ticket_table: str | None,
    ticket_flags: dict | None = None,
) -> str:
    """对单据主表按域/能力补齐扩展列，并剔除跨域 L1 超集。"""
    t = (ticket_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql
    want = ticket_optional_columns_for(domain, ticket_flags=ticket_flags)
    allow = {n.lower() for n, _ in want}

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != t.lower():
            return m.group(0)
        body = _prune_columns(body, allow=allow, known=_TICKET_OPTIONAL_NAMES)
        if want:
            body = _inject_missing_columns(body, want)
        body = _strip_trailing_comma(body)
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, sql)


_CREDIT_LEDGER_DDL = """
CREATE TABLE IF NOT EXISTS credit_ledger (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  delta INT NOT NULL,
  score_after INT NOT NULL DEFAULT 0,
  reason VARCHAR(128) DEFAULT '',
  ref_type VARCHAR(32) DEFAULT '',
  ref_id BIGINT NULL,
  operator VARCHAR(64) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_credit_user (username, id)
);
"""

def ensure_borrow_credit_sql(
    sql: str,
    *,
    enabled: bool,
    initial: int = 100,
) -> str:
    """信誉分物理列：sys_user.credit_score + credit_ledger 流水。"""
    init = max(1, min(999, int(initial or 100)))
    cols = [("credit_score", f"INT NOT NULL DEFAULT {init}")]
    out = sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != "sys_user":
            return m.group(0)
        if not enabled:
            body = _prune_columns(body, allow=set(), known={"credit_score"})
        else:
            body = _inject_missing_columns(body, cols)
        body = _strip_trailing_comma(body)
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(repl, out)
    if not enabled:
        out = re.sub(
            r"CREATE TABLE IF NOT EXISTS\s+`?credit_ledger`?\s*\((?:.|\n)*?\);\s*",
            "",
            out,
            flags=re.IGNORECASE,
        )
    elif "credit_ledger" not in out.lower():
        out = out.rstrip() + "\n" + _CREDIT_LEDGER_DDL
    return out


def ensure_ticket_progress_sql(sql: str, ticket_table: str | None) -> str:
    """单据进度统一为 {ticket}_progress；去掉同域闲置的 {ticket}_log，避免双表语义。"""
    t = (ticket_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql
    progress = f"{t}_progress"
    log_name = f"{t}_log"
    out = re.sub(
        rf"CREATE TABLE IF NOT EXISTS\s+`?{re.escape(log_name)}`?\s*\((?:.|\n)*?\);\s*",
        "",
        sql,
        count=1,
        flags=re.IGNORECASE,
    )
    if re.search(rf"CREATE TABLE IF NOT EXISTS\s+`?{re.escape(progress)}`?\b", out, re.I):
        return out
    return out.rstrip() + "\n" + _TICKET_PROGRESS_DDL.format(table=progress)
