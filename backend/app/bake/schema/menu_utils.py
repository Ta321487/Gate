"""菜单列表幂等插入（features / archetype_shells 共用）。"""

from __future__ import annotations


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
