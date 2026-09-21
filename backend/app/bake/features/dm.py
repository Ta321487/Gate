"""一对一私信（dm）：短轮询会话，非站内信、非留言板、非 WebSocket。

默认挂 DOM-DATING；论坛等域开题写「私信/私聊」等再扫入。
商城/点餐：开题写「客服」即挂（单店=平台客服选人；写明商家/多店才收窄为店铺客服）。
纯「智能客服」走 AI 岛，不由此挂私信。
"""

from __future__ import annotations

import re
from typing import Any

from app.bake.proposal_lexicon import pattern_mentioned

DM_CAP = "dm"

DM_PEER_ALL = "all"
DM_PEER_MERCHANT = "merchant"

_TRADE_CS_DOMAINS = frozenset({"DOM-SHOP", "DOM-FOOD"})

_DM_SIGNALS = re.compile(
    r"(?:实时|即时)?私信|一对一(?:私信|聊天|私聊)|私聊|在线聊天|站内聊天|private\s*chat|\bDM\b",
    re.IGNORECASE,
)

# 留言模块里写「与管理员/用户沟通」：交易壳要一对一会话，不只留言板回复
_ADMIN_CHAT_SIGNALS = re.compile(
    r"与管理员沟通|和管理员沟通|向管理员沟通|与用户沟通|和用户沟通"
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

# 去掉 AI 岛说法后仍含「客服」→ 交易壳挂私信客服（对齐 opening_align 的「客服」）
_AI_CS_PHRASES = re.compile(
    r"智能客服|AI(?:智能)?客服|大模型客服|机器人客服",
    re.IGNORECASE,
)

_USER_PEER_CHAT = re.compile(
    r"用户(?:之间|互)?(?:私信|私聊|互聊)|站内私信|会员互聊",
)

_DEFAULT_DOMAINS = frozenset({"DOM-DATING"})

_DM_OOS_NAMES = frozenset({"实时私信", "即时私信", "一对一私信", "私信"})


def scan_dm(text: str) -> bool:
    return pattern_mentioned(text or "", _DM_SIGNALS, ignore_contrast=True)


def scan_dm_merchant_peers(text: str) -> bool:
    return pattern_mentioned(text or "", _DM_MERCHANT_PEER_SIGNALS, ignore_contrast=True)


def scan_admin_dialogue(text: str) -> bool:
    """留言里点名和总管或用户沟通，交易壳挂一对一会话。"""
    return pattern_mentioned(text or "", _ADMIN_CHAT_SIGNALS, ignore_contrast=True)


def scan_trade_customer_service(text: str) -> bool:
    """交易壳开题是否点名人工/平台客服（不含纯智能客服）。"""
    raw = text or ""
    if "客服" not in raw:
        return False
    stripped = _AI_CS_PHRASES.sub("", raw)
    return "客服" in stripped


def _user_peer_chat_mentioned(text: str) -> bool:
    return bool(_USER_PEER_CHAT.search(text or ""))


def resolve_dm_peer_mode(
    proposal_text: str = "",
    *,
    domain: str | None = None,
) -> str:
    if scan_dm_merchant_peers(proposal_text):
        return DM_PEER_MERCHANT
    # 多店商城：开题写「客服」且未写用户互聊/站内私信 → 默认店铺客服
    if (domain or "") == "DOM-SHOP":
        from app.bake.scene_scan import scan_shop_marketplace

        blob = proposal_text or ""
        if scan_shop_marketplace("", blob) or scan_shop_marketplace(blob, blob):
            if scan_trade_customer_service(blob) and not _user_peer_chat_mentioned(blob):
                return DM_PEER_MERCHANT
    return DM_PEER_ALL


def want_dm_cs_labels(
    proposal_text: str = "",
    *,
    domain: str | None = None,
    peer_mode: str = DM_PEER_ALL,
) -> bool:
    """菜单/页眉用「客服」而非「私信」：店铺客服，或交易壳点名客服且非用户互聊。"""
    if peer_mode == DM_PEER_MERCHANT:
        return True
    if (domain or "") in _TRADE_CS_DOMAINS and scan_trade_customer_service(proposal_text):
        return not _user_peer_chat_mentioned(proposal_text)
    if (domain or "") in _TRADE_CS_DOMAINS and scan_admin_dialogue(proposal_text):
        return not _user_peer_chat_mentioned(proposal_text)
    return False


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
    if domain in _TRADE_CS_DOMAINS:
        from app.bake.scene_scan import scan_shop_marketplace

        if domain == "DOM-SHOP" and scan_shop_marketplace(proposal_text, proposal_text):
            return True
        if scan_dm_merchant_peers(proposal_text):
            return True
        if scan_trade_customer_service(proposal_text):
            return True
        if scan_admin_dialogue(proposal_text):
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


def attach_dm_menus(
    schema: dict[str, Any],
    *,
    peer_mode: str = DM_PEER_ALL,
    cs_labels: bool = False,
) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    user = menus.setdefault("user", [])
    admin = menus.setdefault("admin", [])
    merchant = peer_mode == DM_PEER_MERCHANT
    use_cs = merchant or cs_labels
    item = {"key": "dm", "label": "客服" if use_cs else "私信"}
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
            if isinstance(m, dict) and m.get("key") == "dm" and use_cs:
                m["label"] = "客服"
    # 管理端：办理岗也要有入口（店铺客服 / 平台客服 / 红娘 / 版主私信等）
    admin_item = {
        "key": "dm",
        "label": "客服" if use_cs else "私信",
        "superOnly": False,
    }
    if not any(isinstance(m, dict) and m.get("key") == "dm" for m in admin):
        placed = False
        for before in ("guestbook", "orders", "order_reviews", "content", "users"):
            if any(isinstance(m, dict) and m.get("key") == before for m in admin):
                ensure_menu(admin, "dm", admin_item, before_key=before)
                placed = True
                break
        if not placed:
            admin.append(admin_item)
    else:
        for m in admin:
            if isinstance(m, dict) and m.get("key") == "dm":
                m["label"] = "客服" if use_cs else "私信"
                m["superOnly"] = False
    labels = schema.setdefault("labels", {})
    if merchant:
        labels["dmPageTitle"] = "客服"
        labels["dmPageLead"] = "与店铺商家一对一沟通，打开会话后自动刷新新消息。"
        labels["dmNewTitle"] = "联系商家客服"
        labels["dmPeerPlaceholder"] = "选择店铺商家"
        labels["dmEmptyPeers"] = "暂无会话，点「新建」选店铺商家。"
        labels["dmEmptyChat"] = "选择左侧会话，或新建联系商家。"
        labels["dmMerchantPageLead"] = "回复买家咨询，打开会话后自动刷新新消息。"
        labels["dmMerchantNewTitle"] = "联系买家"
        labels["dmMerchantPeerPlaceholder"] = "选择买家账号"
        labels["dmMerchantEmptyPeers"] = "暂无会话，买家发起咨询后会出现在这里；也可点「新建」选买家。"
        labels["dmMerchantEmptyChat"] = "选择左侧会话，或新建联系买家。"
    elif use_cs:
        labels["dmPageTitle"] = "客服"
        labels["dmPageLead"] = "与平台客服一对一沟通，打开会话后自动刷新新消息。"
        labels["dmNewTitle"] = "联系客服"
        labels["dmPeerPlaceholder"] = "选择客服账号"
        labels["dmEmptyPeers"] = "暂无会话，点「新建」选客服开聊。"
        labels["dmEmptyChat"] = "选择左侧会话，或新建联系客服。"
        labels["dmMerchantPageLead"] = "回复用户咨询，打开会话后自动刷新新消息。"
        labels["dmMerchantNewTitle"] = "联系用户"
        labels["dmMerchantPeerPlaceholder"] = "选择用户账号"
        labels["dmMerchantEmptyPeers"] = "暂无会话，用户发起咨询后会出现在这里；也可点「新建」选用户。"
        labels["dmMerchantEmptyChat"] = "选择左侧会话，或新建联系用户。"
    else:
        labels["dmPageTitle"] = "私信"
        labels["dmPageLead"] = "与其他用户一对一沟通，打开会话后自动刷新新消息。"
        labels["dmNewTitle"] = "新建私信"
        labels["dmPeerPlaceholder"] = "选择对方账号"
        labels["dmEmptyPeers"] = "暂无会话，点「新建」选人开聊。"
        labels["dmEmptyChat"] = "选择左侧会话，或新建私信。"
        labels["dmMerchantPageLead"] = "与用户一对一沟通，打开会话后自动刷新新消息。"
        labels["dmMerchantNewTitle"] = "联系用户"
        labels["dmMerchantPeerPlaceholder"] = "选择用户账号"
        labels["dmMerchantEmptyPeers"] = "暂无会话，点「新建」选用户开聊。"
        labels["dmMerchantEmptyChat"] = "选择左侧会话，或新建联系用户。"
    ents = schema.setdefault("entities", {})
    if "dm" not in ents:
        ents["dm"] = {
            "key": "dm",
            "label": "客服" if use_cs else "私信",
            "labelPlural": "客服" if use_cs else "私信",
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
    cs_labels = want_dm_cs_labels(
        proposal_text, domain=domain, peer_mode=peer_mode
    )

    if DM_CAP in caps:
        # 学生包只认业务布尔：店铺客服选人（多店）；单店客服仍 peer=all，仅文案为客服
        schema["dmShopCs"] = peer_mode == DM_PEER_MERCHANT
        schema.pop("dmPeerMode", None)
        attach_dm_menus(schema, peer_mode=peer_mode, cs_labels=cs_labels)
        from app.bake.gate_contracts import merge_dm_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_dm_gate(gate, caps)

        _strip_dm_oos(spec)

        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if peer_mode == DM_PEER_MERCHANT:
            feat_name = "商家客服"
        elif cs_labels:
            feat_name = "平台客服"
        else:
            feat_name = "一对一私信"
        if (
            feat_name not in names
            and "一对一私信" not in names
            and "商家客服" not in names
            and "商家客服私信" not in names
            and "平台客服" not in names
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
