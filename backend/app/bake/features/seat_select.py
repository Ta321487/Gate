"""影院选座购票（seat_select）：场次座位图占座 + 订单（C-15）。"""

from __future__ import annotations

import re
from typing import Any

from app.bake.proposal_lexicon import pattern_mentioned

SEAT_SELECT_CAP = "seat_select"

_SEAT_SIGNALS = re.compile(
    r"选座购票|影院选座|电影票选座|在线选座|座位图购票|影院售票|电影院购票|场次选座|影院票务选座|观影选座"
)
# 材料点名购物车模块时与选座并存（默仍摘车，避免单场馆题多挂商城壳）
_CART_NAMED = re.compile(r"购物车")


def scan_seat_select(text: str) -> bool:
    return pattern_mentioned(text or "", _SEAT_SIGNALS, ignore_contrast=True)


def scan_cart_named(text: str) -> bool:
    """开题/任务书点名「购物车」——与选座主路径可并存。"""
    return pattern_mentioned(text or "", _CART_NAMED, ignore_contrast=True)


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


def attach_seat_select_menus(
    schema: dict[str, Any], *, keep_cart: bool = False
) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    user = menus.setdefault("user", [])
    # 答辩主路径：用户端只挂「场次选座」进座位图；勿并挂「浏览场次/场次目录」抢入口
    ensure_menu(
        user,
        "seat_shows",
        {"key": "seat_shows", "label": "场次选座"},
        before_key="my_orders",
    )
    # 摘地址簿/留言；默认摘购物车。材料点名购物车则保留（仍不挂物流地址簿）
    # 用户侧 archive 与 seat_shows 同看场次 → 摘掉，管理端场次管理保留
    drop = {"addresses", "guestbook", "archive"}
    if not keep_cart:
        drop.add("cart")
    menus["user"] = [
        m for m in user if not (isinstance(m, dict) and m.get("key") in drop)
    ]
    if keep_cart:
        ensure_menu(
            user,
            "cart",
            {"key": "cart", "label": "购物车"},
            before_key="my_orders",
        )
        schema["seatSelectKeepCart"] = True
    else:
        schema.pop("seatSelectKeepCart", None)
    admin = menus.setdefault("admin", [])
    menus["admin"] = [
        m for m in admin if not (isinstance(m, dict) and m.get("key") == "guestbook")
    ]
    labels = schema.setdefault("labels", {})
    labels["userHomePath"] = "/seats/shows"
    labels.setdefault("seatShowsTitle", "场次选座")
    labels.setdefault(
        "seatShowsLead",
        "选择场次后进入座位图，确认购票后出票。开场后该场次不再售票。",
    )
    labels.setdefault("seatMapTitle", "选座购票")
    labels.setdefault("seatSelectCta", "选座")
    if keep_cart:
        labels.setdefault(
            "cartPageLead",
            "主路径请先在「场次选座」里自选座位购票；"
            "购物车用于先加场次再结算，结算时自动分配空闲座位。柜台取票，无物流配送。",
        )
        labels.setdefault("cinemaCartFulfillLabel", "柜台取票")
    ents = schema.setdefault("entities", {})
    if "seat" not in ents:
        ents["seat"] = {
            "key": "seat",
            "label": "座位",
            "labelPlural": "座位",
            "rows": 6,
            "cols": 8,
            "maxRows": 15,
            "maxCols": 16,
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
    blob = f"{spec.get('title') or ''} {proposal_text or ''}"
    keep_cart = scan_cart_named(blob)

    if SEAT_SELECT_CAP in caps:
        attach_seat_select_menus(schema, keep_cart=keep_cart)
        from app.bake.gate_contracts import merge_seat_select_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_seat_select_gate(gate, caps)

        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "选座购票" not in names:
            features.append({"name": "选座购票", "status": "flow"})
        if keep_cart and "购物车" not in names:
            features.append({"name": "购物车", "status": "module"})
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
