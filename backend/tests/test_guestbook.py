"""guestbook 能力：开题扫描、交易默认、SQL 注入、Spec 挂载。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import attach_accept
from app.bake.engine import count_create_tables, domain_sql
from app.bake.features.guestbook import (
    GUESTBOOK_CAP,
    apply_guestbook_to_spec,
    merge_guestbook_capabilities,
    scan_guestbook,
)
from tests.helpers.normalize import normalize_sql


class GuestbookCapabilityTests(unittest.TestCase):
    def test_scan_guestbook_keywords(self) -> None:
        self.assertTrue(scan_guestbook("前台公告与留言功能"))
        self.assertTrue(scan_guestbook("支持访客留言与留言管理"))
        self.assertFalse(scan_guestbook("仅公告浏览，无其它互动"))

    def test_trade_defaults_include_guestbook(self) -> None:
        for domain in ("DOM-SHOP", "DOM-FOOD"):
            caps = merge_guestbook_capabilities(
                ["archive", "order_lines", "content"],
                "",
                domain=domain,
            )
            self.assertIn(GUESTBOOK_CAP, caps)

        caps = merge_guestbook_capabilities(
            ["archive", "order_lines", "content"],
            "",
            domain="DOM-GENERIC",
            archetype="ARCH-TRADE",
            archetypes=["ARCH-TRADE"],
        )
        self.assertIn(GUESTBOOK_CAP, caps)

    def test_forum_never_gets_guestbook(self) -> None:
        caps = merge_guestbook_capabilities(
            ["archive", "ticket_flow", "content"],
            "需要留言板与论坛",
            domain="DOM-FORUM",
        )
        self.assertNotIn(GUESTBOOK_CAP, caps)

    def test_proposal_adds_guestbook_on_library(self) -> None:
        caps = merge_guestbook_capabilities(
            ["archive", "ticket_flow", "content"],
            "读者可在门户发表留言，管理员回复",
            domain="DOM-LIBRARY",
        )
        self.assertIn(GUESTBOOK_CAP, caps)

    def test_apply_spec_menus_and_entities(self) -> None:
        spec = apply_guestbook_to_spec(
            {
                "domain": "DOM-GENERIC",
                "archetype": "ARCH-TRADE",
                "archetypes": ["ARCH-TRADE"],
                "capabilities": ["archive", "order_lines", "content", "org_users"],
                "entities": ["Item", "Category", "CartLine", "Order", "Notice"],
                "features": [],
                "schema": {"menus": {"admin": [], "user": []}, "labels": {}},
                "gate": {},
            }
        )
        self.assertIn(GUESTBOOK_CAP, spec["capabilities"])
        self.assertIn("Guestbook", spec["entities"])
        admin_keys = [m["key"] for m in spec["schema"]["menus"]["admin"]]
        user_keys = [m["key"] for m in spec["schema"]["menus"]["user"]]
        self.assertIn("guestbook", admin_keys)
        self.assertIn("guestbook", user_keys)

    def test_attach_accept_flower_proposal(self) -> None:
        text = "前台支持公告与留言；后台留言管理。"
        spec = attach_accept(
            {
                "title": "鲜花销售管理系统的设计与实现",
                "domain": "DOM-GENERIC",
                "archetype": "ARCH-TRADE",
                "archetypes": ["ARCH-TRADE"],
                "capabilities": [
                    "archive",
                    "order_lines",
                    "quota",
                    "content",
                    "org_users",
                ],
                "entities": ["Item", "Category", "CartLine", "Order", "Notice"],
                "features": [],
                "schema": {"version": 1, "title": "t", "capabilities": []},
            },
            text,
        )
        self.assertIn(GUESTBOOK_CAP, spec["capabilities"])
        self.assertEqual(spec.get("accept"), "full")

    def test_trade_sql_injects_guestbook_within_budget(self) -> None:
        sql = domain_sql(
            "DOM-GENERIC",
            "thesis_test",
            archetype="ARCH-TRADE",
            archetypes=["ARCH-TRADE"],
        )
        self.assertIn("sys_guestbook", sql)
        n = count_create_tables(sql)
        self.assertLessEqual(n, 13)
        self.assertGreaterEqual(n, 6)

        shop = domain_sql("DOM-SHOP", "thesis_test")
        self.assertIn("sys_guestbook", shop)
        self.assertLessEqual(count_create_tables(shop), 13)

    def test_library_without_keyword_no_guestbook_table(self) -> None:
        sql = normalize_sql(domain_sql("DOM-LIBRARY", "thesis_test"))
        self.assertNotIn("sys_guestbook", sql)


if __name__ == "__main__":
    unittest.main()
