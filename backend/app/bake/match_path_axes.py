"""匹配确认：身份场景 + 主路径入口（单一真源）。

扫描仍走 ``scene_scan`` 既有 hint；本模块只：
1. 列出可手改选项（随领域）
2. 汇总推荐 / 当前出包
3. 在 bake / build_spec 时注入覆盖上下文（不复制扫词）

禁止在本文件重写 CAMPUS_HINTS / EVENT_SELF_REPORT_HINTS 等。
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from app.bake import scene_scan as _scan

# 运营台身份轴（常见三档；扫描若给出其它档则并入选项）
_BASE_SCENE_OPTIONS: tuple[dict[str, str], ...] = (
    {"id": "campus", "label": "校园"},
    {"id": "enterprise", "label": "企业"},
    {"id": "community", "label": "社区"},
)

_EXTRA_SCENE_LABELS: dict[str, str] = {
    "commercial": "商业/消费",
    "institution": "机构照护",
    "adopt": "领养",
    "default": "域默认",
}

# 仅对「同域入口分叉」已有 scan 函数的域暴露入口轴（禁止另写判定）
ENTRY_OPTIONS_BY_DOMAIN: dict[str, tuple[dict[str, str], ...]] = {
    "DOM-EVENT": (
        {"id": "caseload", "label": "对象台账作业（网格/班主任录入）"},
        {"id": "self_report", "label": "本人打卡填单（晨午检/自报）"},
    ),
    "DOM-INTERN": (
        {"id": "select_post", "label": "选已建档岗交周报"},
        {"id": "post_bound", "label": "资料绑定岗位后填报"},
    ),
    "DOM-BED": (
        {"id": "select_bed", "label": "浏览床位选房"},
        {"id": "transfer", "label": "调宿/退宿填单优先"},
    ),
}


def scene_options_for(domain: str, recommended: str) -> list[dict[str, str]]:
    opts = [dict(x) for x in _BASE_SCENE_OPTIONS]
    ids = {x["id"] for x in opts}
    rec = (recommended or "").strip()
    if rec and rec not in ids:
        opts.append(
            {
                "id": rec,
                "label": _EXTRA_SCENE_LABELS.get(rec, rec),
            }
        )
    return opts


def entry_options_for(domain: str) -> list[dict[str, str]]:
    return [dict(x) for x in ENTRY_OPTIONS_BY_DOMAIN.get(domain or "", ())]


def recommend_scene(domain: str, title: str = "", proposal_text: str = "") -> str:
    """开题扫描推荐场景（忽略运营台覆盖）。"""
    return _scan.scene_for(
        domain, title, proposal_text, respect_override=False
    )


def recommend_entry(domain: str, title: str = "", proposal_text: str = "") -> str:
    """开题扫描推荐入口；无入口轴的域返回空串。"""
    if domain == "DOM-EVENT":
        return (
            "self_report"
            if _scan.event_self_report(
                title, proposal_text, respect_override=False
            )
            else "caseload"
        )
    if domain == "DOM-INTERN":
        return (
            "post_bound"
            if _scan.intern_post_bound(
                title, proposal_text, respect_override=False
            )
            else "select_post"
        )
    if domain == "DOM-BED":
        return (
            "transfer"
            if _scan.bed_transfer_primary(
                title, proposal_text, respect_override=False
            )
            else "select_bed"
        )
    return ""


def entry_is_weak(domain: str, recommended_entry: str) -> bool:
    """默认档且存在分叉 → 弱依据（确认前须勾主路径）。"""
    if domain == "DOM-EVENT":
        return recommended_entry == "caseload"
    if domain == "DOM-INTERN":
        return recommended_entry == "select_post"
    if domain == "DOM-BED":
        return recommended_entry == "select_bed"
    return False


def label_of(options: list[dict[str, str]], value: str) -> str:
    for o in options:
        if o.get("id") == value:
            return str(o.get("label") or value)
    return value or ""


def normalize_scene(value: str | None, allowed: list[dict[str, str]]) -> str | None:
    if value is None:
        return None
    v = str(value).strip()
    ids = {str(o.get("id")) for o in allowed}
    if v not in ids:
        raise ValueError(f"未知身份场景：{v}")
    return v


def normalize_entry(value: str | None, allowed: list[dict[str, str]]) -> str | None:
    if value is None:
        return None
    if not allowed:
        raise ValueError("当前领域无主路径入口可选")
    v = str(value).strip()
    ids = {str(o.get("id")) for o in allowed}
    if v not in ids:
        raise ValueError(f"未知主路径入口：{v}")
    return v


def resolve_match_path(
    domain: str,
    title: str = "",
    proposal_text: str = "",
    *,
    scene: str | None = None,
    entry: str | None = None,
    prev: dict[str, Any] | None = None,
    clear_overrides: bool = False,
) -> dict[str, Any]:
    """汇总推荐与当前出包。

    ``scene`` / ``entry`` 仅在本次请求显式传入时写入 overrides；
    否则沿用 prev.overrides（恢复推荐时 clear_overrides）。
    """
    rec_scene = recommend_scene(domain, title, proposal_text)
    scene_opts = scene_options_for(domain, rec_scene)
    entry_opts = entry_options_for(domain)
    rec_entry = recommend_entry(domain, title, proposal_text) if entry_opts else ""

    prev = prev if isinstance(prev, dict) else {}
    overrides: dict[str, Any] = {}
    if not clear_overrides:
        raw_ov = prev.get("overrides")
        if isinstance(raw_ov, dict):
            overrides = {
                k: v
                for k, v in raw_ov.items()
                if k in {"scene", "entry"} and v not in (None, "")
            }

    if scene is not None:
        overrides["scene"] = normalize_scene(str(scene), scene_opts)
    if entry is not None:
        if entry_opts:
            overrides["entry"] = normalize_entry(str(entry), entry_opts)
        else:
            overrides.pop("entry", None)

    # 换领域后入口 override 可能非法
    if "entry" in overrides and entry_opts:
        try:
            overrides["entry"] = normalize_entry(str(overrides["entry"]), entry_opts)
        except ValueError:
            overrides.pop("entry", None)
    elif "entry" in overrides and not entry_opts:
        overrides.pop("entry", None)

    if "scene" in overrides:
        try:
            overrides["scene"] = normalize_scene(str(overrides["scene"]), scene_opts)
        except ValueError:
            overrides.pop("scene", None)

    out_scene = str(overrides.get("scene") or rec_scene)
    out_entry = str(overrides.get("entry") or rec_entry) if entry_opts else ""

    weak = bool(entry_opts) and entry_is_weak(domain, rec_entry)
    manual = bool(overrides)
    # 弱依据且未手改 → 确认前必须勾「主路径已核对」
    needs_ack = weak and not manual

    return {
        "recommended_scene": rec_scene,
        "recommended_entry": rec_entry,
        "scene": out_scene,
        "entry": out_entry,
        "overrides": overrides,
        "scene_options": scene_opts,
        "entry_options": entry_opts,
        "entry_weak": weak,
        "needs_path_ack": needs_ack,
        "scene_label": label_of(scene_opts, out_scene),
        "entry_label": label_of(entry_opts, out_entry) if entry_opts else "",
        "recommended_scene_label": label_of(scene_opts, rec_scene),
        "recommended_entry_label": label_of(entry_opts, rec_entry)
        if entry_opts
        else "",
        "deviant": bool(
            out_scene != rec_scene
            or (entry_opts and out_entry and out_entry != rec_entry)
        ),
    }


@contextmanager
def match_path_override_scope(
    domain: str,
    scene: str | None = None,
    entry: str | None = None,
) -> Iterator[None]:
    """bake / build_spec 期间让 scene_for 与入口 bool 读运营台选择。"""
    token = _scan.push_path_override(
        domain=domain or "",
        scene=(scene or "").strip() or None,
        entry=(entry or "").strip() or None,
    )
    try:
        yield
    finally:
        _scan.reset_path_override(token)
