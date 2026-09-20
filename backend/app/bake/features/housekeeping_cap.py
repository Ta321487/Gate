"""酒店清洁任务。开题写到才挂；依赖房态板。复用 room_status_log，不另建任务表。

裸「清洁工/保洁员」不够开本岛（防健身房误读）；须客房保洁类词或伞扫酒店管理。
"""

from __future__ import annotations

from typing import Any

from app.bake.features.room_board import (
    ensure_room_board_dep,
    pms_domain_ok,
    scan_hotel_pms_umbrella,
)
from app.bake.proposal_lexicon import keyword_mentioned

HOUSEKEEPING_CAP = "housekeeping"

_TERMS = (
    "客房保洁",
    "客房打扫",
    "客房整理",
    "清洁任务",
    "楼层保洁",
    "客房服务",
)


def _hit(text: str, terms: tuple[str, ...]) -> bool:
    return any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in terms)


def scan_housekeeping_cap(text: str, title: str = "") -> bool:
    blob = f"{title or ''}\n{text or ''}"
    if scan_hotel_pms_umbrella(text, title):
        return True
    return _hit(blob, _TERMS)


def merge_housekeeping_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
    title: str = "",
) -> list[str]:
    out = list(caps or [])
    if "slot_reserve" not in out or not pms_domain_ok(domain, title, proposal_text):
        return [c for c in out if c != HOUSEKEEPING_CAP]
    if HOUSEKEEPING_CAP not in out and scan_housekeeping_cap(proposal_text or "", title):
        out.append(HOUSEKEEPING_CAP)
    if HOUSEKEEPING_CAP in out:
        out = ensure_room_board_dep(out)
    return out


def apply_housekeeping_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    from app.bake.features.room_board import apply_room_board_to_spec
    from app.bake.schema.menu_utils import ensure_menu

    title = str(spec.get("title") or "")
    caps = merge_housekeeping_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text or "",
        domain=spec.get("domain"),
        title=title,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    spec = {**spec, "schema": schema}
    if HOUSEKEEPING_CAP not in caps:
        return spec

    spec = apply_room_board_to_spec(spec, proposal_text or "")
    schema = dict(spec.get("schema") or {})
    caps = list(spec.get("capabilities") or [])
    schema["capabilities"] = caps
    schema["housekeepingTasks"] = True
    labels = dict(schema.get("labels") or {})
    labels.setdefault("cleanTasksMenu", "清洁任务")
    labels.setdefault(
        "cleanTasksHint",
        "列出待打扫的房间。打扫完成后点完成，房间回到空房。",
    )
    schema["labels"] = labels
    menus = dict(schema.get("menus") or {})
    admin = list(menus.get("admin") or [])
    # 主管可查清洁进度；现场岗走 /staff/clean
    ensure_menu(
        admin,
        "clean_tasks",
        {
            "key": "clean_tasks",
            "label": labels.get("cleanTasksMenu", "清洁任务"),
            "superOnly": False,
        },
        before_key="orders",
    )
    menus["admin"] = admin
    schema["menus"] = menus
    return {**spec, "schema": schema}
