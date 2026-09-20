"""旧书回收。开题写到才挂，挂在已有商品上架上。

前半是回收单：估价、同意、上门、入库、上架。不同意就结束。
上架前不能购买。单独图书借阅不开。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

BUYBACK_CAP = "buyback"

_ANCHORS = ("旧书回收", "上门回收")


def recycle_opening(text: str, title: str = "") -> bool:
    blob = f"{title or ''}\n{text or ''}"
    if any(keyword_mentioned(blob, kw, ignore_contrast=True) for kw in _ANCHORS):
        return True
    return keyword_mentioned(blob, "估价", ignore_contrast=True) and keyword_mentioned(
        blob, "回收", ignore_contrast=True
    )


def scan_buyback(text: str, title: str = "") -> bool:
    return recycle_opening(text, title)


def merge_buyback_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
    title: str = "",
) -> list[str]:
    out = list(caps or [])
    if (domain or "") != "DOM-SHOP" or "order_lines" not in out:
        return [c for c in out if c != BUYBACK_CAP]
    if BUYBACK_CAP in out:
        return out
    if scan_buyback(proposal_text or "", title):
        out.append(BUYBACK_CAP)
    return out


def apply_buyback_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    from app.bake.schema.menu_utils import ensure_menu

    title = str(spec.get("title") or "")
    caps = merge_buyback_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text or "",
        domain=spec.get("domain"),
        title=title,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if BUYBACK_CAP not in caps:
        return {**spec, "schema": schema}

    schema["buyback"] = True
    labels = dict(schema.get("labels") or {})
    labels.setdefault("buybackMenu", "旧书回收")
    labels.setdefault("buybackSlotMenu", "上门时段")
    labels.setdefault("myBuybackMenu", "我的回收")
    labels.setdefault(
        "buybackHint",
        "先报价，同意后上门。入库后再上架，上架后才能购买。不同意报价则本单结束。",
    )
    schema["labels"] = labels
    menus = dict(schema.get("menus") or {})
    admin = list(menus.get("admin") or [])
    ensure_menu(
        admin,
        "buybacks",
        {"key": "buybacks", "label": "旧书回收", "superOnly": False},
    )
    ensure_menu(
        admin,
        "buyback_slots",
        {"key": "buyback_slots", "label": "上门时段", "superOnly": False},
    )
    menus["admin"] = admin
    user = list(menus.get("user") or [])
    ensure_menu(user, "my_buybacks", {"key": "my_buybacks", "label": "我的回收"})
    menus["user"] = user
    schema["menus"] = menus
    return {**spec, "schema": schema}
