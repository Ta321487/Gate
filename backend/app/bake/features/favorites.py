"""收藏夹：user_favorite 一表。

- 交易域（SHOP/FOOD 默认；其它 order_lines 开题写到才挂）：收藏后可再加购
- 内容流（MEDIA/MUSIC/BLOG）：即时收藏，不走单据/审核
"""

from __future__ import annotations

import re
from typing import Any

FAVORITES_CAP = "favorites"

_FAVORITES_SIGNALS = re.compile(
    r"收藏夹|我的收藏|商品收藏|加入收藏|收藏功能|wishlist|favorite"
)

_DEFAULT_TRADE_DOMAINS = frozenset({"DOM-SHOP", "DOM-FOOD"})
# 内容流默认即时收藏；不含 FORUM（回帖仍走 ticket 审核）
_CONTENT_FAVORITE_DOMAINS = frozenset({"DOM-MEDIA", "DOM-MUSIC", "DOM-BLOG"})


def scan_favorites(text: str) -> bool:
    return bool(_FAVORITES_SIGNALS.search(text or ""))


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
    # 非交易且非内容收藏域：剥掉误带的 favorites
    if "order_lines" not in out and domain not in _CONTENT_FAVORITE_DOMAINS:
        return [c for c in out if c != FAVORITES_CAP]
    want = force or favorites_wanted(
        domain=domain, capabilities=out, proposal_text=proposal_text
    )
    if want and FAVORITES_CAP not in out:
        out.append(FAVORITES_CAP)
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


def attach_favorites_menus(
    schema: dict[str, Any],
    *,
    page_lead: str | None = None,
) -> None:
    menus = schema.setdefault("menus", {})
    user = menus.setdefault("user", [])
    item = {"key": "favorites", "label": "我的收藏"}
    if not any(m.get("key") == "favorites" for m in user):
        placed = False
        for before in ("cart", "my_orders", "content", "profile"):
            if any(m.get("key") == before for m in user):
                _ensure_menu(user, "favorites", item, before_key=before)
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


def apply_favorites_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    domain = spec.get("domain")
    caps = merge_favorites_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text,
        domain=domain,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if FAVORITES_CAP in caps:
        lead = None
        if domain in _CONTENT_FAVORITE_DOMAINS:
            lead = "收藏感兴趣的内容，方便随时回看。"
        attach_favorites_menus(schema, page_lead=lead)
        from app.bake.gate_contracts import merge_favorites_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_favorites_gate(gate, caps)
        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        fav_name = "内容收藏" if domain in _CONTENT_FAVORITE_DOMAINS else "商品收藏"
        if fav_name not in names and "商品收藏" not in names:
            features.append({"name": fav_name, "status": "module"})
        spec["features"] = features
    spec["schema"] = schema
    return spec
