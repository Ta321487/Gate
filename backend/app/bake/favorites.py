"""交易域收藏夹：user_favorite 一表；默认 SHOP/FOOD，开题写收藏时可扫入其它 order_lines 域。"""

from __future__ import annotations

import re
from typing import Any

FAVORITES_CAP = "favorites"

_FAVORITES_SIGNALS = re.compile(
    r"收藏夹|我的收藏|商品收藏|加入收藏|收藏功能|wishlist|favorite"
)

_DEFAULT_DOMAINS = frozenset({"DOM-SHOP", "DOM-FOOD"})


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
    # 未显式传 caps 时，用域默认能力判断是否交易域
    if not caps and domain:
        from app.bake.domains import DOMAIN_CAPABILITIES

        caps = list(DOMAIN_CAPABILITIES.get(domain) or [])
    if "order_lines" not in caps:
        return False
    if domain in _DEFAULT_DOMAINS:
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
    if "order_lines" not in out:
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


def attach_favorites_menus(schema: dict[str, Any]) -> None:
    menus = schema.setdefault("menus", {})
    user = menus.setdefault("user", [])
    _ensure_menu(
        user,
        "favorites",
        {"key": "favorites", "label": "我的收藏"},
        before_key="cart",
    )
    if not any(m.get("key") == "favorites" for m in user):
        _ensure_menu(user, "favorites", {"key": "favorites", "label": "我的收藏"}, before_key="my_orders")
    labels = schema.setdefault("labels", {})
    labels.setdefault("favoritesPageTitle", "我的收藏")
    labels.setdefault("favoritesPageLead", "收藏感兴趣的商品，便于再次加购。")
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
        attach_favorites_menus(schema)
        from app.bake.gate_contracts import merge_favorites_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_favorites_gate(gate, caps)
        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "商品收藏" not in names:
            features.append({"name": "商品收藏", "status": "module"})
        spec["features"] = features
    spec["schema"] = schema
    return spec
