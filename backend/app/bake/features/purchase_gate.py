"""购买审核与每月限购。开题写到才挂，挂在已有加购和下单上。

不是医院「处方开药」。医院那条仍不做。
哪些商品要审、每月限几件，写在商品上，由管理端改。
"""

from __future__ import annotations

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
