"""配送时段与节日加价。开题写到才挂，挂在已有订单上。

不是预约域的 resource_slot，也不是商品活动价 flash_price。
管理端维护时段和节日区间；用户在结算页从这份列表里选。
"""

from __future__ import annotations

import re
from app.bake.sql.ddl_edit import (
    CREATE_TABLE_RE as _CREATE_TABLE_RE,
    inject_missing_columns as _inject_missing_columns,
    prune_columns as _prune_columns,
)

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

DELIVERY_WINDOW_CAP = "delivery_window"

_TERMS = (
    "配送日期",
    "配送时段",
    "送达时段",
    "当日达",
    "节日涨价",
    "节日加价",
)


def _hit(text: str, terms: tuple[str, ...]) -> bool:
    return any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in terms)


def scan_delivery_window(text: str, title: str = "") -> bool:
    blob = f"{title or ''}\n{text or ''}"
    if _hit(blob, _TERMS):
        return True
    from app.bake.scene_scan import shop_product_kind

    if shop_product_kind(title, text) == "flowers" and _hit(blob, ("预订", "配送")):
        return True
    return False


def merge_delivery_window_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
    title: str = "",
) -> list[str]:
    out = list(caps or [])
    if "order_lines" not in out:
        return [c for c in out if c != DELIVERY_WINDOW_CAP]
    if DELIVERY_WINDOW_CAP in out:
        return out
    if scan_delivery_window(proposal_text or "", title):
        out.append(DELIVERY_WINDOW_CAP)
    return out


def apply_delivery_window_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    from app.bake.schema.menu_utils import ensure_menu

    title = str(spec.get("title") or "")
    caps = merge_delivery_window_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text or "",
        domain=spec.get("domain"),
        title=title,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if DELIVERY_WINDOW_CAP not in caps:
        return {**spec, "schema": schema}

    schema["deliveryWindow"] = True
    labels = dict(schema.get("labels") or {})
    labels.setdefault("deliverySlotMenu", "配送时段")
    labels.setdefault("priceSpanMenu", "节日加价")
    labels.setdefault(
        "deliveryWindowHint",
        "请选择配送日期和仍有余量的时段。当日达、预订由该时段决定，节日加价按下单当日规则计入本单。",
    )
    schema["labels"] = labels
    menus = dict(schema.get("menus") or {})
    admin = list(menus.get("admin") or [])
    ensure_menu(
        admin,
        "delivery_slots",
        {"key": "delivery_slots", "label": "配送时段", "superOnly": False},
        before_key="orders",
    )
    ensure_menu(
        admin,
        "price_spans",
        {"key": "price_spans", "label": "节日加价", "superOnly": False},
        before_key="orders",
    )
    menus["admin"] = admin
    schema["menus"] = menus
    return {**spec, "schema": schema}


# --- SQL ensure (moved from fragments.py) ---

ORDER_WINDOW_COLUMNS: list[tuple[str, str]] = [
    ("fulfill_mode", "VARCHAR(16) DEFAULT ''"),
    ("delivery_on", "DATE NULL"),
    ("slot_id", "BIGINT NULL"),
    ("slot_label", "VARCHAR(64) DEFAULT ''"),
    ("price_rate", "DECIMAL(6,2) NOT NULL DEFAULT 1.00"),
]

_DELIVERY_WINDOW_DDL = """
CREATE TABLE IF NOT EXISTS delivery_slot (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  label VARCHAR(64) NOT NULL,
  start_hm VARCHAR(8) NOT NULL DEFAULT '',
  end_hm VARCHAR(8) NOT NULL DEFAULT '',
  capacity INT NOT NULL DEFAULT 1,
  fulfill_mode VARCHAR(16) NOT NULL DEFAULT 'preorder',
  cutoff_hm VARCHAR(8) NOT NULL DEFAULT '',
  enabled TINYINT NOT NULL DEFAULT 1,
  sort_no INT NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS price_span (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL,
  date_from DATE NOT NULL,
  date_to DATE NOT NULL,
  rate DECIMAL(6,2) NOT NULL DEFAULT 1.00,
  enabled TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

_DELIVERY_WINDOW_SEED = """
INSERT INTO delivery_slot (id, label, start_hm, end_hm, capacity, fulfill_mode, cutoff_hm, enabled, sort_no)
SELECT 1, '上午档', '09:00', '12:00', 8, 'same_day', '11:00', 1, 10 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM delivery_slot WHERE id=1);
INSERT INTO delivery_slot (id, label, start_hm, end_hm, capacity, fulfill_mode, cutoff_hm, enabled, sort_no)
SELECT 2, '下午档', '14:00', '18:00', 8, 'preorder', '', 1, 20 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM delivery_slot WHERE id=2);
INSERT INTO price_span (id, name, date_from, date_to, rate, enabled)
SELECT 1, '情人节', '2026-02-10', '2026-02-14', 1.50, 1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM price_span WHERE id=1);
UPDATE biz_order
SET fulfill_mode='preorder', delivery_on='2026-09-26', slot_id=2, slot_label='下午档', price_rate=1.00
WHERE id=1 AND (slot_id IS NULL OR slot_id=0);
"""

def ensure_delivery_window_sql(sql: str, *, enabled: bool) -> str:
    """配送时段表、节日加价表、订单头快照列。未开不加。"""
    if not enabled:
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != "biz_order":
            return m.group(0)
        body = _inject_missing_columns(body, ORDER_WINDOW_COLUMNS)
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(repl, sql)
    if not re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?delivery_slot`?\b", out):
        out = out.rstrip() + "\n" + _DELIVERY_WINDOW_DDL + "\n" + _DELIVERY_WINDOW_SEED
    return out
