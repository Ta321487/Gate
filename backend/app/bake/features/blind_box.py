"""盲盒。开题写到才挂，挂在已有下单上。

付款买的是盒子，不是某一个奖品。抽中之后才扣奖品库存。
保底次数写在盒子商品上，奖池由管理端维护。不是活动抽奖，也不是影院选座。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

BLIND_BOX_CAP = "blind_box"

_TERMS = (
    "盲盒",
    "概率",
    "保底",
    "隐藏款",
)

# 活动抽奖、影院选座、拼车都不是零售盲盒
_NEIGHBORS = frozenset({"DOM-ACTIVITY", "DOM-CINEMA", "DOM-CARPOOL"})


def _hit(text: str, terms: tuple[str, ...]) -> bool:
    return any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in terms)


def scan_blind_box(text: str, title: str = "") -> bool:
    return _hit(f"{title or ''}\n{text or ''}", _TERMS)


def merge_blind_box_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
    title: str = "",
) -> list[str]:
    out = list(caps or [])
    if (domain or "") in _NEIGHBORS or "order_lines" not in out:
        return [c for c in out if c != BLIND_BOX_CAP]
    if BLIND_BOX_CAP in out:
        return out
    if scan_blind_box(proposal_text or "", title):
        out.append(BLIND_BOX_CAP)
    return out


def apply_blind_box_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    from app.bake.schema.menu_utils import ensure_menu

    title = str(spec.get("title") or "")
    caps = merge_blind_box_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text or "",
        domain=spec.get("domain"),
        title=title,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if BLIND_BOX_CAP not in caps:
        return {**spec, "schema": schema}

    schema["blindBox"] = True
    labels = dict(schema.get("labels") or {})
    labels.setdefault("blindBoxMenu", "盲盒奖池")
    labels.setdefault(
        "blindBoxHint",
        "买家购买的是盲盒。开出的奖品记在订单上，保底按该盲盒的设置计算。",
    )
    schema["labels"] = labels

    ents = dict(schema.get("entities") or {})
    arch = dict(ents.get("archive") or {})
    fields = [f for f in (arch.get("fields") or []) if isinstance(f, dict)]
    keys = {str(f.get("key") or "") for f in fields}
    if "pityN" not in keys:
        fields.append({"key": "pityN", "label": "保底次数", "type": "number"})
    arch["fields"] = fields
    ents["archive"] = arch
    schema["entities"] = ents

    menus = dict(schema.get("menus") or {})
    admin = list(menus.get("admin") or [])
    ensure_menu(
        admin,
        "blind_pools",
        {"key": "blind_pools", "label": "盲盒奖池", "superOnly": False},
        before_key="orders",
    )
    menus["admin"] = admin
    schema["menus"] = menus
    return {**spec, "schema": schema}
