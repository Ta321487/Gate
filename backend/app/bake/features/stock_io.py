"""浅进销存（stock_io）：入库/出库登记 + 库存流水（C-17）。"""

from __future__ import annotations

import re
from typing import Any

STOCK_IO_CAP = "stock_io"

_STOCK_IO_SIGNALS = re.compile(
    r"进销存|入库单|出库单|出入库登记|入库出库|出入库管理|库存台账|库存流水|"
    r"浅进销存|仓储出入库|物资出入库|入出存"
)


def scan_stock_io(text: str) -> bool:
    return bool(_STOCK_IO_SIGNALS.search(text or ""))


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
        {"key": "stock_moves", "label": "入出库登记", "superOnly": True},
        before_key="content",
    )
    ensure_menu(
        admin,
        "stock_ledger",
        {"key": "stock_ledger", "label": "库存流水", "superOnly": True},
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

        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "入出库与库存流水" not in names:
            features.append({"name": "入出库与库存流水", "status": "flow"})
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
