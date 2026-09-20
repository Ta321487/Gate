"""寄卖。开题写到才挂，挂在已有下单上。

同一用户提交，质检通过后才生成可买商品。不是多商家入驻，也不是图书馆借阅。
校园二手的成色列仍只跟校园二手皮，不从这里注入。
"""

from __future__ import annotations

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
