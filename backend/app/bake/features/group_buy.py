"""拼团。开题写到才挂，挂在已有订单上。

不是活动报名，也不是拼车。不加定时任务：打开订单或下单时顺手扫描过期团。
成团人数和截止时间由管理端维护，用户只对开着的团开团或参团。
"""

from __future__ import annotations

import re

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

GROUP_BUY_CAP = "group_buy"

_TERMS = ("拼团", "成团", "未成团")
_NEIGHBORS = frozenset({"DOM-ACTIVITY", "DOM-CARPOOL"})


def _hit(text: str) -> bool:
    blob = text or ""
    return any(keyword_mentioned(blob, kw, ignore_contrast=True) for kw in _TERMS)


def scan_group_buy(text: str, title: str = "") -> bool:
    return _hit(f"{title or ''}\n{text or ''}")


def merge_group_buy_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
    title: str = "",
) -> list[str]:
    out = list(caps or [])
    if (domain or "") in _NEIGHBORS or "order_lines" not in out:
        return [c for c in out if c != GROUP_BUY_CAP]
    if GROUP_BUY_CAP in out:
        return out
    if scan_group_buy(proposal_text or "", title):
        out.append(GROUP_BUY_CAP)
    return out


def apply_group_buy_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    from app.bake.schema.menu_utils import ensure_menu

    title = str(spec.get("title") or "")
    caps = merge_group_buy_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text or "",
        domain=spec.get("domain"),
        title=title,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if GROUP_BUY_CAP not in caps:
        return {**spec, "schema": schema}

    schema["groupBuy"] = True
    labels = dict(schema.get("labels") or {})
    labels.setdefault("groupBuyMenu", "拼团")
    labels.setdefault(
        "groupBuyHint",
        "选择一个未截止的团。人数和截止时间以该团为准，人齐后才能发货，过期未齐则取消并退回余额。",
    )
    schema["labels"] = labels

    ents = dict(schema.get("entities") or {})
    order = dict(ents.get("order") or {})
    states = dict(order.get("states") or {})
    states["grouping"] = "待成团"
    order["states"] = states
    ents["order"] = order
    schema["entities"] = ents

    menus = dict(schema.get("menus") or {})
    admin = list(menus.get("admin") or [])
    ensure_menu(
        admin,
        "group_campaigns",
        {"key": "group_campaigns", "label": "拼团", "superOnly": False},
        before_key="orders",
    )
    menus["admin"] = admin
    schema["menus"] = menus
    return {**spec, "schema": schema}


# --- SQL ensure (moved from fragments.py) ---

_GROUP_BUY_DDL = """\
CREATE TABLE IF NOT EXISTS group_campaign (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  item_id BIGINT NOT NULL,
  target_size INT NOT NULL,
  deadline DATETIME NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'open',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_group_item (item_id, status)
);
CREATE TABLE IF NOT EXISTS group_member (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  campaign_id BIGINT NOT NULL,
  order_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  UNIQUE KEY uk_group_user (campaign_id, username),
  KEY idx_group_order (order_id)
);
"""

_GROUP_BUY_SEED = """\
INSERT INTO group_campaign (item_id, target_size, deadline, status)
SELECT 1, 3, DATE_ADD(NOW(), INTERVAL 2 DAY), 'open' FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM group_campaign WHERE item_id=1 AND status='open');
INSERT INTO group_member (campaign_id, order_id, username)
SELECT c.id, 1, 'demo_joiner' FROM group_campaign c
WHERE c.item_id=1 AND c.status='open'
AND NOT EXISTS (SELECT 1 FROM group_member m WHERE m.campaign_id=c.id AND m.username='demo_joiner')
LIMIT 1;
INSERT INTO group_campaign (item_id, target_size, deadline, status)
SELECT 2, 3, DATE_SUB(NOW(), INTERVAL 1 DAY), 'failed' FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM group_campaign WHERE status='failed');
"""

def ensure_group_buy_sql(sql: str, *, enabled: bool) -> str:
    """拼团两张表。未开不加，活动报名和拼车也不会走到这里。"""
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?group_campaign`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _GROUP_BUY_DDL + "\n" + _GROUP_BUY_SEED
