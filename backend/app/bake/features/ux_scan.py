"""开题写到才挂的三项：search_assist / browse_history / gallery（无域默认；没有描述则保持原样）。"""

from __future__ import annotations

import re
from typing import Any

SEARCH_ASSIST_CAP = "search_assist"
BROWSE_HISTORY_CAP = "browse_history"
GALLERY_CAP = "gallery"

UX_CAPS = (SEARCH_ASSIST_CAP, BROWSE_HISTORY_CAP, GALLERY_CAP)

_SEARCH_SIGNALS = re.compile(
    r"搜索联想|联想搜索|自动补全|下拉联想|热搜|热门搜索|搜索推荐|搜索提示"
)
_BROWSE_SIGNALS = re.compile(
    r"浏览历史|浏览足迹|最近浏览|浏览记录|足迹功能"
)
_GALLERY_SIGNALS = re.compile(
    r"多图(?:轮播)?|图集|商品多图|详情轮播|多张图片|相册"
)


def scan_search_assist(text: str) -> bool:
    return bool(_SEARCH_SIGNALS.search(text or ""))


def scan_browse_history(text: str) -> bool:
    return bool(_BROWSE_SIGNALS.search(text or ""))


def scan_gallery(text: str) -> bool:
    return bool(_GALLERY_SIGNALS.search(text or ""))


def merge_ux_capabilities(caps: list[str], proposal_text: str = "") -> list[str]:
    """无档案能力则不挂；仅材料命中才追加（无 SHOP 默认）。"""
    out = list(caps or [])
    if "archive" not in out:
        return [c for c in out if c not in UX_CAPS]
    text = proposal_text or ""
    if scan_search_assist(text) and SEARCH_ASSIST_CAP not in out:
        out.append(SEARCH_ASSIST_CAP)
    if scan_browse_history(text) and BROWSE_HISTORY_CAP not in out:
        out.append(BROWSE_HISTORY_CAP)
    if scan_gallery(text) and GALLERY_CAP not in out:
        out.append(GALLERY_CAP)
    return out


def _ensure_menu(menus: list[dict], key: str, item: dict, *, before_key: str | None = None) -> None:
    if any(m.get("key") == key for m in menus):
        return
    if before_key:
        for i, m in enumerate(menus):
            if m.get("key") == before_key:
                menus.insert(i, item)
                return
    menus.append(item)


def attach_ux_schema(schema: dict[str, Any], caps: list[str]) -> None:
    caps = list(caps or [])
    labels = schema.setdefault("labels", {})
    menus = schema.setdefault("menus", {})
    user = menus.setdefault("user", [])
    archive = (schema.get("entities") or {}).setdefault("archive", {})

    if SEARCH_ASSIST_CAP in caps:
        labels.setdefault("searchSuggestHint", "输入名称可联想")
        # 演示热搜：无材料定制时给中性占位，管理端可改 schema / 交付 JSON
        search = schema.setdefault("search", {})
        search.setdefault("hotKeywords", ["热门推荐", "新品", "精选"])
        search["suggestEnabled"] = True

    if BROWSE_HISTORY_CAP in caps:
        _ensure_menu(
            user,
            "browse_history",
            {"key": "browse_history", "label": "浏览历史"},
            before_key="favorites",
        )
        if not any(m.get("key") == "browse_history" for m in user):
            _ensure_menu(user, "browse_history", {"key": "browse_history", "label": "浏览历史"}, before_key="profile")
        labels.setdefault("browseHistoryPageTitle", "浏览历史")
        labels.setdefault("browseHistoryPageLead", "最近看过的记录，便于回看。")
        search = schema.setdefault("search", {})
        search.setdefault("browseHistoryLimit", 20)

    if GALLERY_CAP in caps:
        archive["galleryEnabled"] = True
        labels.setdefault("galleryLabel", "图集")


def apply_ux_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    caps = merge_ux_capabilities(list(spec.get("capabilities") or []), proposal_text)
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if any(c in caps for c in UX_CAPS):
        attach_ux_schema(schema, caps)
        from app.bake.gate_contracts import merge_ux_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_ux_gate(gate, caps)
        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        mapping = {
            SEARCH_ASSIST_CAP: "搜索联想与热搜",
            BROWSE_HISTORY_CAP: "浏览历史",
            GALLERY_CAP: "商品多图",
        }
        for cap, name in mapping.items():
            if cap in caps and name not in names:
                features.append({"name": name, "status": "module"})
        spec["features"] = features
    spec["schema"] = schema
    return spec
