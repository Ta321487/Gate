"""影院选座购票（seat_select）：场次座位图占座 + 订单（C-15）。"""

from __future__ import annotations

import re
from typing import Any

from app.bake.proposal_lexicon import pattern_mentioned

SEAT_SELECT_CAP = "seat_select"

_SEAT_SIGNALS = re.compile(
    r"选座购票|影院选座|电影票选座|在线选座|座位图购票|影院售票|电影院购票|场次选座|影院票务选座|观影选座"
)


def scan_seat_select(text: str) -> bool:
    return pattern_mentioned(text or "", _SEAT_SIGNALS, ignore_contrast=True)


def seat_select_wanted(
    *,
    domain: str | None,
    capabilities: list[str] | None = None,
    proposal_text: str = "",
) -> bool:
    caps = list(capabilities or [])
    if SEAT_SELECT_CAP in caps:
        return True
    if (domain or "") == "DOM-CINEMA":
        return True
    return scan_seat_select(proposal_text)


def merge_seat_select_capabilities(
    caps: list[str],
    proposal_text: str = "",
    *,
    domain: str | None = None,
    force: bool = False,
) -> list[str]:
    out = list(caps or [])
    want = force or seat_select_wanted(
        domain=domain,
        capabilities=out,
        proposal_text=proposal_text,
    )
    if want and SEAT_SELECT_CAP not in out:
        out.append(SEAT_SELECT_CAP)
    if want and "order_lines" not in out:
        out.append("order_lines")
    return out


def attach_seat_select_menus(schema: dict[str, Any]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    user = menus.setdefault("user", [])
    # 场次列表走选座入口；保留订单
    ensure_menu(
        user,
        "seat_shows",
        {"key": "seat_shows", "label": "场次选座"},
        before_key="my_orders",
    )
    # 影院主路径不走购物车/地址簿/留言（选座下单为主）
    drop = {"cart", "addresses", "guestbook"}
    menus["user"] = [
        m for m in user if not (isinstance(m, dict) and m.get("key") in drop)
    ]
    admin = menus.setdefault("admin", [])
    menus["admin"] = [
        m for m in admin if not (isinstance(m, dict) and m.get("key") == "guestbook")
    ]
    labels = schema.setdefault("labels", {})
    labels.setdefault("seatShowsTitle", "场次选座")
    labels.setdefault("seatShowsLead", "选择场次后进入座位图；确认后生成订单并占座（无真锁座）。")
    labels.setdefault("seatMapTitle", "选座购票")
    ents = schema.setdefault("entities", {})
    if "seat" not in ents:
        ents["seat"] = {
            "key": "seat",
            "label": "座位",
            "labelPlural": "座位",
            "rows": 6,
            "cols": 8,
        }


def apply_seat_select_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    domain = spec.get("domain")
    caps = merge_seat_select_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text,
        domain=domain,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps

    if SEAT_SELECT_CAP in caps:
        attach_seat_select_menus(schema)
        from app.bake.gate_contracts import merge_seat_select_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_seat_select_gate(gate, caps)

        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "选座购票" not in names:
            features.append({"name": "选座购票", "status": "flow"})
        spec["features"] = features

        ents = list(spec.get("entities") or [])
        if "Seat" not in ents:
            if "Notice" in ents:
                ents.insert(ents.index("Notice"), "Seat")
            else:
                ents.append("Seat")
            spec["entities"] = ents

    spec["schema"] = schema
    return spec
