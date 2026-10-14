"""菜单列表幂等插入 + 通用菜单键收束（无域皮文案、不调 feature attach）。

硬拦 ↔ 收集 UI 合同见 ``hard_assert_ui``。
"""

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
    """能力已开则通用菜单键必须在（favorites / 评价 / 留言）。

    dm 的菜单与店铺客服文案见 ``dm.sync_dm_surface_from_caps``。
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
