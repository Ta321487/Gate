"""浅进销存（stock_io）：入库/出库登记 + 库存流水（C-17）。"""

from __future__ import annotations

import re
from typing import Any

from app.bake.proposal_lexicon import pattern_mentioned

STOCK_IO_CAP = "stock_io"

_STOCK_IO_SIGNALS = re.compile(
    r"进销存|入库单|出库单|出入库登记|入库出库|出入库管理|库存台账|库存流水|"
    r"浅进销存|仓储出入库|物资出入库|入出存"
)

_STOCK_WARN_NOTIFY_TERMS = (
    "低库存提醒",
    "库存预警通知",
    "库存不足提醒",
    "低库存站内",
    "库存预警站内",
    "低库存通知",
    "库存预警消息",
    "自动库存预警",
)


def scan_stock_io(text: str) -> bool:
    return pattern_mentioned(text or "", _STOCK_IO_SIGNALS, ignore_contrast=True)


def scan_stock_warn_notify(text: str) -> bool:
    """低库存站内信提醒总管；工作台图表仍默认有，本开关加深消息。"""
    from app.bake.proposal_lexicon import keyword_mentioned

    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _STOCK_WARN_NOTIFY_TERMS)


def stock_io_wanted(
    *,
    domain: str | None,
    capabilities: list[str] | None = None,
    proposal_text: str = "",
) -> bool:
    caps = list(capabilities or [])
    if STOCK_IO_CAP in caps:
        return True
    if (domain or "") == "DOM-ASSET":
        return True
    return scan_stock_io(proposal_text)


def merge_stock_io_capabilities(
    caps: list[str],
    proposal_text: str = "",
    *,
    domain: str | None = None,
    force: bool = False,
) -> list[str]:
    out = list(caps or [])
    want = force or stock_io_wanted(
        domain=domain,
        capabilities=out,
        proposal_text=proposal_text,
    )
    if want and STOCK_IO_CAP not in out:
        out.append(STOCK_IO_CAP)
    return out


def attach_stock_io_menus(schema: dict[str, Any]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    admin = menus.setdefault("admin", [])
    ensure_menu(
        admin,
        "stock_moves",
        {"key": "stock_moves", "label": "入出库登记", "superOnly": False},
        before_key="content",
    )
    ensure_menu(
        admin,
        "stock_ledger",
        {"key": "stock_ledger", "label": "库存流水", "superOnly": False},
        before_key="content",
    )
    labels = schema.setdefault("labels", {})
    labels.setdefault("stockMovesTitle", "入出库登记")
    labels.setdefault(
        "stockMovesLead",
        "登记入库或出库并即时调整库存；单仓模式，无多仓调拨与 RFID。",
    )
    labels.setdefault("stockLedgerTitle", "库存流水")
    ents = schema.setdefault("entities", {})
    if "stock_io" not in ents:
        ents["stock_io"] = {
            "key": "stock_io",
            "label": "入出库",
            "labelPlural": "入出库记录",
        }


def apply_stock_io_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    domain = spec.get("domain")
    caps = merge_stock_io_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text,
        domain=domain,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps

    if STOCK_IO_CAP in caps:
        attach_stock_io_menus(schema)
        from app.bake.gate_contracts import merge_stock_io_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_stock_io_gate(gate, caps)

        # 工作台低库存图表默认有；开题写「低库存提醒/库存预警通知」才发站内信
        if scan_stock_warn_notify(proposal_text or ""):
            schema["stockWarnNotify"] = True
            try:
                below = int(schema.get("stockWarnBelow") or 0)
            except (TypeError, ValueError):
                below = 0
            if below <= 0:
                schema["stockWarnBelow"] = 10

        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "入出库与库存流水" not in names:
            features.append({"name": "入出库与库存流水", "status": "flow"})
        if schema.get("stockWarnNotify") and "低库存站内提醒" not in names:
            features.append({"name": "低库存站内提醒", "status": "flow"})
        spec["features"] = features

        ents = list(spec.get("entities") or [])
        if "StockIo" not in ents:
            if "Notice" in ents:
                ents.insert(ents.index("Notice"), "StockIo")
            else:
                ents.append("StockIo")
            spec["entities"] = ents

    spec["schema"] = schema
    return spec


# --- SQL ensure (moved from fragments.py) ---

_STOCK_IO_DDL = """
CREATE TABLE IF NOT EXISTS stock_move (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  move_type VARCHAR(16) NOT NULL,
  item_id BIGINT NOT NULL,
  item_title VARCHAR(200) DEFAULT '',
  qty INT NOT NULL,
  remark VARCHAR(255) DEFAULT '',
  operator VARCHAR(64) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_stock_move_item (item_id, id),
  KEY idx_stock_move_type (move_type, id)
);
"""

def ensure_stock_io_sql(sql: str, *, enabled: bool) -> str:
    """能力开启时幂等补入出库流水表。"""
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?stock_move`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _STOCK_IO_DDL
