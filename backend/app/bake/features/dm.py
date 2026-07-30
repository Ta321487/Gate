"""一对一私信（dm）：用户↔用户短轮询私信，非站内信、非留言板、非 WebSocket。

默认挂 DOM-DATING；论坛等域开题写「私信/私聊」等再扫入（论坛样例常把实时私信当对比不做）。
"""

from __future__ import annotations

import re
from typing import Any

from app.bake.proposal_lexicon import pattern_mentioned

DM_CAP = "dm"

# 开题常见写法；「WebSocket / 环信」等真实时通道仍走过重扫词，不进本能力
_DM_SIGNALS = re.compile(
    r"(?:实时|即时)?私信|一对一(?:私信|聊天|私聊)|私聊|在线聊天|站内聊天|private\s*chat|\bDM\b",
    re.IGNORECASE,
)

_DEFAULT_DOMAINS = frozenset({"DOM-DATING"})

# 能力落地后从「本期不做」里摘掉的壳默认名
_DM_OOS_NAMES = frozenset({"实时私信", "即时私信", "一对一私信", "私信"})


def scan_dm(text: str) -> bool:
    return pattern_mentioned(text or "", _DM_SIGNALS, ignore_contrast=True)


def dm_wanted(
    *,
    domain: str | None,
    capabilities: list[str] | None = None,
    proposal_text: str = "",
) -> bool:
    """是否应启用私信：显式能力 / 域默认 / 开题扫描。"""
    caps = list(capabilities or [])
    if DM_CAP in caps:
        return True
    domain = domain or ""
    if domain in _DEFAULT_DOMAINS:
        return True
    return scan_dm(proposal_text)


def merge_dm_capabilities(
    caps: list[str],
    proposal_text: str = "",
    *,
    domain: str | None = None,
    force: bool = False,
) -> list[str]:
    out = list(caps or [])
    want = force or dm_wanted(
        domain=domain,
        capabilities=out,
        proposal_text=proposal_text,
    )
    if want and DM_CAP not in out:
        out.append(DM_CAP)
    return out


def _strip_dm_oos(spec: dict[str, Any]) -> None:
    oos = [x for x in (spec.get("out_of_mvp") or []) if str(x) not in _DM_OOS_NAMES]
    spec["out_of_mvp"] = oos
    keep = []
    for f in spec.get("features") or []:
        if not isinstance(f, dict):
            keep.append(f)
            continue
        if f.get("status") == "out_of_mvp" and str(f.get("name") or "").split("（")[0] in _DM_OOS_NAMES:
            continue
        keep.append(f)
    spec["features"] = keep


def attach_dm_menus(schema: dict[str, Any]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    user = menus.setdefault("user", [])
    item = {"key": "dm", "label": "私信"}
    if not any(m.get("key") == "dm" for m in user):
        placed = False
        for before in ("messages", "profile", "content"):
            if any(m.get("key") == before for m in user):
                ensure_menu(user, "dm", item, before_key=before)
                placed = True
                break
        if not placed:
            user.append(item)
    labels = schema.setdefault("labels", {})
    labels.setdefault("dmPageTitle", "私信")
    labels.setdefault(
        "dmPageLead",
        "与其他用户一对一沟通；打开会话后自动刷新新消息（短轮询，非 WebSocket）。",
    )
    ents = schema.setdefault("entities", {})
    if "dm" not in ents:
        ents["dm"] = {"key": "dm", "label": "私信", "labelPlural": "私信"}


def apply_dm_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    """合并 dm 能力、菜单、实体列表与 gate；落地后摘掉相关 out_of_mvp。"""
    domain = spec.get("domain")
    caps = merge_dm_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text,
        domain=domain,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps

    if DM_CAP in caps:
        attach_dm_menus(schema)
        from app.bake.gate_contracts import merge_dm_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_dm_gate(gate, caps)

        _strip_dm_oos(spec)

        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "一对一私信" not in names:
            features.append({"name": "一对一私信", "status": "module"})
        spec["features"] = features

        ents = list(spec.get("entities") or [])
        if "Dm" not in ents:
            if "Notice" in ents:
                ents.insert(ents.index("Notice"), "Dm")
            else:
                ents.append("Dm")
            spec["entities"] = ents

    spec["schema"] = schema
    return spec
