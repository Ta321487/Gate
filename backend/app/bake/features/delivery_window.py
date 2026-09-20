"""配送时段与节日加价。开题写到才挂，挂在已有订单上。

不是预约域的 resource_slot，也不是商品活动价 flash_price。
管理端维护时段和节日区间；用户在结算页从这份列表里选。
"""

from __future__ import annotations

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
