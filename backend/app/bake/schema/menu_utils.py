"""菜单列表幂等插入（features / archetype_shells 共用）。"""

from __future__ import annotations

from typing import Any


def ensure_menu(
    menus: list[dict],
    key: str,
    item: dict,
    *,
    before_key: str | None = None,
) -> None:
    """若 key 已存在则跳过；否则插到 before_key 之前，找不到则追加。"""
    if any(m.get("key") == key for m in menus):
        return
    if before_key:
        for i, m in enumerate(menus):
            if m.get("key") == before_key:
                menus.insert(i, item)
                return
    menus.append(item)


def sync_user_menus_from_caps(schema: dict[str, Any]) -> None:
    """能力已开则菜单必须在：防填岛/壳重写漏挂 favorites、dm、评价等。

    同时补 admin 侧 dm（商家客服/办理岗私信）；仅补 user 会导致店长看不到入口。
    """
    caps = set(schema.get("capabilities") or [])
    menus = schema.setdefault("menus", {})
    user = menus.setdefault("user", [])
    admin = menus.setdefault("admin", [])
    labels = schema.setdefault("labels", {})

    if "favorites" in caps:
        ensure_menu(
            user,
            "favorites",
            {"key": "favorites", "label": labels.get("favoritesPageTitle") or "我的收藏"},
            before_key="cart",
        )
        labels.setdefault("favoritesPageTitle", "我的收藏")
    if "dm" in caps:
        # 多店商城有 dm 但未落 dmShopCs 时，按店铺客服收口（与 resolve_dm_peer_mode 默认同向）
        if not schema.get("dmShopCs") and schema.get("shopMarketplace"):
            schema["dmShopCs"] = True
        shop_cs = bool(schema.get("dmShopCs"))
        dm_lab = labels.get("dmPageTitle") or ("客服" if shop_cs else "私信")
        ensure_menu(
            user,
            "dm",
            {"key": "dm", "label": dm_lab},
            before_key="messages",
        )
        if not any(isinstance(m, dict) and m.get("key") == "dm" for m in user):
            ensure_menu(
                user,
                "dm",
                {"key": "dm", "label": dm_lab},
                before_key="profile",
            )
        ensure_menu(
            admin,
            "dm",
            {"key": "dm", "label": dm_lab, "superOnly": False},
            before_key="guestbook",
        )
        if not any(isinstance(m, dict) and m.get("key") == "dm" for m in admin):
            ensure_menu(
                admin,
                "dm",
                {"key": "dm", "label": dm_lab, "superOnly": False},
                before_key="orders",
            )
        for m in admin:
            if isinstance(m, dict) and m.get("key") == "dm":
                m["label"] = dm_lab
                m["superOnly"] = False
        labels["dmPageTitle"] = dm_lab
        if shop_cs:
            labels.setdefault("dmPageLead", "与店铺商家一对一沟通，打开会话后自动刷新新消息。")
            labels.setdefault("dmNewTitle", "联系商家客服")
            labels.setdefault("dmPeerPlaceholder", "选择店铺商家")
            labels.setdefault("dmEmptyPeers", "暂无会话，点「新建」选店铺商家。")
            labels.setdefault("dmEmptyChat", "选择左侧会话，或新建联系商家。")
            labels.setdefault("dmMerchantPageLead", "回复买家咨询，打开会话后自动刷新新消息。")
            labels.setdefault("dmMerchantNewTitle", "联系买家")
            labels.setdefault("dmMerchantPeerPlaceholder", "选择买家账号")
            labels.setdefault(
                "dmMerchantEmptyPeers",
                "暂无会话，买家发起咨询后会出现在这里；也可点「新建」选买家。",
            )
            labels.setdefault("dmMerchantEmptyChat", "选择左侧会话，或新建联系买家。")
    if "order_review" in caps:
        ensure_menu(
            user,
            "order_reviews",
            {"key": "order_reviews", "label": labels.get("orderReviewPageTitle") or "我的评价"},
            before_key="my_orders",
        )
        ensure_menu(
            admin,
            "order_reviews",
            {"key": "order_reviews", "label": "评价管理", "superOnly": False},
            before_key="orders",
        )
    if "guestbook" in caps:
        ensure_menu(
            user,
            "guestbook",
            {"key": "guestbook", "label": labels.get("guestbookPageTitle") or "留言反馈"},
            before_key="content",
        )

