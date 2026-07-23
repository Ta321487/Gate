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

# 忠诚度：余额 / 积分 / 会员（运行时按能力使用）
SYS_USER_LOYALTY_COLUMNS: list[tuple[str, str]] = [
    ("balance_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
    ("points", "INT NOT NULL DEFAULT 0"),
    ("member_tier", "VARCHAR(32) DEFAULT ''"),
    ("spend_total_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
]

ORDER_LOYALTY_COLUMNS: list[tuple[str, str]] = [
    ("discount_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
    ("pay_balance_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
    ("points_earned", "INT NOT NULL DEFAULT 0"),
    ("coupon_code", "VARCHAR(32) DEFAULT ''"),
]

ORDER_REFUND_COLUMNS: list[tuple[str, str]] = [
    ("refund_status", "VARCHAR(16) DEFAULT ''"),
    ("refund_reason", "VARCHAR(255) DEFAULT ''"),
    ("refund_at", "DATETIME NULL"),
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
    if d == "DOM-GENERIC":
        cols = list(ORDER_ADDRESS_COLUMNS) + list(ORDER_SHOP_FULFILL_COLUMNS)
        if "ARCH-RESERVE" in arches:
            cols = cols + list(ORDER_RESERVATION_LINK_COLUMNS)
        return cols
    # 其他带订单的域：按商城履约，不含餐饮口味/预约外键
    return list(ORDER_ADDRESS_COLUMNS) + list(ORDER_SHOP_FULFILL_COLUMNS)


def ensure_shared_sql_columns(
    sql: str,
    *,
    domain: str = "",
    archetypes: list[str] | None = None,
    staff: bool = True,
    loyalty: bool = False,
) -> str:
    """对 reservation / 订单表 / sys_user 补齐共享列。

    预约/订单履约列均按 domain（及 GENERIC 的 archetype）注入并剔除跨域字段。
    """
    resv_cols = list(RESERVATION_COLUMNS_BY_DOMAIN.get(domain or "", []))
    resv_allow = {n.lower() for n, _ in resv_cols}
    order_fulfill = order_fulfill_columns_for(domain, archetypes)
    order_allow = {n.lower() for n, _ in order_fulfill} | {
        n.lower() for n, _ in ORDER_REFUND_COLUMNS
    }
    if loyalty:
        order_allow |= _ORDER_LOYALTY_NAMES

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        t = table.lower()
        if t == "reservation":
            body = _prune_columns(
                body, allow=resv_allow, known=_RESERVATION_EXTRA_NAMES
            )
            if resv_cols:
                body = _inject_missing_columns(body, resv_cols)
        elif t in ("biz_order", "shop_order", "food_order", "hotel_order", "orders"):
            body = _prune_columns(
                body,
                allow=order_allow,
                known=_ORDER_FULFILL_NAMES | _ORDER_LOYALTY_NAMES,
            )
            cols = list(order_fulfill) + list(ORDER_REFUND_COLUMNS)
            if loyalty:
                cols = list(order_fulfill) + list(ORDER_LOYALTY_COLUMNS) + list(
                    ORDER_REFUND_COLUMNS
                )
            body = _inject_missing_columns(body, cols)
        elif t == "sys_user":
            if not loyalty:
                body = _prune_columns(
                    body, allow=set(), known=_SYS_USER_LOYALTY_NAMES
                )
            cols: list[tuple[str, str]] = []
            if staff:
                cols.extend(SYS_USER_STAFF_COLUMNS)
            if loyalty:
                cols.extend(SYS_USER_LOYALTY_COLUMNS)
            if cols:
                body = _inject_missing_columns(body, cols)
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(repl, sql)
    if not loyalty:
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


_GUESTBOOK_DDL = """
CREATE TABLE IF NOT EXISTS sys_guestbook (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  nickname VARCHAR(64) DEFAULT '',
  body VARCHAR(500) NOT NULL,
  reply VARCHAR(500) DEFAULT '',
  reply_username VARCHAR(64) DEFAULT '',
  replied_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_gb_created (id),
  KEY idx_gb_user (username)
);
"""

_FAVORITE_DDL = """
CREATE TABLE IF NOT EXISTS user_favorite (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  item_id BIGINT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_fav_user_item (username, item_id),
  KEY idx_fav_user (username, id)
);
"""


def ensure_guestbook_sql(sql: str, *, enabled: bool) -> str:
    """能力开启时幂等补留言表；未开启不注入（控表预算）。"""
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?sys_guestbook`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _GUESTBOOK_DDL


def ensure_favorites_sql(sql: str, *, enabled: bool) -> str:
    """交易收藏表；未开启不注入。"""
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?user_favorite`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _FAVORITE_DDL


_BROWSE_HISTORY_DDL = """
CREATE TABLE IF NOT EXISTS user_browse_history (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  item_id BIGINT NOT NULL,
  viewed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_browse_user_item (username, item_id),
  KEY idx_browse_user_time (username, viewed_at)
);
"""


def ensure_browse_history_sql(sql: str, *, enabled: bool) -> str:
    """浏览足迹表；仅开题挂 browse_history 时注入。"""
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?user_browse_history`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _BROWSE_HISTORY_DDL


GALLERY_COLUMNS: list[tuple[str, str]] = [
    ("gallery_json", "TEXT NULL"),
]


def ensure_gallery_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    """档案主表补 gallery_json；仅 gallery 能力开启时注入。"""
    if not enabled:
        return sql
    t = (item_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != t.lower():
            return m.group(0)
        body = _inject_missing_columns(body, GALLERY_COLUMNS)
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, sql)


CHECKIN_CODE_COLUMNS: list[tuple[str, str]] = [
    ("checkin_code", "VARCHAR(16) NOT NULL DEFAULT ''"),
]

MUTEX_CODE_COLUMNS: list[tuple[str, str]] = [
    ("mutex_code", "VARCHAR(32) NOT NULL DEFAULT ''"),
]


def ensure_archive_flag_columns(
    sql: str,
    *,
    item_table: str | None,
    allow_checkin: bool = False,
    check_mutex: bool = False,
) -> str:
    """档案表按单据能力补签到码 / 互斥码（禁止运行时再 ALTER）。"""
    t = (item_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql
    cols: list[tuple[str, str]] = []
    if allow_checkin:
        cols.extend(CHECKIN_CODE_COLUMNS)
    if check_mutex:
        cols.extend(MUTEX_CODE_COLUMNS)
    if not cols:
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != t.lower():
            return m.group(0)
        body = _inject_missing_columns(body, cols)
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, sql)


_PROMO_COUPON_DDL = """
CREATE TABLE IF NOT EXISTS promo_coupon (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  code VARCHAR(32) NOT NULL,
  label VARCHAR(64) DEFAULT '',
  min_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  off_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  total_quota INT NOT NULL DEFAULT 0,
  claimed INT NOT NULL DEFAULT 0,
  expire_at DATETIME NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'active',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_promo_code (code)
);
"""

_USER_COUPON_DDL = """
CREATE TABLE IF NOT EXISTS user_coupon (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  coupon_id BIGINT NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'unused',
  claimed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  used_at DATETIME NULL,
  order_id BIGINT NULL,
  UNIQUE KEY uk_user_coupon (username, coupon_id),
  KEY idx_user_coupon_user (username, status, id)
);
"""

_ORDER_REVIEW_DDL = """
CREATE TABLE IF NOT EXISTS order_review (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  order_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  rating INT NOT NULL,
  body VARCHAR(500) DEFAULT '',
  reply VARCHAR(500) DEFAULT '',
  replied_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_order_review (order_id),
  KEY idx_review_user (username, id)
);
"""


def ensure_coupon_lifecycle_sql(sql: str, *, enabled: bool) -> str:
    if not enabled:
        return sql
    out = sql
    if not re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?promo_coupon`?\b", out):
        out = out.rstrip() + "\n" + _PROMO_COUPON_DDL
    if not re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?user_coupon`?\b", out):
        out = out.rstrip() + "\n" + _USER_COUPON_DDL
    return out


def ensure_order_review_sql(sql: str, *, enabled: bool) -> str:
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?order_review`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _ORDER_REVIEW_DDL


# 单据可选扩展列全集（剔除名单）；注入按域 + schema.ticket 能力
TICKET_OPTIONAL_COLUMNS: list[tuple[str, str]] = [
    ("attach_url", "VARCHAR(255) NOT NULL DEFAULT ''"),
    ("rating", "INT NULL"),
    ("rating_remark", "VARCHAR(255) NOT NULL DEFAULT ''"),
    ("rated_at", "DATETIME NULL"),
    ("priority", "VARCHAR(16) DEFAULT '普通'"),
    ("contact_phone", "VARCHAR(20) DEFAULT ''"),
    ("fine_status", "VARCHAR(16) DEFAULT 'none'"),
    ("pickup_at", "DATETIME NULL"),
    ("pickup_place", "VARCHAR(128) DEFAULT ''"),
    ("actual_qty", "INT NULL"),
    ("contact_channel", "VARCHAR(32) DEFAULT ''"),
    ("next_follow_at", "DATETIME NULL"),
    ("checked_in_at", "DATETIME NULL"),
    ("qty", "INT NOT NULL DEFAULT 1"),
    ("period_start", "DATETIME NULL"),
    ("period_end", "DATETIME NULL"),
]

_TICKET_OPTIONAL_NAMES = {n.lower() for n, _ in TICKET_OPTIONAL_COLUMNS}
_TICKET_COL_DDL = {n.lower(): ddl for n, ddl in TICKET_OPTIONAL_COLUMNS}

# 域固有业务列（不含 attach/rating 等能力开关列）
TICKET_DOMAIN_COLUMNS: dict[str, list[str]] = {
    "DOM-LIBRARY": ["fine_status"],
    "DOM-EQUIP": ["fine_status"],
    "DOM-ASSET": ["pickup_at", "pickup_place", "actual_qty"],
    "DOM-CRM": ["contact_channel", "next_follow_at"],
    "DOM-EVENT": ["contact_channel", "next_follow_at"],
    "DOM-DORM": ["priority", "contact_phone"],
    "DOM-PROPERTY": ["priority", "contact_phone"],
    "DOM-IT": ["priority", "contact_phone"],
    "DOM-LOST": ["fine_status", "pickup_at", "pickup_place"],
    "DOM-ACTIVITY": [],
    "DOM-COURSE": [],
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
    if f.get("allowQty"):
        names.append("qty")
    if f.get("pickDateRange"):
        names.extend(["period_start", "period_end"])
    if f.get("allowCheckin"):
        names.append("checked_in_at")
    if f.get("noShowAfterEnd") or f.get("fineLabel"):
        names.append("fine_status")
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
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, sql)


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
