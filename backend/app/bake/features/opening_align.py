"""开题模块枚举 ∩ 实包：工厂能交却未挂 → 禁止静默薄包。"""

from __future__ import annotations

from typing import Any

# (材料关键词, 缺口说明, 判定已交付)
# 仅高置信、跨开题常见；避免误伤短题。
_ALIGN_RULES: list[tuple[tuple[str, ...], str, str]] = [
    (("购物车",), "购物车", "cart"),
    (("收货地址", "地址簿"), "收货地址", "addresses"),
    (("收藏",), "收藏", "favorites"),
    (("留言", "留言反馈"), "留言反馈", "guestbook"),
    (("客服", "站内私信", "在线沟通"), "客服/私信", "dm"),
    (("评价模块", "商品评价", "订单评价", "确认收货后可发表评价"), "订单评价", "order_review"),
    (("申请售后", "退货申请", "售后管理"), "售后/退货", "refund"),
    # 词表与 scene_scan.SHOP_MARKETPLACE_HINTS 对齐；命中检测走 scan_shop_marketplace
    (("商家入驻", "多商家", "商家端", "卖家中心"), "多商家入驻", "marketplace"),
]

# 内容壳：条下评论 / 投稿 / 先审（与交易规则分开，避免商城「评论」误伤）
_CONTENT_ALIGN_RULES: list[tuple[tuple[str, ...], str, str]] = [
    (
        ("条下评论", "评论区", "用户评论", "发表评论", "评论模块", "影评", "视频评论"),
        "条下评论",
        "item_comment",
    ),
    (
        ("用户投稿", "读者投稿", "在线投稿", "用户上传", "用户发布文章", "上传视频", "上传曲目"),
        "用户投稿",
        "user_publish",
    ),
    (
        ("投稿审核", "先审后发", "审核后上架", "发帖需审核", "投稿需审核", "审核通过后可见"),
        "投稿先审",
        "publish_review",
    ),
]

_TRADE_ALIGN_DOMAINS = frozenset(
    {"DOM-SHOP", "DOM-FOOD", "DOM-CINEMA", "DOM-HOTEL", "DOM-CARRENT"}
)
_CONTENT_ALIGN_DOMAINS = frozenset({"DOM-MEDIA", "DOM-MUSIC", "DOM-BLOG", "DOM-FORUM"})


