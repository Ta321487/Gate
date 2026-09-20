"""课时包。开题写到才挂，挂在已有私教预约上。

约课成功扣 1 节，未开始前取消退回。已上课不能退节。
只写私教预约、时间银行或选课不加这张表。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

LESSON_PACK_CAP = "lesson_pack"

_ANCHORS = ("课时包", "消课", "剩余课时")

_NEIGHBORS = frozenset({"DOM-TIMEBANK", "DOM-COURSE", "DOM-ACTIVITY"})


def _hit(text: str) -> bool:
    return any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in _ANCHORS)


def scan_lesson_pack(text: str, title: str = "") -> bool:
    return _hit(f"{title or ''}\n{text or ''}")


def merge_lesson_pack_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
    title: str = "",
) -> list[str]:
    out = list(caps or [])
    if (domain or "") != "DOM-SALON" or (domain or "") in _NEIGHBORS or "slot_reserve" not in out:
        return [c for c in out if c != LESSON_PACK_CAP]
    if LESSON_PACK_CAP in out:
        return out
    if scan_lesson_pack(proposal_text or "", title):
        out.append(LESSON_PACK_CAP)
    return out


def apply_lesson_pack_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    from app.bake.schema.menu_utils import ensure_menu

    title = str(spec.get("title") or "")
    caps = merge_lesson_pack_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text or "",
        domain=spec.get("domain"),
        title=title,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if LESSON_PACK_CAP not in caps:
        return {**spec, "schema": schema}

    schema["lessonPack"] = True
    labels = dict(schema.get("labels") or {})
    labels.setdefault("lessonPackMenu", "课时包")
    labels.setdefault("lessonUseMenu", "消课记录")
    labels.setdefault("myLessonMenu", "我的课时")
    labels.setdefault(
        "lessonHint",
        "选择课时包购买。约课成功扣 1 节，未开始前取消退回。已上课不能退节。",
    )
    schema["labels"] = labels
    menus = dict(schema.get("menus") or {})
    admin = list(menus.get("admin") or [])
    ensure_menu(
        admin,
        "lesson_packs",
        {"key": "lesson_packs", "label": "课时包", "superOnly": False},
    )
    ensure_menu(
        admin,
        "lesson_uses",
        {"key": "lesson_uses", "label": "消课记录", "superOnly": False},
    )
    menus["admin"] = admin
    user = list(menus.get("user") or [])
    ensure_menu(user, "my_lessons", {"key": "my_lessons", "label": "我的课时"})
    menus["user"] = user
    schema["menus"] = menus
    return {**spec, "schema": schema}
