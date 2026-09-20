"""约拍。开题写到才挂，挂在已有时段预约上。

摄影师是可预约资源，同一人同一时段靠现有占用拒绝。不是影院选座、影视点播或场地座位。
只写摄影欣赏不开。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

SHOOT_CAP = "shoot"

_ANCHORS = ("约拍", "摄影师", "交片")

_NEIGHBORS = frozenset({"DOM-CINEMA", "DOM-MEDIA", "DOM-MEETING", "DOM-EQUIP"})


def _hit(text: str) -> bool:
    if keyword_mentioned(text, "摄影欣赏", ignore_contrast=True) and not any(
        keyword_mentioned(text, kw, ignore_contrast=True) for kw in ("约拍", "摄影师", "交片")
    ):
        return False
    return any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in _ANCHORS)


def scan_shoot(text: str, title: str = "") -> bool:
    return _hit(f"{title or ''}\n{text or ''}")


def merge_shoot_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
    title: str = "",
) -> list[str]:
    out = list(caps or [])
    if (domain or "") in _NEIGHBORS or "slot_reserve" not in out:
        return [c for c in out if c != SHOOT_CAP]
    if SHOOT_CAP in out:
        return out
    if scan_shoot(proposal_text or "", title):
        out.append(SHOOT_CAP)
    return out


def apply_shoot_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    from app.bake.schema.menu_utils import ensure_menu

    title = str(spec.get("title") or "")
    caps = merge_shoot_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text or "",
        domain=spec.get("domain"),
        title=title,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if SHOOT_CAP not in caps:
        return {**spec, "schema": schema}

    schema["shoot"] = True
    labels = dict(schema.get("labels") or {})
    labels.setdefault("shootBundleMenu", "约拍套餐")
    labels.setdefault("shootFileMenu", "交片")
    labels.setdefault("myShootMenu", "我的成片")
    labels.setdefault("shootHint", "选择摄影师和套餐。交片后才能查看文件。同一摄影师同一时段不能约两次。")
    schema["labels"] = labels
    menus = dict(schema.get("menus") or {})
    admin = list(menus.get("admin") or [])
    ensure_menu(
        admin,
        "shoot_bundles",
        {"key": "shoot_bundles", "label": "约拍套餐", "superOnly": False},
    )
    ensure_menu(
        admin,
        "shoot_files",
        {"key": "shoot_files", "label": "交片", "superOnly": False},
    )
    menus["admin"] = admin
    user = list(menus.get("user") or [])
    ensure_menu(user, "my_shots", {"key": "my_shots", "label": "我的成片"})
    menus["user"] = user
    schema["menus"] = menus
    return {**spec, "schema": schema}
