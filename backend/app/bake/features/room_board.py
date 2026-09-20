"""酒店房态板。开题写到才挂，挂在 DOM-HOTEL 预约壳上。

民宿/寄养不开。客房预约单写不挂。伞扫「酒店管理」三岛同开。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

ROOM_BOARD_CAP = "room_board"

# 字符串集合，避免与 front_desk / housekeeping_cap 循环导入
PMS_CAPS = frozenset({ROOM_BOARD_CAP, "front_desk", "housekeeping"})

_ROOM_BOARD_TERMS = (
    "房态",
    "房态图",
    "房态板",
    "房间状态",
    "空房",
    "维修房",
)

_UMBRELLA = (
    "酒店管理",
    "酒店管理系统",
)


def _hit(text: str, terms: tuple[str, ...]) -> bool:
    return any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in terms)


def scan_hotel_pms_umbrella(text: str, title: str = "") -> bool:
    return _hit(f"{title or ''}\n{text or ''}", _UMBRELLA)


def scan_room_board(text: str, title: str = "") -> bool:
    blob = f"{title or ''}\n{text or ''}"
    return _hit(blob, _ROOM_BOARD_TERMS) or scan_hotel_pms_umbrella(text, title)


def pms_domain_ok(domain: str | None, title: str = "", proposal_text: str = "") -> bool:
    if (domain or "") != "DOM-HOTEL":
        return False
    from app.bake.scene_scan import hotel_product_kind

    kind = hotel_product_kind(title or "", proposal_text or "")
    return kind not in ("homestay", "boarding")


def strip_pms_caps(caps: list[str]) -> list[str]:
    return [c for c in caps if c not in PMS_CAPS]


def ensure_room_board_dep(out: list[str]) -> list[str]:
    if ("front_desk" in out or "housekeeping" in out or ROOM_BOARD_CAP in out) and (
        ROOM_BOARD_CAP not in out
    ):
        out = list(out) + [ROOM_BOARD_CAP]
    return out


def merge_room_board_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
    title: str = "",
) -> list[str]:
    out = list(caps or [])
    if "slot_reserve" not in out or not pms_domain_ok(domain, title, proposal_text):
        return strip_pms_caps(out)
    if ROOM_BOARD_CAP in out:
        return out
    if scan_room_board(proposal_text or "", title):
        out.append(ROOM_BOARD_CAP)
    return out


def apply_room_board_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    from app.bake.schema.menu_utils import ensure_menu

    title = str(spec.get("title") or "")
    caps = merge_room_board_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text or "",
        domain=spec.get("domain"),
        title=title,
    )
    caps = ensure_room_board_dep(caps)
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if ROOM_BOARD_CAP not in caps:
        return {**spec, "schema": schema}

    schema["roomBoard"] = True
    labels = dict(schema.get("labels") or {})
    labels.setdefault("roomBoardMenu", "房态板")
    labels.setdefault(
        "roomBoardHint",
        "按房间查看空房、已订、入住中、待打扫和维修。点格子可改状态或分房。",
    )
    schema["labels"] = labels
    menus = dict(schema.get("menus") or {})
    admin = list(menus.get("admin") or [])
    ensure_menu(
        admin,
        "room_board",
        {
            "key": "room_board",
            "label": labels.get("roomBoardMenu", "房态板"),
            "superOnly": False,
        },
        before_key="orders",
    )
    menus["admin"] = admin
    schema["menus"] = menus
    return {**spec, "schema": schema}
