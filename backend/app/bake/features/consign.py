"""寄卖。开题写到才挂，挂在已有下单上。

同一用户提交，质检通过后才生成可买商品。不是多商家入驻，也不是图书馆借阅。
校园二手的成色列仍只跟校园二手皮，不从这里注入。
"""

from __future__ import annotations

import re

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

CONSIGN_CAP = "consign"

# 抽成、提现单独出现不开。锚点是寄卖本身。
_TERMS = (
    "寄卖",
    "寄售",
    "质检上架",
)

_NEIGHBORS = frozenset({"DOM-LIBRARY", "DOM-ACTIVITY"})


def _hit(text: str, terms: tuple[str, ...]) -> bool:
    return any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in terms)


def scan_consign(text: str, title: str = "") -> bool:
    return _hit(f"{title or ''}\n{text or ''}", _TERMS)


def merge_consign_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
    title: str = "",
) -> list[str]:
    out = list(caps or [])
    if (domain or "") in _NEIGHBORS or "order_lines" not in out:
        return [c for c in out if c != CONSIGN_CAP]
    if CONSIGN_CAP in out:
        return out
    if scan_consign(proposal_text or "", title):
        out.append(CONSIGN_CAP)
    return out


def apply_consign_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    from app.bake.schema.menu_utils import ensure_menu

    title = str(spec.get("title") or "")
    caps = merge_consign_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text or "",
        domain=spec.get("domain"),
        title=title,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if CONSIGN_CAP not in caps:
        return {**spec, "schema": schema}

    schema["consign"] = True
    labels = dict(schema.get("labels") or {})
    labels.setdefault("consignMenu", "寄卖质检")
    labels.setdefault("myConsignMenu", "我的寄卖")
    labels.setdefault(
        "consignHint",
        "质检通过后才会上架。订单完成后按当时的抽成记一笔，寄卖人再申请提现。",
    )
    schema["labels"] = labels

    menus = dict(schema.get("menus") or {})
    admin = list(menus.get("admin") or [])
    ensure_menu(
        admin,
        "consigns",
        {"key": "consigns", "label": "寄卖质检", "superOnly": False},
        before_key="orders",
    )
    menus["admin"] = admin
    user = list(menus.get("user") or [])
    ensure_menu(
        user,
        "my_consigns",
        {"key": "my_consigns", "label": "我的寄卖"},
        before_key="my_orders",
    )
    menus["user"] = user
    schema["menus"] = menus
    return {**spec, "schema": schema}


# --- SQL ensure (moved from fragments.py) ---

_CONSIGN_DDL = """
CREATE TABLE IF NOT EXISTS consign_item (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  title VARCHAR(200) NOT NULL DEFAULT '',
  expect_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  condition_note VARCHAR(64) NOT NULL DEFAULT '',
  status VARCHAR(16) NOT NULL DEFAULT 'pending',
  reject_reason VARCHAR(255) NOT NULL DEFAULT '',
  product_id BIGINT NULL,
  fee_rate DECIMAL(6,4) NOT NULL DEFAULT 0.1000,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS consign_ledger (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  consign_id BIGINT NOT NULL,
  order_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  gross_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  fee_rate DECIMAL(6,4) NOT NULL DEFAULT 0,
  payout_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  withdraw_status VARCHAR(16) NOT NULL DEFAULT 'ready',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_consign_order (consign_id, order_id)
);
"""

def ensure_consign_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    """寄卖单、成交账。未开不加。成色列不在这里注入。"""
    if not enabled:
        return sql
    t = (item_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?consign_item`?\b", sql):
        return sql
    seed = f"""INSERT INTO consign_item (id, username, title, expect_yuan, condition_note, status, fee_rate)
SELECT 9, '', '', 0, '', 'rate', 0.1000 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM consign_item WHERE status='rate');
INSERT INTO consign_item (id, username, title, expect_yuan, condition_note, status, fee_rate)
SELECT 1, 'user', '耳机', 80.00, '九成新', 'pending', 0.1000 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM consign_item WHERE id=1);
INSERT IGNORE INTO {t} (id, title, author, isbn, category_id, stock, status) VALUES
(5, '台灯', '45.00', 'CS-05', 2, 1, 'available');
INSERT INTO consign_item (id, username, title, expect_yuan, condition_note, status, product_id, fee_rate)
SELECT 2, 'user', '台灯', 45.00, '八成新', 'on_sale', 5, 0.1000 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM consign_item WHERE id=2);
INSERT IGNORE INTO {t} (id, title, author, isbn, category_id, stock, status) VALUES
(6, '键盘', '100.00', 'CS-06', 2, 0, 'unavailable');
INSERT INTO consign_item (id, username, title, expect_yuan, condition_note, status, product_id, fee_rate)
SELECT 3, 'user', '键盘', 100.00, '九成新', 'sold', 6, 0.1000 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM consign_item WHERE id=3);
INSERT IGNORE INTO biz_order (id, username, status, total_yuan, remark, receiver_name, receiver_phone, address_line, delivery_type) VALUES
(2, 'user', 'completed', 100.00, '', '王先生', '13800000002', '示例小区 3 栋 1201', '配送到家');
INSERT IGNORE INTO order_line (id, order_id, item_id, title, price_yuan, qty) VALUES
(2, 2, 6, '键盘', 100.00, 1);
INSERT INTO consign_ledger (id, consign_id, order_id, username, gross_yuan, fee_rate, payout_yuan, withdraw_status)
SELECT 1, 3, 2, 'user', 100.00, 0.1000, 90.00, 'ready' FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM consign_ledger WHERE id=1);
"""
    return sql.rstrip() + "\n" + _CONSIGN_DDL + "\n" + seed
