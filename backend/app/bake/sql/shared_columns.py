"""Moved from fragments.py — SQL ensure helpers."""

from __future__ import annotations

import re

from app.bake.sql.ddl_edit import (
    CREATE_TABLE_RE as _CREATE_TABLE_RE,
    inject_missing_columns as _inject_missing_columns,
    prune_columns as _prune_columns,
)


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

RESERVATION_COLUMNS_BY_DOMAIN: dict[str, list[tuple[str, str]]] = {
    "DOM-PARKING": [
        ("plate_no", "VARCHAR(16) DEFAULT ''"),
        ("entry_at", "DATETIME NULL"),
        ("exit_at", "DATETIME NULL"),
        ("overtime_fee_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("duration_fee_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("parking_pass_used", "TINYINT NOT NULL DEFAULT 0"),
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
        ("recording_url", "VARCHAR(255) NOT NULL DEFAULT ''"),
        ("video_url", "VARCHAR(255) NOT NULL DEFAULT ''"),
        ("door_code", "VARCHAR(32) NOT NULL DEFAULT ''"),
        ("service_tea", "TINYINT NOT NULL DEFAULT 0"),
        ("service_device", "TINYINT NOT NULL DEFAULT 0"),
        ("equip_borrow", "TINYINT NOT NULL DEFAULT 0"),
        ("minutes_attach", "VARCHAR(512) NOT NULL DEFAULT ''"),
        ("meeting_stage", "VARCHAR(16) NOT NULL DEFAULT ''"),
        ("checkin_token", "VARCHAR(32) NOT NULL DEFAULT ''"),
    ],
    "DOM-HOTEL": [
        ("guest_name", "VARCHAR(32) DEFAULT ''"),
        ("guest_count", "INT DEFAULT 0"),
        ("stay_from", "DATE NULL"),
        ("stay_to", "DATE NULL"),
        ("id_no", "VARCHAR(32) NOT NULL DEFAULT ''"),
        ("deposit_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("balance_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("breakfast_vouchers", "INT NOT NULL DEFAULT 0"),
        ("notice_ack", "TINYINT NOT NULL DEFAULT 0"),
        ("extra_bed", "TINYINT NOT NULL DEFAULT 0"),
        ("late_checkout_fee_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("checkout_checklist", "VARCHAR(512) NOT NULL DEFAULT ''"),
    ],
    "DOM-CARRENT": [
        ("guest_name", "VARCHAR(32) DEFAULT ''"),
        ("guest_count", "INT DEFAULT 0"),
        ("violation_hold_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("violation_hold_note", "VARCHAR(255) NOT NULL DEFAULT ''"),
        ("inspect_ack", "TINYINT NOT NULL DEFAULT 0"),
        ("mileage_over_fee_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("insurance_pkg", "VARCHAR(32) NOT NULL DEFAULT ''"),
        ("license_expire_on", "DATE NULL"),
        ("violation_attach", "VARCHAR(512) NOT NULL DEFAULT ''"),
        ("etc_fee_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
    ],
    "DOM-SALON": [
        ("preferred_stylist", "VARCHAR(32) DEFAULT ''"),
        ("queue_no", "INT DEFAULT 0"),
    ],
    "DOM-INSTRUMENT": [
        ("overtime_fee_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("training_ack", "TINYINT NOT NULL DEFAULT 0"),
        ("consumable_note", "VARCHAR(512) NOT NULL DEFAULT ''"),
    ],
}

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

ORDER_SHIP_COLUMNS: list[tuple[str, str]] = [
    *ORDER_ADDRESS_COLUMNS,
    ("taste_note", "VARCHAR(255) DEFAULT ''"),
    ("tracking_no", "VARCHAR(64) DEFAULT ''"),
    ("pickup_code", "VARCHAR(32) DEFAULT ''"),
    ("shipped_at", "DATETIME NULL"),
    ("reservation_id", "BIGINT NULL"),
]

_ORDER_FULFILL_NAMES = {n.lower() for n, _ in ORDER_SHIP_COLUMNS}

SYS_USER_STAFF_COLUMNS: list[tuple[str, str]] = [
    ("staff_post", "VARCHAR(64) DEFAULT ''"),
    ("staff_kind", "VARCHAR(16) DEFAULT ''"),
]

# 与 fragments.py 对齐：按 cap 拆列（wallet 默认 ≠ 整包灌积分/会员/券）
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

ORDER_LIFECYCLE_COLUMNS: list[tuple[str, str]] = [
    ("completed_at", "DATETIME NULL"),
]
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
