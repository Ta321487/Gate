"""商城多店（shop marketplace）扫描 / schema / SQL 门禁。"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from app.bake.engine_sql import domain_sql
from app.bake.scene_scan import scan_shop_marketplace
from app.bake.schema.builders_slot import _shop_schema

_SHOP_SQL = Path(__file__).resolve().parents[1] / "app" / "bake" / "sql" / "templates" / "DOM-SHOP.sql"


def _product_create_body(sql: str) -> str:
    m = re.search(
        r"CREATE TABLE IF NOT EXISTS\s+product\s*\((.*?)\n\s*created_at\b",
        sql,
        re.I | re.S,
    )
    assert m is not None, "product CREATE missing"
    return m.group(1)


def _notice_create_body(sql: str) -> str:
    m = re.search(
        r"CREATE TABLE IF NOT EXISTS\s+sys_notice\s*\((.*?)\n\s*created_at\b",
        sql,
        re.I | re.S,
    )
    assert m is not None, "sys_notice CREATE missing"
    return m.group(1)


class ShopMarketplaceScanTests(unittest.TestCase):
    def test_scan_on(self) -> None:
        self.assertTrue(scan_shop_marketplace("多商家入驻电商", "支持商家入驻与店铺审核"))
        self.assertTrue(scan_shop_marketplace("", "平台商家注册与入驻审核"))

    def test_scan_off(self) -> None:
        self.assertFalse(scan_shop_marketplace("农产品电商", "助农生鲜果蔬粮油选购"))
        self.assertFalse(scan_shop_marketplace("日用百货商城", "购物车下单配送"))


class ShopMarketplaceSchemaTests(unittest.TestCase):
    def test_marketplace_schema_flag(self) -> None:
        schema = _shop_schema("多商家电商平台", "商家入驻与店铺管理")
        self.assertTrue(schema.get("shopMarketplace"))
        content = next(
            (
                m
                for m in (schema.get("menus") or {}).get("admin") or []
                if isinstance(m, dict) and m.get("key") == "content"
            ),
            None,
        )
        self.assertIsNotNone(content)
        self.assertFalse(content.get("superOnly"))
        users = next(
            (
                m
                for m in (schema.get("menus") or {}).get("admin") or []
                if isinstance(m, dict) and m.get("key") == "users"
            ),
            None,
        )
        self.assertTrue(users.get("superOnly"))
        self.assertEqual(users.get("label"), "用户管理")
        dash = next(
            (
                m
                for m in (schema.get("menus") or {}).get("admin") or []
                if isinstance(m, dict) and m.get("key") == "dashboard"
            ),
            None,
        )
        self.assertEqual(dash.get("label"), "数据分析")
        hint = (schema.get("labels") or {}).get("registerRoleHint") or ""
        self.assertIn("管理员不开放自助注册", hint)
        posts = __import__("app.bake.staff_posts", fromlist=["staff_posts_for_domain"]).staff_posts_for_domain(
            "DOM-SHOP", title="多商家电商平台", proposal_text="商家入驻与店铺管理"
        )
        self.assertTrue(any(p.get("id") == "shop_merchant" and p.get("label") == "商家" for p in posts))
        from app.bake.profile_fields import profile_fields_for

        fields = profile_fields_for(
            "DOM-SHOP", title="多商家电商平台", proposal_text="商家入驻与店铺管理"
        )
        shop_name = next((f for f in fields if isinstance(f, dict) and f.get("key") == "shopName"), None)
        self.assertIsNotNone(shop_name)
        self.assertEqual(shop_name.get("forRoles"), ["staff"])
        self.assertTrue(shop_name.get("onRegister"))
        self.assertTrue(schema.get("demoPay"))
        states = ((schema.get("entities") or {}).get("order") or {}).get("states") or {}
        self.assertEqual(states.get("pending"), "待付款")
        self.assertEqual(states.get("confirmed"), "待发货")
        self.assertIn("in_transit", states)
        self.assertIn("signed", states)
        self.assertEqual(schema.get("stockWarnBelow"), 10)
        self.assertIn("双通道", (schema.get("labels") or {}).get("guestbookPageLead") or "")
        self.assertEqual((schema.get("labels") or {}).get("dmPageTitle"), "客服")

    def test_single_farm_no_marketplace(self) -> None:
        schema = _shop_schema("农产品电商", "助农生鲜果蔬粮油")
        self.assertFalse(bool(schema.get("shopMarketplace")))


class ShopMarketplaceSqlTests(unittest.TestCase):
    def test_single_shop_no_marketplace_columns(self) -> None:
        sql = domain_sql(
            "DOM-SHOP",
            "t_shop_single",
            title="农产品电商",
            proposal_text="助农生鲜果蔬粮油选购下单",
        )
        product = _product_create_body(sql)
        self.assertNotIn("owner_username", product)
        notice = _notice_create_body(sql)
        self.assertNotIn("audit_status", notice)
        self.assertNotIn("submitter_username", notice)
        self.assertNotIn("merchant_b", sql)
        self.assertNotIn("shop_merchant", sql)
        self.assertNotRegex(
            sql,
            r"CREATE TABLE IF NOT EXISTS\s+sys_guestbook\s*\([^;]*\bchannel\b",
        )

    def test_marketplace_sql_has_owner_and_audit(self) -> None:
        sql = domain_sql(
            "DOM-SHOP",
            "t_shop_mp",
            title="多商家入驻电商平台",
            proposal_text="支持商家入驻、店铺审核与多商户商品上架",
        )
        product = _product_create_body(sql)
        self.assertIn("owner_username", product)
        notice = _notice_create_body(sql)
        self.assertIn("audit_status", notice)
        self.assertIn("submitter_username", notice)
        self.assertIn("merchant_b", sql)
        self.assertIn("shop_merchant", sql)
        self.assertIn("owner_username", sql)
        self.assertRegex(
            sql,
            r"CREATE TABLE IF NOT EXISTS\s+sys_guestbook\s*\([^;]*\bchannel\b",
        )
        self.assertIn("(username, nickname, body, channel)", sql)
        self.assertRegex(
            sql,
            r"INSERT INTO sys_guestbook[\s\S]*?'user'[\s\S]*?FROM DUAL WHERE NOT EXISTS \(SELECT 1 FROM sys_guestbook",
        )
        self.assertRegex(
            sql,
            r"INSERT INTO sys_guestbook[\s\S]*?'merchant'[\s\S]*?FROM DUAL WHERE NOT EXISTS \(SELECT 1 FROM sys_guestbook",
        )


if __name__ == "__main__":
    unittest.main()
