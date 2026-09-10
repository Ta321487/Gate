"""收藏夹：user_favorite 一表。

- 交易域（SHOP/FOOD 默认；其它 order_lines 开题写到才挂）：收藏后可再加购
- 内容流（MEDIA/MUSIC/BLOG）：即时收藏，不走单据/审核

E-03 同文件扩展（禁止旁挂）：
- post_like：帖/档案点赞（开题扫词）
- content_report：内容/交友举报处置（开题扫词）
"""

from __future__ import annotations

import re
from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned, pattern_mentioned

FAVORITES_CAP = "favorites"
POST_LIKE_CAP = "post_like"
CONTENT_REPORT_CAP = "content_report"

_FAVORITES_SIGNALS = re.compile(
    r"收藏夹|我的收藏|商品收藏|加入收藏|收藏功能|wishlist|favorite"
)

_LIKE_TERMS = ("点赞", "点个赞", "帖子点赞", "一键点赞", "点赞功能")
_REPORT_TERMS = (
    "举报",
    "投诉帖",
    "不良信息举报",
    "用户举报",
    "举报功能",
    "举报违规",
)

_DEFAULT_TRADE_DOMAINS = frozenset({"DOM-SHOP", "DOM-FOOD"})
# 内容流默认即时收藏；不含 FORUM（回帖仍走 ticket 审核）
_CONTENT_FAVORITE_DOMAINS = frozenset({"DOM-MEDIA", "DOM-MUSIC", "DOM-BLOG"})
# 资料型：开题写「收藏」才挂（婚恋心仪对象等），默认不挂
_PROFILE_SCAN_FAVORITE_DOMAINS = frozenset({"DOM-DATING"})

# 点赞：论坛/博客/媒资（写到才挂）
_LIKE_DOMAINS = frozenset({"DOM-FORUM", "DOM-BLOG", "DOM-MEDIA", "DOM-MUSIC"})
# 举报：论坛/交友/博客可挂；论坛行业默认
_REPORT_DOMAINS = frozenset({"DOM-FORUM", "DOM-DATING", "DOM-BLOG"})
_REPORT_DEFAULT_DOMAINS = frozenset({"DOM-FORUM"})


def scan_favorites(text: str) -> bool:
    return pattern_mentioned(text or "", _FAVORITES_SIGNALS, ignore_contrast=True)


def scan_post_like(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _LIKE_TERMS)


def scan_content_report(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _REPORT_TERMS)


def favorites_wanted(
    *,
    domain: str | None,
    capabilities: list[str] | None = None,
    proposal_text: str = "",
) -> bool:
    caps = list(capabilities or [])
    if FAVORITES_CAP in caps:
        return True
    domain = domain or ""
    # 未显式传 caps 时，用域默认能力判断
    if not caps and domain:
        from app.bake.domains import DOMAIN_CAPABILITIES

        caps = list(DOMAIN_CAPABILITIES.get(domain) or [])
    if domain in _CONTENT_FAVORITE_DOMAINS:
        return True
    if domain in _PROFILE_SCAN_FAVORITE_DOMAINS:
        return scan_favorites(proposal_text)
    if "order_lines" not in caps:
        return False
    if domain in _DEFAULT_TRADE_DOMAINS:
        return True
    return scan_favorites(proposal_text)


def merge_favorites_capabilities(
    caps: list[str],
    proposal_text: str = "",
    *,
    domain: str | None = None,
    force: bool = False,
) -> list[str]:
    out = list(caps or [])
    domain = domain or ""
    # 非交易且非内容/资料扫描收藏域：剥掉误带的 favorites
    if (
        "order_lines" not in out
        and domain not in _CONTENT_FAVORITE_DOMAINS
        and domain not in _PROFILE_SCAN_FAVORITE_DOMAINS
    ):
        return [c for c in out if c != FAVORITES_CAP]
    want = force or favorites_wanted(
        domain=domain, capabilities=out, proposal_text=proposal_text
    )
    if want and FAVORITES_CAP not in out:
        out.append(FAVORITES_CAP)
    return out


def merge_post_like_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
) -> list[str]:
    out = list(caps or [])
    if POST_LIKE_CAP in out:
        return out
    if (domain or "") not in _LIKE_DOMAINS:
        return out
    if not scan_post_like(proposal_text or ""):
        return out
    if "archive" not in out:
        return out
    out.append(POST_LIKE_CAP)
    return out


