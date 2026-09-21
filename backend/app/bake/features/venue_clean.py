"""场馆/会议室保洁任务。开题写满才挂；复用档案 clean_status，不建酒店房态表。

裸「清洁工/保洁员」不够（与酒店 housekeeping 一致）。禁止挂 DOM-HOTEL。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

VENUE_CLEAN_CAP = "venue_clean"

_VENUE_DOMAINS = frozenset({"DOM-SALON", "DOM-MEETING", "DOM-PROPERTY"})

# 须写满业务词；裸「清洁工」不开（防健身房顺带一提）
_TERMS = (
    "保洁任务",
    "清洁管理",
    "场馆保洁",
    "场地清洁",
    "场地保洁",
    "驻场保洁",
    "会议室清洁",
    "清洁信息管理",
)


def _hit(text: str) -> bool:
    return any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in _TERMS)


def scan_venue_clean(text: str, title: str = "") -> bool:
    return _hit(f"{title or ''}\n{text or ''}")


def merge_venue_clean_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
    title: str = "",
) -> list[str]:
    out = list(caps or [])
    dom = (domain or "").strip().upper()
    if dom not in _VENUE_DOMAINS:
        return [c for c in out if c != VENUE_CLEAN_CAP]
    if VENUE_CLEAN_CAP in out:
        return out
    if scan_venue_clean(proposal_text or "", title):
        out.append(VENUE_CLEAN_CAP)
    return out


def apply_venue_clean_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    from app.bake.schema.menu_utils import ensure_menu

    title = str(spec.get("title") or "")
    caps = merge_venue_clean_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text or "",
        domain=spec.get("domain"),
        title=title,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if VENUE_CLEAN_CAP not in caps:
        return {**spec, "schema": schema}

    schema["venueCleanTasks"] = True
    labels = dict(schema.get("labels") or {})
    labels.setdefault("cleanTasksMenu", "保洁任务")
    labels.setdefault(
        "cleanTasksHint",
        "列出待清洁的场地/教室。打扫完成后点完成，状态改为已清洁。",
    )
    labels.setdefault("venueCleanMarkDirty", "标为待清洁")
    schema["labels"] = labels
    menus = dict(schema.get("menus") or {})
    admin = list(menus.get("admin") or [])
    ensure_menu(
        admin,
        "clean_tasks",
        {
            "key": "clean_tasks",
            "label": labels.get("cleanTasksMenu", "保洁任务"),
            "superOnly": False,
        },
        before_key="orders",
    )
    menus["admin"] = admin
    schema["menus"] = menus
    return {**spec, "schema": schema}
