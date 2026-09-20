"""酒店前台登记与退房结算。开题写到才挂；依赖房态板。

cap id 为 front_desk（域默认 checkin 是口令签到，勿撞名）。表名可用 checkin。
"""

from __future__ import annotations

from typing import Any

from app.bake.features.room_board import (
    ensure_room_board_dep,
    pms_domain_ok,
    scan_hotel_pms_umbrella,
)
from app.bake.proposal_lexicon import keyword_mentioned

FRONT_DESK_CAP = "front_desk"

_TERMS = (
    "前台登记",
    "入住登记",
    "退房结算",
    "消费挂账",
    "押金",
)


def _hit(text: str, terms: tuple[str, ...]) -> bool:
    return any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in terms)


def scan_front_desk(text: str, title: str = "") -> bool:
    blob = f"{title or ''}\n{text or ''}"
    if scan_hotel_pms_umbrella(text, title):
        return True
    # 裸「押金」在租车等域也常见；须与入住/退房/前台语境同现，或明确登记词
    if _hit(blob, ("前台登记", "入住登记", "退房结算", "消费挂账")):
        return True
    if _hit(blob, ("押金",)) and _hit(blob, ("入住", "退房", "前台", "客房")):
        return True
    return False


def merge_front_desk_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
    title: str = "",
) -> list[str]:
    out = list(caps or [])
    if "slot_reserve" not in out or not pms_domain_ok(domain, title, proposal_text):
        return [c for c in out if c != FRONT_DESK_CAP]
    if FRONT_DESK_CAP not in out and scan_front_desk(proposal_text or "", title):
        out.append(FRONT_DESK_CAP)
    if FRONT_DESK_CAP in out:
        out = ensure_room_board_dep(out)
    return out


def apply_front_desk_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    from app.bake.features.room_board import apply_room_board_to_spec
    from app.bake.schema.menu_utils import ensure_menu

    title = str(spec.get("title") or "")
    caps = merge_front_desk_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text or "",
        domain=spec.get("domain"),
        title=title,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    spec = {**spec, "schema": schema}
    if FRONT_DESK_CAP not in caps:
        return spec

    spec = apply_room_board_to_spec(spec, proposal_text or "")
    schema = dict(spec.get("schema") or {})
    caps = list(spec.get("capabilities") or [])
    schema["capabilities"] = caps
    schema["frontDesk"] = True
    labels = dict(schema.get("labels") or {})
    labels.setdefault("frontCheckinMenu", "前台登记")
    labels.setdefault("frontCheckoutMenu", "退房结算")
    labels.setdefault(
        "frontDeskHint",
        "前台为住客登记入住、收取押金、记下挂账，退房时一并结算。",
    )
    schema["labels"] = labels

    order = dict((schema.get("entities") or {}).get("order") or {})
    states = dict(order.get("states") or {})
    states.setdefault("shipped", "已入住")
    states.setdefault("completed", "已退房")
    verbs = dict(order.get("verbs") or {})
    verbs.setdefault("ship", "办理登记")
    verbs.setdefault("complete", "办理退房")
    order["states"] = states
    order["verbs"] = verbs
    order["frontDesk"] = True
    ents = dict(schema.get("entities") or {})
    ents["order"] = order
    schema["entities"] = ents

    menus = dict(schema.get("menus") or {})
    admin = list(menus.get("admin") or [])
    ensure_menu(
        admin,
        "front_checkin",
        {
            "key": "front_checkin",
            "label": labels.get("frontCheckinMenu", "前台登记"),
            "superOnly": False,
        },
        before_key="orders",
    )
    ensure_menu(
        admin,
        "front_checkout",
        {
            "key": "front_checkout",
            "label": labels.get("frontCheckoutMenu", "退房结算"),
            "superOnly": False,
        },
        before_key="orders",
    )
    menus["admin"] = admin
    schema["menus"] = menus
    return {**spec, "schema": schema}