def merge_content_report_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
) -> list[str]:
    out = list(caps or [])
    if CONTENT_REPORT_CAP in out:
        return out
    if (domain or "") not in _REPORT_DOMAINS:
        return out
    want = (domain or "") in _REPORT_DEFAULT_DOMAINS or scan_content_report(
        proposal_text or ""
    )
    if not want:
        return out
    out.append(CONTENT_REPORT_CAP)
    return out


def attach_favorites_menus(
    schema: dict[str, Any],
    *,
    page_lead: str | None = None,
) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    user = menus.setdefault("user", [])
    item = {"key": "favorites", "label": "我的收藏"}
    if not any(m.get("key") == "favorites" for m in user):
        placed = False
        for before in ("cart", "my_orders", "content", "profile"):
            if any(m.get("key") == before for m in user):
                ensure_menu(user, "favorites", item, before_key=before)
                placed = True
                break
        if not placed:
            user.append(item)
    labels = schema.setdefault("labels", {})
    labels.setdefault("favoritesPageTitle", "我的收藏")
    labels.setdefault(
        "favoritesPageLead",
        page_lead or "收藏感兴趣的商品，便于再次加购。",
    )
    ents = schema.setdefault("entities", {})
    if "favorites" not in ents:
        ents["favorites"] = {"key": "favorites", "label": "收藏", "labelPlural": "收藏"}


def attach_content_report_menus(schema: dict[str, Any]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    admin = menus.setdefault("admin", [])
    ensure_menu(
        admin,
        "content_reports",
        {"key": "content_reports", "label": "举报管理"},
        before_key="guestbook",
    )
    labels = schema.setdefault("labels", {})
    labels.setdefault("contentReportsPageTitle", "举报管理")
    labels.setdefault(
        "contentReportsPageLead", "查看用户举报并处理（忽略或下架相关内容）。"
    )
    labels.setdefault("reportVerb", "举报")
    ents = schema.setdefault("entities", {})
    ents.setdefault(
        "contentReport",
        {"key": "content_report", "label": "举报", "labelPlural": "举报"},
    )


def apply_favorites_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    domain = spec.get("domain")
    text = proposal_text or ""
    caps = merge_favorites_capabilities(
        list(spec.get("capabilities") or []),
        text,
        domain=domain,
    )
    caps = merge_post_like_capabilities(caps, text, domain=domain)
    caps = merge_content_report_capabilities(caps, text, domain=domain)
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    features = list(spec.get("features") or [])
    names = {f.get("name") for f in features if isinstance(f, dict)}

    if FAVORITES_CAP in caps:
        lead = None
        if domain in _CONTENT_FAVORITE_DOMAINS:
            lead = "收藏感兴趣的内容，方便随时回看。"
        elif domain in _PROFILE_SCAN_FAVORITE_DOMAINS:
            lead = "收藏感兴趣的资料，便于再次牵线。"
        attach_favorites_menus(schema, page_lead=lead)
        from app.bake.gate_contracts import merge_favorites_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_favorites_gate(gate, caps)
        if domain in _CONTENT_FAVORITE_DOMAINS:
            fav_name = "内容收藏"
        elif domain in _PROFILE_SCAN_FAVORITE_DOMAINS:
            fav_name = "资料收藏"
        else:
            fav_name = "商品收藏"
        if fav_name not in names and "商品收藏" not in names:
            features.append({"name": fav_name, "status": "module"})
            names.add(fav_name)

    if POST_LIKE_CAP in caps:
        labels = schema.setdefault("labels", {})
        if isinstance(labels, dict):
            labels.setdefault("likeVerb", "点赞")
            labels.setdefault("likedVerb", "已赞")
        if "点赞" not in names:
            features.append({"name": "点赞", "status": "module"})
            names.add("点赞")
        from app.bake.gate_contracts import merge_post_like_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_post_like_gate(gate, caps)

    if CONTENT_REPORT_CAP in caps:
        attach_content_report_menus(schema)
        if "举报" not in names:
            features.append({"name": "举报", "status": "module"})
            names.add("举报")
        from app.bake.gate_contracts import merge_content_report_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_content_report_gate(gate, caps)

    spec["features"] = features
    spec["schema"] = schema
    return spec
