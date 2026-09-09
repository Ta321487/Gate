"""一对一私信（dm）：短轮询会话，非站内信、非留言板、非 WebSocket。

默认挂 DOM-DATING；论坛等域开题写「私信/私聊」等再扫入。
商城：仅当开题写明「与商家/店铺客服」时，学生包按店铺客服选人（买家↔商家）；
未写明则不擅自收窄。
"""

from __future__ import annotations

import re
from typing import Any

from app.bake.proposal_lexicon import pattern_mentioned

DM_CAP = "dm"

DM_PEER_ALL = "all"
DM_PEER_MERCHANT = "merchant"

_DM_SIGNALS = re.compile(
    r"(?:实时|即时)?私信|一对一(?:私信|聊天|私聊)|私聊|在线聊天|站内聊天|private\s*chat|\bDM\b",
    re.IGNORECASE,
)

_DM_MERCHANT_PEER_SIGNALS = re.compile(
    r"(?:与|跟|向)商家(?:在线)?(?:沟通|咨询|联系|聊天|私信)|"
    r"商家(?:在线)?(?:客服|沟通|咨询)|"
    r"店铺客服|店家客服|商家客服|"
    r"客服(?:模块|功能)?[（(]?[^）)\n]{0,24}商家|"
    r"联系(?:店铺|商家|店家)|"
    r"在线(?:咨询|沟通)商家",
    re.IGNORECASE,
)

_DEFAULT_DOMAINS = frozenset({"DOM-DATING"})

_DM_OOS_NAMES = frozenset({"实时私信", "即时私信", "一对一私信", "私信"})


def scan_dm(text: str) -> bool:
    return pattern_mentioned(text or "", _DM_SIGNALS, ignore_contrast=True)


def scan_dm_merchant_peers(text: str) -> bool:
    return pattern_mentioned(text or "", _DM_MERCHANT_PEER_SIGNALS, ignore_contrast=True)


def resolve_dm_peer_mode(
    proposal_text: str = "",
    *,
    domain: str | None = None,
) -> str:
    if scan_dm_merchant_peers(proposal_text):
        return DM_PEER_MERCHANT
    return DM_PEER_ALL


def dm_wanted(
    *,
    domain: str | None,
    capabilities: list[str] | None = None,
    proposal_text: str = "",
) -> bool:
    caps = list(capabilities or [])
    if DM_CAP in caps:
        return True
    domain = domain or ""
    if domain in _DEFAULT_DOMAINS:
        return True
    if domain == "DOM-SHOP":
        from app.bake.scene_scan import scan_shop_marketplace

        if scan_shop_marketplace(proposal_text, proposal_text):
            return True
        if scan_dm_merchant_peers(proposal_text):
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


def attach_dm_menus(schema: dict[str, Any], *, peer_mode: str = DM_PEER_ALL) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    user = menus.setdefault("user", [])
    merchant = peer_mode == DM_PEER_MERCHANT
    item = {"key": "dm", "label": "客服" if merchant else "私信"}
    if not any(m.get("key") == "dm" for m in user):
        placed = False
        for before in ("messages", "profile", "content"):
            if any(m.get("key") == before for m in user):
                ensure_menu(user, "dm", item, before_key=before)
                placed = True
                break
        if not placed:
            user.append(item)
    else:
        for m in user:
            if isinstance(m, dict) and m.get("key") == "dm" and merchant:
                m["label"] = "客服"
    labels = schema.setdefault("labels", {})
    if merchant:
        labels["dmPageTitle"] = "客服"
        labels["dmPageLead"] = "与店铺商家一对一沟通，打开会话后自动刷新新消息。"
        labels["dmNewTitle"] = "联系商家客服"
        labels["dmPeerPlaceholder"] = "选择店铺商家"
        labels["dmEmptyPeers"] = "暂无会话，点「新建」选店铺商家。"
        labels["dmEmptyChat"] = "选择左侧会话，或新建联系商家。"
    else:
        labels["dmPageTitle"] = "私信"
        labels["dmPageLead"] = "与其他用户一对一沟通，打开会话后自动刷新新消息。"
        labels["dmNewTitle"] = "新建私信"
        labels["dmPeerPlaceholder"] = "选择对方账号"
        labels["dmEmptyPeers"] = "暂无会话，点「新建」选人开聊。"
        labels["dmEmptyChat"] = "选择左侧会话，或新建私信。"
    ents = schema.setdefault("entities", {})
    if "dm" not in ents:
        ents["dm"] = {
            "key": "dm",
            "label": "客服" if merchant else "私信",
            "labelPlural": "客服" if merchant else "私信",
        }


def apply_dm_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    domain = spec.get("domain")
    caps = merge_dm_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text,
        domain=domain,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    peer_mode = resolve_dm_peer_mode(proposal_text, domain=domain)

    if DM_CAP in caps:
        # 学生包只认业务布尔：店铺客服选人
        schema["dmShopCs"] = peer_mode == DM_PEER_MERCHANT
        schema.pop("dmPeerMode", None)
        attach_dm_menus(schema, peer_mode=peer_mode)
        from app.bake.gate_contracts import merge_dm_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_dm_gate(gate, caps)

        _strip_dm_oos(spec)

        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        feat_name = "商家客服" if peer_mode == DM_PEER_MERCHANT else "一对一私信"
        if (
            feat_name not in names
            and "一对一私信" not in names
            and "商家客服" not in names
            and "商家客服私信" not in names
        ):
            features.append({"name": feat_name, "status": "module"})
        spec["features"] = features

        ents = list(spec.get("entities") or [])
        if "Dm" not in ents:
            if "Notice" in ents:
                ents.insert(ents.index("Notice"), "Dm")
            else:
                ents.append("Dm")
            spec["entities"] = ents
    else:
        schema.pop("dmShopCs", None)
        schema.pop("dmPeerMode", None)

    spec["schema"] = schema
    return spec
