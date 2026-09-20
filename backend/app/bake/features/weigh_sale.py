"""按重量卖，并带次日达和损耗赔付。开题写到才挂，挂在已有下单上。

生鲜皮只换分类，不因货皮加重量列。次日达复用配送时段，不另做一套履约。
"""

from __future__ import annotations

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
