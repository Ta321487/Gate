"""购买审核与每月限购。开题写到才挂，挂在已有加购和下单上。

不是医院「处方开药」。医院那条仍不做。
哪些商品要审、每月限几件，写在商品上，由管理端改。
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

PURCHASE_GATE_CAP = "purchase_gate"

_TERMS = (
    "处方",
    "药师审核",
    "审核后购买",
    "限购",
    "每人每月",
)


def _hit(text: str, terms: tuple[str, ...]) -> bool:
    return any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in terms)


def scan_purchase_gate(text: str, title: str = "") -> bool:
    return _hit(f"{title or ''}\n{text or ''}", _TERMS)


def merge_purchase_gate_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
    title: str = "",
) -> list[str]:
    out = list(caps or [])
    # 挂号域的「处方开药」不是零售审方
    if (domain or "") == "DOM-HOSPITAL" or "order_lines" not in out:
        return [c for c in out if c != PURCHASE_GATE_CAP]
    if PURCHASE_GATE_CAP in out:
        return out
    if scan_purchase_gate(proposal_text or "", title):
        out.append(PURCHASE_GATE_CAP)
    return out


def apply_purchase_gate_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    from app.bake.schema.menu_utils import ensure_menu
    from app.bake.scene_scan import shop_catalog_kind

    title = str(spec.get("title") or "")
    caps = merge_purchase_gate_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text or "",
        domain=spec.get("domain"),
        title=title,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if PURCHASE_GATE_CAP not in caps:
        return {**spec, "schema": schema}

    schema["purchaseGate"] = True
    labels = dict(schema.get("labels") or {})
    pharmacy = shop_catalog_kind(title, proposal_text or "") == "retail_pharmacy"
    reviewer = "药师" if pharmacy else "审核员"
    labels.setdefault("purchasePermitMenu", "购买审核")
    labels.setdefault("permitReviewer", reviewer)
    labels.setdefault(
        "purchaseGateHint",
        "需审核的商品要先上传资料并通过，才能加购和下单。每月限购按本月未取消订单合计。",
    )
    schema["labels"] = labels

    if pharmacy:
        roles = dict(schema.get("roles") or {})
        sub = dict(roles.get("subadmin") or {})
        sub["id"] = "subadmin"
        sub["label"] = "药师"
        roles["subadmin"] = sub
        schema["roles"] = roles

    ents = dict(schema.get("entities") or {})
    arch = dict(ents.get("archive") or {})
    fields = [f for f in (arch.get("fields") or []) if isinstance(f, dict)]
    keys = {str(f.get("key") or "") for f in fields}
    if "needPermit" not in keys:
        fields.append({"key": "needPermit", "label": "需审核后购买", "type": "boolean"})
    if "monthLimit" not in keys:
        fields.append({"key": "monthLimit", "label": "每人每月限购", "type": "number"})
    arch["fields"] = fields
    ents["archive"] = arch
    schema["entities"] = ents

    menus = dict(schema.get("menus") or {})
    admin = list(menus.get("admin") or [])
    user = list(menus.get("user") or [])
    ensure_menu(
        admin,
        "purchase_permits",
        {"key": "purchase_permits", "label": "购买审核", "superOnly": False},
        before_key="orders",
    )
    ensure_menu(
        user,
        "my_permits",
        {"key": "my_permits", "label": "购买审核", "superOnly": False},
        before_key="my_orders",
    )
    menus["admin"] = admin
    menus["user"] = user
    schema["menus"] = menus
    return {**spec, "schema": schema}


# --- SQL ensure (moved from fragments.py) ---

PRODUCT_GATE_COLUMNS: list[tuple[str, str]] = [
    ("need_permit", "TINYINT NOT NULL DEFAULT 0"),
    ("month_limit", "INT NOT NULL DEFAULT 0"),
]

_PURCHASE_GATE_DDL = """\
CREATE TABLE IF NOT EXISTS purchase_permit (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  item_id BIGINT NULL,
  category_id BIGINT NULL,
  image_url VARCHAR(255) NOT NULL DEFAULT '',
  status VARCHAR(16) NOT NULL DEFAULT 'pending',
  reviewer VARCHAR(64) DEFAULT '',
  reject_reason VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  reviewed_at DATETIME NULL,
  KEY idx_permit_user_item (username, item_id),
  KEY idx_permit_user_cat (username, category_id)
);
"""

def ensure_purchase_gate_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    """购买审核表与商品上的开关、月限。未开不加列。"""
    if not enabled:
        return sql
    t = (item_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != t.lower():
            return m.group(0)
        body = _inject_missing_columns(body, PRODUCT_GATE_COLUMNS)
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(repl, sql)
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?purchase_permit`?\b", out):
        return out
    seed = (
        f"UPDATE {t} SET need_permit=1, month_limit=2 WHERE id=1;\n"
        f"UPDATE {t} SET need_permit=0, month_limit=0 WHERE id=2;\n"
        "INSERT INTO purchase_permit (username, item_id, image_url, status)\n"
        "SELECT 'user', 1, '/uploads/seed-permit.png', 'pending' FROM DUAL\n"
        "WHERE NOT EXISTS (SELECT 1 FROM purchase_permit WHERE username='user' AND item_id=1 AND status='pending');\n"
    )
    return out.rstrip() + "\n" + _PURCHASE_GATE_DDL + "\n" + seed
