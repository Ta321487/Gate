"""浅报废 / 盘点（E-08）：开题扫词才挂；无域默认。

复用 stock_io 的 stock_move 流水（类型 scrap / count）；缺 stock_io 时一并挂上以保证表与菜单闭环。
不做多仓调拨、RFID、手持机。
"""

from __future__ import annotations

import re

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

STOCK_SCRAP_CAP = "stock_scrap"
STOCK_COUNT_CAP = "stock_count"
STOCK_IO_CAP = "stock_io"

_SCRAP_TERMS = ("报废",)
_COUNT_TERMS = ("盘点", "库存盘点")


def scan_stock_scrap(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _SCRAP_TERMS)


def scan_stock_count(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _COUNT_TERMS)


def merge_stock_scrap_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
) -> list[str]:
    del domain
    out = list(caps or [])
    text = proposal_text or ""
    want_scrap = scan_stock_scrap(text)
    want_count = scan_stock_count(text)
    if not want_scrap and not want_count:
        return out
    if (want_scrap or want_count) and STOCK_IO_CAP not in out:
        out.append(STOCK_IO_CAP)
    if want_scrap and STOCK_SCRAP_CAP not in out:
        out.append(STOCK_SCRAP_CAP)
    if want_count and STOCK_COUNT_CAP not in out:
        out.append(STOCK_COUNT_CAP)
    return out


def attach_stock_scrap_labels(schema: dict[str, Any], caps: list[str]) -> None:
    labels = schema.setdefault("labels", {})
    scrap = STOCK_SCRAP_CAP in caps
    count = STOCK_COUNT_CAP in caps
    if scrap or count:
        parts = ["入库", "出库"]
        if scrap:
            parts.append("报废")
        if count:
            parts.append("盘点")
        labels["stockMovesTitle"] = "库存变动登记"
        labels["stockMovesLead"] = (
            "登记"
            + "、".join(parts)
            + "并即时调整库存；单仓模式，无多仓调拨与 RFID。"
        )
        labels.setdefault("stockScrapVerb", "报废")
        labels.setdefault("stockCountVerb", "盘点")
        labels.setdefault(
            "stockCountHint",
            "录入实盘数量后过账：库存调整为实盘并记差额流水。",
        )
    if scrap:
        # 独立报废单：pending → approved/rejected，通过后才扣库存写 scrap 流水
        opts = schema.setdefault("stockScrapOpts", {})
        if isinstance(opts, dict):
            opts["approveFlow"] = True
        labels.setdefault(
            "scrapApproveHint",
            "报废须先提交申请，审批通过后才扣减库存并记报废流水。",
        )
        labels.setdefault("scrapPendingTitle", "待审报废单")
        labels.setdefault("scrapApproveVerb", "通过报废")
        labels.setdefault("scrapRejectVerb", "驳回报废")


def apply_stock_scrap_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    text = proposal_text or ""
    caps = merge_stock_scrap_capabilities(
        list(spec.get("capabilities") or []),
        text,
        domain=spec.get("domain"),
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps

    if STOCK_SCRAP_CAP in caps or STOCK_COUNT_CAP in caps:
        # 保证入出库菜单存在（扫词可能刚补上 stock_io）
        if STOCK_IO_CAP in caps:
            from app.bake.features.stock_io import attach_stock_io_menus

            attach_stock_io_menus(schema)
        attach_stock_scrap_labels(schema, caps)
        from app.bake.gate_contracts import merge_stock_scrap_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_stock_scrap_gate(gate, caps)

        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if STOCK_SCRAP_CAP in caps and "物资报废" not in names:
            features.append({"name": "物资报废", "status": "flow"})
        if STOCK_SCRAP_CAP in caps and "报废审批单" not in names:
            features.append({"name": "报废审批单", "status": "flow"})
        if STOCK_COUNT_CAP in caps and "库存盘点" not in names:
            features.append({"name": "库存盘点", "status": "flow"})
        spec["features"] = features

    spec["schema"] = schema
    return spec


# --- SQL ensure (moved from fragments.py) ---

_SCRAP_REQUEST_DDL = """
CREATE TABLE IF NOT EXISTS scrap_request (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  item_id BIGINT NOT NULL,
  item_title VARCHAR(200) DEFAULT '',
  qty INT NOT NULL,
  reason VARCHAR(255) NOT NULL DEFAULT '',
  status VARCHAR(16) NOT NULL DEFAULT 'pending',
  applicant VARCHAR(64) NOT NULL DEFAULT '',
  handler VARCHAR(64) DEFAULT '',
  handle_note VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  handled_at DATETIME NULL,
  KEY idx_scrap_req_status (status, id),
  KEY idx_scrap_req_item (item_id, id)
);
"""

def ensure_scrap_request_sql(sql: str, *, enabled: bool) -> str:
    """报废审批单表：开 stock_scrap 且走审批流时注入。"""
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?scrap_request`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _SCRAP_REQUEST_DDL
