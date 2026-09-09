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
    """能力已开则菜单必须在：防填岛/壳重写漏挂 favorites、dm、评价等。"""
    caps = set(schema.get("capabilities") or [])
    menus = schema.setdefault("menus", {})
    user = menus.setdefault("user", [])
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
        shop_cs = bool(schema.get("dmShopCs"))
        dm_lab = labels.get("dmPageTitle") or ("客服" if shop_cs else "私信")
        ensure_menu(
            user,
            "dm",
            {"key": "dm", "label": dm_lab},
            before_key="messages",
        )
        if not any(m.get("key") == "dm" for m in user):
            ensure_menu(
                user,
                "dm",
                {"key": "dm", "label": dm_lab},
                before_key="profile",
            )
    if "order_review" in caps:
        ensure_menu(
            user,
            "order_reviews",
            {"key": "order_reviews", "label": labels.get("orderReviewPageTitle") or "我的评价"},
            before_key="my_orders",
        )
        admin = menus.setdefault("admin", [])
        ensure_menu(
            admin,
            "order_reviews",
            {"key": "order_reviews", "label": "评价管理"},
            before_key="orders",
        )
    if "guestbook" in caps:
        ensure_menu(
            user,
            "guestbook",
            {"key": "guestbook", "label": labels.get("guestbookPageTitle") or "留言反馈"},
            before_key="content",
        )