def _menu_keys(schema: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    menus = schema.get("menus") if isinstance(schema.get("menus"), dict) else {}
    for side in ("user", "admin"):
        for m in menus.get(side) or []:
            if isinstance(m, dict) and m.get("key"):
                keys.add(str(m["key"]))
    return keys


def _caps(spec: dict[str, Any]) -> set[str]:
    return {str(c) for c in (spec.get("capabilities") or []) if c}


def _archive_flag(schema: dict[str, Any], key: str) -> bool:
    ents = schema.get("entities") if isinstance(schema.get("entities"), dict) else {}
    arch = ents.get("archive") if isinstance(ents.get("archive"), dict) else {}
    return bool(arch.get(key))


def _delivered(kind: str, *, spec: dict[str, Any], schema: dict[str, Any]) -> bool:
    keys = _menu_keys(schema)
    caps = _caps(spec)
    if kind == "cart":
        return "cart" in keys or "order_lines" in caps
    if kind == "addresses":
        return "addresses" in keys or "order_lines" in caps
    if kind == "favorites":
        return "favorites" in caps or "favorites" in keys
    if kind == "guestbook":
        return "guestbook" in caps or "guestbook" in keys
    if kind == "dm":
        return "dm" in caps or "dm" in keys
    if kind == "order_review":
        return "order_review" in caps or "order_reviews" in keys
    if kind == "refund":
        # 壳附带：有订单即有售后入口（订单页按钮），不单独占菜单
        return "order_lines" in caps or "orders" in keys or "my_orders" in keys
    if kind == "marketplace":
        return bool(schema.get("shopMarketplace"))
    if kind == "item_comment":
        return "item_comment" in caps or "item_comments" in keys
    if kind == "user_publish":
        return _archive_flag(schema, "userPublish") or "my_archive" in keys
    if kind == "publish_review":
        return _archive_flag(schema, "publishReview")
    return True


def _rule_mentioned(
    terms: tuple[str, ...],
    kind: str,
    raw: str,
    *,
    domain: str,
) -> bool:
    """材料是否点名该对齐项。客服：剥掉智能客服后再认，避免 AI 岛误伤。"""
    if kind == "dm":
        if any(t in raw for t in terms if t != "客服"):
            return True
        if "客服" not in terms:
            return False
        from app.bake.features.dm import scan_dm, scan_trade_customer_service

        if domain in ("DOM-SHOP", "DOM-FOOD"):
            return scan_trade_customer_service(raw)
        # 非交易：客服模块 / 私信信号；纯智能客服不计入
        return scan_trade_customer_service(raw) or scan_dm(raw)
    if kind == "marketplace":
        from app.bake.scene_scan import scan_shop_marketplace

        return scan_shop_marketplace("", raw) or any(t in raw for t in terms)
    if kind == "item_comment":
        from app.bake.features.item_comment import scan_item_comment

        # 论坛跟帖≠条下评论；仅 MEDIA/MUSIC/BLOG 走扫词
        if domain in ("DOM-MEDIA", "DOM-MUSIC", "DOM-BLOG"):
            return scan_item_comment(raw)
        return any(t in raw for t in terms)
    if kind == "user_publish":
        from app.bake.features.user_publish import scan_user_publish

        return scan_user_publish(raw, domain=domain)
    if kind == "publish_review":
        from app.bake.features.user_publish import scan_publish_review

        return scan_publish_review(raw)
    return any(t in raw for t in terms)


def scan_opening_delivery_gaps(
    spec: dict[str, Any],
    proposal_text: str = "",
) -> list[str]:
    """返回「开题写了且工厂能交、但实包未挂」的缺口说明。"""
    raw = proposal_text or ""
    if len(raw.strip()) < 20:
        return []
    domain = str(spec.get("domain") or "")
    if domain in _TRADE_ALIGN_DOMAINS:
        rules = list(_ALIGN_RULES)
    elif domain in _CONTENT_ALIGN_DOMAINS:
        # 内容壳：留言/收藏/私信 + 评论/投稿/先审
        rules = [r for r in _ALIGN_RULES if r[2] in ("guestbook", "dm", "favorites")]
        rules.extend(_CONTENT_ALIGN_RULES)
        # 论坛主帖默认已有 userPublish；跟帖走 ticket，不按条下评论门禁
        if domain == "DOM-FORUM":
            rules = [r for r in rules if r[2] not in ("item_comment",)]
    else:
        # 其它域：仍查留言/私信/收藏
        rules = [r for r in _ALIGN_RULES if r[2] in ("guestbook", "dm", "favorites")]

    schema = spec.get("schema") if isinstance(spec.get("schema"), dict) else {}
    gaps: list[str] = []
    for terms, label, kind in rules:
        if not _rule_mentioned(terms, kind, raw, domain=domain):
            continue
        if _delivered(kind, spec=spec, schema=schema):
            continue
        gap = f"开题写了「{label}」但实包未挂"
        if gap not in gaps:
            gaps.append(gap)
    return gaps


def apply_opening_align_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    """缺口写入 schema，并在本可 full 时改为 reject，禁止静默薄包。"""
    gaps = scan_opening_delivery_gaps(spec, proposal_text)
    sch = spec.get("schema") if isinstance(spec.get("schema"), dict) else {}
    sch = dict(sch)
    sch["openingGaps"] = gaps
    spec["schema"] = sch
    if not gaps:
        return spec
    # 已因超壳/缺能力 reject 的，只附加 gaps，不改原因主语
    if spec.get("accept") == "full":
        spec["accept"] = "reject"
        spec["accept_reason"] = (
            "开题模块与实包未对齐（"
            + "；".join(gaps[:4])
            + ("…" if len(gaps) > 4 else "")
            + "）；请确认匹配域与能力扫词，禁止静默薄包出炉"
        )
        feats = list(spec.get("features") or [])
        for g in gaps:
            feats.append({"name": g, "status": "gap"})
        spec["features"] = feats
    return spec
