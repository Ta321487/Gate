"""办理岗菜单对称：能力/菜单挂了则岗包可见，且不得 superOnly 挡死。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import attach_accept
from app.bake.features.dm import apply_dm_to_spec
from app.bake.staff_posts import (
    PACK_ADMIN_MENUS,
    enrich_clerk_pack_menus,
    open_clerk_admin_menus,
)


class ClerkPackSymmetryTests(unittest.TestCase):
    def test_order_ops_includes_review_guestbook_coupons(self) -> None:
        for k in ("order_reviews", "guestbook", "coupons", "dm"):
            self.assertIn(k, PACK_ADMIN_MENUS["order_ops"])

    def test_ticket_ops_includes_moderation_keys(self) -> None:
        for k in ("content_reports", "book_suggest", "staff_roster", "guestbook", "dm"):
            self.assertIn(k, PACK_ADMIN_MENUS["ticket_ops"])

    def test_food_counter_sees_order_reviews(self) -> None:
        out = attach_accept(
            {
                "domain": "DOM-FOOD",
                "title": "校园食堂点餐",
                "capabilities": ["archive", "order_lines", "quota", "content", "org_users"],
                "schema": {},
            },
            "店员接单发货，订单评价与回复，留言反馈，优惠券核销",
        )
        packs = (out.get("schema") or {}).get("staffPackMenus") or {}
        order_ops = set(packs.get("order_ops") or [])
        self.assertIn("orders", order_ops)
        self.assertIn("order_reviews", order_ops)
        admin = (out.get("schema") or {}).get("menus", {}).get("admin") or []
        rev = next((m for m in admin if isinstance(m, dict) and m.get("key") == "order_reviews"), None)
        self.assertIsNotNone(rev)
        self.assertFalse(rev.get("superOnly"))

    def test_forum_moderator_sees_reports_or_users_for_mute(self) -> None:
        out = attach_accept(
            {
                "domain": "DOM-FORUM",
                "title": "校园论坛",
                "capabilities": ["archive", "ticket_flow", "content", "org_users"],
                "schema": {},
            },
            "发帖回帖审核，举报管理，禁言处罚，版主私信",
        )
        packs = (out.get("schema") or {}).get("staffPackMenus") or {}
        ticket = set(packs.get("ticket_ops") or [])
        self.assertTrue(
            "content_reports" in ticket or "users" in ticket,
            f"版主须能举报或禁言 users，got={sorted(ticket)}",
        )
        admin = (out.get("schema") or {}).get("menus", {}).get("admin") or []
        if "content_reports" in ticket:
            row = next((m for m in admin if isinstance(m, dict) and m.get("key") == "content_reports"), None)
            self.assertIsNotNone(row)
            self.assertFalse(row.get("superOnly"))

    def test_library_book_suggest_not_super_only_for_clerk(self) -> None:
        out = attach_accept(
            {
                "domain": "DOM-LIBRARY",
                "title": "图书管理系统",
                "capabilities": ["archive", "ticket_flow", "content", "org_users"],
                "schema": {},
            },
            "读者荐购与馆员荐购审核",
        )
        packs = (out.get("schema") or {}).get("staffPackMenus") or {}
        ticket = set(packs.get("ticket_ops") or [])
        admin = (out.get("schema") or {}).get("menus", {}).get("admin") or []
        suggest = next((m for m in admin if isinstance(m, dict) and m.get("key") == "book_suggest"), None)
        if suggest:
            self.assertIn("book_suggest", ticket)
            self.assertFalse(suggest.get("superOnly"))

    def test_dm_admin_menu_for_non_shop(self) -> None:
        spec = apply_dm_to_spec(
            {
                "domain": "DOM-DATING",
                "capabilities": ["archive", "ticket_flow", "dm"],
                "entities": [],
                "features": [],
                "schema": {"menus": {"admin": [{"key": "users", "label": "用户"}], "user": []}, "labels": {}},
                "gate": {},
            },
            "会员一对一私信",
        )
        admin = (spec.get("schema") or {}).get("menus", {}).get("admin") or []
        dm = next((m for m in admin if isinstance(m, dict) and m.get("key") == "dm"), None)
        self.assertIsNotNone(dm)
        self.assertFalse(dm.get("superOnly"))

    def test_enrich_only_keeps_existing_menus(self) -> None:
        schema = {
            "capabilities": ["order_review", "guestbook"],
            "menus": {
                "admin": [
                    {"key": "dashboard", "label": "工作台"},
                    {"key": "orders", "label": "订单"},
                    {"key": "order_reviews", "label": "评价", "superOnly": True},
                ]
            },
        }
        packs = enrich_clerk_pack_menus(schema, {"order_ops"})
        keys = set(packs["order_ops"])
        self.assertIn("order_reviews", keys)
        self.assertNotIn("guestbook", keys)  # 菜单未挂
        open_clerk_admin_menus(schema, packs)
        rev = schema["menus"]["admin"][2]
        self.assertFalse(rev.get("superOnly"))


if __name__ == "__main__":
    unittest.main()
