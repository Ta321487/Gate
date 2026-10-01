"""按重量卖，并带次日达和损耗赔付。开题写到才挂，挂在已有下单上。

生鲜皮只换分类，不因货皮加重量列。次日达复用配送时段，不另做一套履约。
"""

from __future__ import annotations

import re
from app.bake.sql.ddl_edit import (
    CREATE_TABLE_RE as _CREATE_TABLE_RE,
    inject_missing_columns as _inject_missing_columns,
    prune_columns as _prune_columns,
)

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

WEIGH_SALE_CAP = "weigh_sale"

_TERMS = (
    "按重量",
    "元/斤",
    "损耗",
    "赔付",
    "次日达",
)

_NEIGHBORS = frozenset({"DOM-HOTEL", "DOM-MEETING", "DOM-LIBRARY"})


def line_yuan(unit_price: Decimal | str | float, weight_qty: Decimal | str | float) -> Decimal:
    """行金额 = 单价 × 重量，保留两位。件数不参与。"""
    unit = Decimal(str(unit_price))
    weight = Decimal(str(weight_qty))
    return (unit * weight).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _hit(text: str, terms: tuple[str, ...]) -> bool:
    return any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in terms)


def scan_weigh_sale(text: str, title: str = "") -> bool:
    return _hit(f"{title or ''}\n{text or ''}", _TERMS)


def merge_weigh_sale_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
    title: str = "",
) -> list[str]:
    out = list(caps or [])
    if (domain or "") in _NEIGHBORS or "order_lines" not in out:
        return [c for c in out if c != WEIGH_SALE_CAP]
    if WEIGH_SALE_CAP not in out and scan_weigh_sale(proposal_text or "", title):
        out.append(WEIGH_SALE_CAP)
    if WEIGH_SALE_CAP in out:
        from app.bake.features.delivery_window import DELIVERY_WINDOW_CAP

        if DELIVERY_WINDOW_CAP not in out:
            out.append(DELIVERY_WINDOW_CAP)
    return out


def apply_weigh_sale_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    from app.bake.features.delivery_window import apply_delivery_window_to_spec
    from app.bake.schema.menu_utils import ensure_menu

    title = str(spec.get("title") or "")
    caps = merge_weigh_sale_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text or "",
        domain=spec.get("domain"),
        title=title,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    spec = {**spec, "schema": schema}
    if WEIGH_SALE_CAP not in caps:
        return spec

    spec = apply_delivery_window_to_spec(spec, proposal_text or "")
    schema = dict(spec.get("schema") or {})
    schema["weighSale"] = True
    labels = dict(schema.get("labels") or {})
    labels.setdefault("lossMenu", "损耗赔付")
    labels.setdefault("myLossMenu", "损耗赔付")
    labels.setdefault(
        "weighSaleHint",
        "按重量卖的商品按重量计价。次日达只能选明天。损耗赔付按单笔上限退回余额。",
    )
    schema["labels"] = labels

    ents = dict(schema.get("entities") or {})
    arch = dict(ents.get("archive") or {})
    fields = [f for f in (arch.get("fields") or []) if isinstance(f, dict)]
    keys = {str(f.get("key") or "") for f in fields}
    if "sellByWeight" not in keys:
        fields.append({"key": "sellByWeight", "label": "按重量卖", "type": "switch"})
    if "weightUnit" not in keys:
        fields.append({
            "key": "weightUnit",
            "label": "计价单位",
            "type": "select",
            "options": ["斤", "公斤"],
        })
    arch["fields"] = fields
    ents["archive"] = arch
    schema["entities"] = ents

    menus = dict(schema.get("menus") or {})
    admin = list(menus.get("admin") or [])
    ensure_menu(
        admin,
        "loss_claims",
        {"key": "loss_claims", "label": "损耗赔付", "superOnly": False},
        before_key="orders",
    )
    menus["admin"] = admin
    user = list(menus.get("user") or [])
    ensure_menu(
        user,
        "my_loss",
        {"key": "my_loss", "label": "损耗赔付"},
        before_key="my_orders",
    )
    menus["user"] = user
    schema["menus"] = menus
    return {**spec, "schema": schema}


# --- SQL ensure (moved from fragments.py) ---

PRODUCT_WEIGH_COLUMNS: list[tuple[str, str]] = [
    ("sell_by_weight", "TINYINT NOT NULL DEFAULT 0"),
    ("weight_unit", "VARCHAR(8) NOT NULL DEFAULT ''"),
]

ORDER_LINE_WEIGHT_COLUMNS: list[tuple[str, str]] = [
    ("weight_qty", "DECIMAL(10,3) NULL"),
]

_WEIGH_SALE_DDL = """
CREATE TABLE IF NOT EXISTS loss_policy (
  id BIGINT PRIMARY KEY,
  enabled TINYINT NOT NULL DEFAULT 0,
  cap_yuan DECIMAL(10,2) NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS loss_claim (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  order_id BIGINT NOT NULL,
  amount_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  reason VARCHAR(255) NOT NULL DEFAULT '',
  status VARCHAR(16) NOT NULL DEFAULT 'pending',
  paid_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

def ensure_weigh_sale_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    """重量列、次日达时段、损耗赔付。未开不加。"""
    if not enabled:
        return sql
    t = (item_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        low = table.lower()
        if low == t.lower():
            body = _inject_missing_columns(body, PRODUCT_WEIGH_COLUMNS)
        elif low == "order_line":
            body = _inject_missing_columns(body, ORDER_LINE_WEIGHT_COLUMNS)
        elif low == "sys_user":
            body = _inject_missing_columns(body, [("balance_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0")])
        else:
            return m.group(0)
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(repl, sql)
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?loss_policy`?\b", out):
        return out
    seed = f"""UPDATE {t} SET sell_by_weight=1, weight_unit='斤' WHERE id=1;
INSERT INTO delivery_slot (id, label, start_hm, end_hm, capacity, fulfill_mode, cutoff_hm, enabled, sort_no)
SELECT 3, '次日达', '09:00', '18:00', 20, 'next_day', '', 1, 30 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM delivery_slot WHERE id=3);
INSERT INTO loss_policy (id, enabled, cap_yuan)
SELECT 1, 1, 20.00 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM loss_policy WHERE id=1);
"""
    return out.rstrip() + "\n" + _WEIGH_SALE_DDL + "\n" + seed
