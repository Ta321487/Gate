"""features[].name 近义折叠：同能力只留一条规范名（清单去重，不是前端隐藏）。

过渡钉。正式可维护台见 docs/factory-asset-catalogs.md #13；口令「做功能名台」。
"""

from __future__ import annotations

from typing import Any

# (规范名, 别名全集含规范名)
FEATURE_ALIAS_GROUPS: tuple[tuple[str, frozenset[str]], ...] = (
    (
        "订单超时自动取消",
        frozenset({"订单超时自动取消", "订单超时未付自动取消"}),
    ),
    (
        "缺货到货通知",
        frozenset({"缺货到货通知", "商品到货订阅"}),
    ),
    (
        "消息模板",
        frozenset({"消息模板", "站内消息模板"}),
    ),
    (
        "限时购",
        frozenset({"限时购", "限时购倒计时展示"}),
    ),
    (
        "售后换货",
        frozenset({"售后换货", "仅换货不退款"}),
    ),
)

_ALIAS_TO_CANONICAL: dict[str, str] = {}
for _canon, _aliases in FEATURE_ALIAS_GROUPS:
    for _a in _aliases:
        _ALIAS_TO_CANONICAL[_a] = _canon

ORDER_TIMEOUT_FEATURE = "订单超时自动取消"
ORDER_TIMEOUT_FEATURE_ALIASES = frozenset(
    next(a for c, a in FEATURE_ALIAS_GROUPS if c == ORDER_TIMEOUT_FEATURE)
)
STOCK_NOTIFY_FEATURE = "缺货到货通知"
MESSAGE_TEMPLATE_FEATURE = "消息模板"
FLASH_PRICE_FEATURE = "限时购"
REFUND_EXCHANGE_FEATURE = "售后换货"


def feature_names(features: list | None) -> set[str]:
    return {
        f.get("name")
        for f in (features or [])
        if isinstance(f, dict) and f.get("name")
    }


def canonical_feature_name(name: str | None) -> str | None:
    if not name or not isinstance(name, str):
        return name
    return _ALIAS_TO_CANONICAL.get(name, name)


def collapse_feature_aliases(
    features: list | None, *, default_status: str | None = None
) -> list:
    """近义别名只留规范名一条；其它 features 原样保留。"""
    out: list = []
    kept_canon: set[str] = set()
    for f in features or []:
        if not isinstance(f, dict):
            out.append(f)
            continue
        name = f.get("name")
        canon = canonical_feature_name(name) if isinstance(name, str) else name
        if isinstance(name, str) and name in _ALIAS_TO_CANONICAL:
            if canon in kept_canon:
                continue
            kept_canon.add(str(canon))
            row = dict(f)
            row["name"] = canon
            if default_status and not row.get("status"):
                row["status"] = default_status
            out.append(row)
            continue
        out.append(f)
    return out


def has_feature(features: list | None, canonical: str) -> bool:
    aliases = next((a for c, a in FEATURE_ALIAS_GROUPS if c == canonical), frozenset({canonical}))
    return bool(feature_names(features) & aliases)


def ensure_feature(
    features: list | None,
    canonical: str,
    *,
    status: str = "module",
) -> list:
    """折叠近义后若不存在规范名则追加。"""
    out = collapse_feature_aliases(features, default_status=status)
    if not has_feature(out, canonical):
        out = list(out)
        out.append({"name": canonical, "status": status})
    return out


def collapse_order_timeout_features(
    features: list | None, *, status: str = "module"
) -> list:
    return collapse_feature_aliases(features, default_status=status)


def ensure_order_timeout_feature(
    features: list | None, *, status: str = "module"
) -> list:
    return ensure_feature(features, ORDER_TIMEOUT_FEATURE, status=status)


def has_order_timeout_feature(features: list | None) -> bool:
    return has_feature(features, ORDER_TIMEOUT_FEATURE)
