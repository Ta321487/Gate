"""门户留言板（guestbook）：用户发表、管理端列表/删除/简短回复。

与公告（content/sys_notice）、站内信（sys_message）、论坛跟帖（ticket reply）分离。
默认挂交易壳（SHOP/FOOD/GENERIC·TRADE）；开题写「留言」时可扫入其它域（论坛除外）。
"""

from __future__ import annotations

import re
from typing import Any

GUESTBOOK_CAP = "guestbook"

_GUESTBOOK_SIGNALS = re.compile(
    r"留言(?:功能|管理|板|反馈)?|访客留言|在线留言|guestbook|留言板"
)

# 论坛已有跟帖，勿再叠留言表（表预算也顶格）
_SKIP_DOMAINS = frozenset({"DOM-FORUM"})

# 交易门户默认开
_DEFAULT_DOMAINS = frozenset({"DOM-SHOP", "DOM-FOOD"})


def scan_guestbook(text: str) -> bool:
    return bool(_GUESTBOOK_SIGNALS.search(text or ""))


def guestbook_wanted(
    *,
    domain: str | None,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
    capabilities: list[str] | None = None,
    proposal_text: str = "",
) -> bool:
    """是否应启用留言：显式能力 / 交易默认 / 开题扫描。"""
    domain = domain or ""
    if domain in _SKIP_DOMAINS:
        return False
    caps = list(capabilities or [])
    if GUESTBOOK_CAP in caps:
        return True
    if domain in _DEFAULT_DOMAINS:
        return True
    from app.bake.archetype_shells import normalize_archetypes, path_flags

    arches = normalize_archetypes(archetypes, primary=archetype)
    _flow, need_trade, _reserve = path_flags(arches)
    if domain == "DOM-GENERIC" and need_trade:
        return True
    return scan_guestbook(proposal_text)


def merge_guestbook_capabilities(
    caps: list[str],
    proposal_text: str = "",
    *,
    domain: str | None = None,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
    force: bool = False,
) -> list[str]:
    out = list(caps or [])
    if domain in _SKIP_DOMAINS:
        return [c for c in out if c != GUESTBOOK_CAP]
    want = force or guestbook_wanted(
        domain=domain,
        archetype=archetype,
        archetypes=archetypes,
        capabilities=out,
        proposal_text=proposal_text,
    )
    if want and GUESTBOOK_CAP not in out:
        out.append(GUESTBOOK_CAP)
    return out


def attach_guestbook_menus(schema: dict[str, Any]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    admin = menus.setdefault("admin", [])
    user = menus.setdefault("user", [])
    ensure_menu(
        admin,
        "guestbook",
        {"key": "guestbook", "label": "留言管理", "superOnly": True},
        before_key="content",
    )
    ensure_menu(
        user,
        "guestbook",
        {"key": "guestbook", "label": "留言"},
        before_key="content",
    )
    if not any(m.get("key") == "guestbook" for m in user):
        ensure_menu(
            user,
            "guestbook",
            {"key": "guestbook", "label": "留言"},
            before_key="profile",
        )
    labels = schema.setdefault("labels", {})
    labels.setdefault("guestbookPageTitle", "留言板")
    labels.setdefault(
        "guestbookPageLead",
        "欢迎留下建议或咨询；管理员可简短回复。",
    )
    ents = schema.setdefault("entities", {})
    if "guestbook" not in ents:
        ents["guestbook"] = {
            "key": "guestbook",
            "label": "留言",
            "labelPlural": "留言",
        }


def apply_guestbook_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    """合并 guestbook 能力、菜单、实体列表与 gate。"""
    domain = spec.get("domain")
    archetype = spec.get("archetype")
    arches = list(spec.get("archetypes") or ([archetype] if archetype else []))
    caps = merge_guestbook_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text,
        domain=domain,
        archetype=archetype,
        archetypes=arches,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps

    if GUESTBOOK_CAP in caps:
        attach_guestbook_menus(schema)
        from app.bake.gate_contracts import merge_guestbook_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_guestbook_gate(gate, caps)

        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "访客留言" not in names:
            features.append({"name": "访客留言", "status": "module"})
        spec["features"] = features

        ents = list(spec.get("entities") or [])
        if "Guestbook" not in ents:
            if "Notice" in ents:
                ents.insert(ents.index("Notice"), "Guestbook")
            else:
                ents.append("Guestbook")
            spec["entities"] = ents

    spec["schema"] = schema
    return spec
