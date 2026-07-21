"""跨域 SQL 共享片段：bake 时幂等补列，避免各 DOM-*.sql 手改漏列。

运行时 SlotStore.ensureResvCol / OrderStore ensure 仍会兜底；
此处保证交付的 schema.sql 一开始就完整。
"""

from __future__ import annotations

import re

# 预约表扩展列（停车/挂号/场地/酒店/美发共用超集）
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

# 订单物流/取餐
ORDER_SHIP_COLUMNS: list[tuple[str, str]] = [
    ("tracking_no", "VARCHAR(64) DEFAULT ''"),
    ("pickup_code", "VARCHAR(32) DEFAULT ''"),
    ("shipped_at", "DATETIME NULL"),
    ("reservation_id", "BIGINT NULL"),
]

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

_CREATE_TABLE_RE = re.compile(
    r"(CREATE TABLE IF NOT EXISTS\s+(\w+)\s*\()((?:.|\n)*?)(\);)",
    re.IGNORECASE,
)


def _inject_missing_columns(body: str, columns: list[tuple[str, str]]) -> str:
    lower = body.lower()
    missing = [(name, ddl) for name, ddl in columns if name.lower() not in lower]
    if not missing:
        return body
    lines = [f"  {name} {ddl}," for name, ddl in missing]
    # 插在 created_at 前；没有则插在末尾逗号后
    m = re.search(r"(?m)^(\s*created_at\b)", body)
    if m:
        return body[: m.start()] + "\n".join(lines) + "\n" + body[m.start() :]
    trimmed = body.rstrip()
    if not trimmed.endswith(","):
        trimmed += ","
    return trimmed + "\n" + "\n".join(lines) + "\n"


def ensure_shared_sql_columns(sql: str) -> str:
    """对 reservation / biz_order / sys_user / 常见订单表补齐共享列。"""

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        t = table.lower()
        if t == "reservation":
            body = _inject_missing_columns(body, RESERVATION_EXTRA_COLUMNS)
        elif t in ("biz_order", "shop_order", "food_order", "hotel_order", "orders"):
            body = _inject_missing_columns(
                body, ORDER_SHIP_COLUMNS + ORDER_LOYALTY_COLUMNS + ORDER_REFUND_COLUMNS
            )
        elif t == "sys_user":
            body = _inject_missing_columns(
                body, SYS_USER_STAFF_COLUMNS + SYS_USER_LOYALTY_COLUMNS
            )
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(repl, sql)
    if "user_ledger" not in out.lower():
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
