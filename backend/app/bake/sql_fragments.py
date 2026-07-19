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
            body = _inject_missing_columns(body, ORDER_SHIP_COLUMNS)
        elif t == "sys_user":
            body = _inject_missing_columns(body, SYS_USER_STAFF_COLUMNS)
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, sql)
