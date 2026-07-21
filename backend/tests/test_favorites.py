"""favorites 能力：默认 SHOP/FOOD、SQL 注入、Spec 挂载。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import attach_accept
from app.bake.engine import count_create_tables, domain_sql
from app.bake.favorites import (
    FAVORITES_CAP,
    apply_favorites_to_spec,
    merge_favorites_capabilities,
    scan_favorites,
)
from tests._normalize import normalize_sql


class FavoritesCapabilityTests(unittest.TestCase):
    def test_scan_favorites_keywords(self) -> None:
        self.assertTrue(scan_favorites("支持商品收藏与我的收藏"))
        self.assertTrue(scan_favorites("加入收藏夹"))
        self.assertFalse(scan_favorites("仅购物车与订单"))

    def test_trade_defaults_include_favorites(self) -> None:
        for domain in ("DOM-SHOP", "DOM-FOOD"):
            caps = merge_favorites_capabilities(
                ["archive", "order_lines", "content"],
                "",
                domain=domain,
            )
            self.assertIn(FAVORITES_CAP, caps)

    def test_requires_order_lines(self) -> None:
        caps = merge_favorites_capabilities(
            ["archive", "ticket_flow"],
            "我的收藏",
            domain="DOM-LIBRARY",
        )
        self.assertNotIn(FAVORITES_CAP, caps)

    def test_sql_injects_user_favorite(self) -> None:
        sql = domain_sql("DOM-SHOP", "thesis_shop")
        n = normalize_sql(sql)
        self.assertIn("user_favorite", n)
        self.assertLessEqual(count_create_tables(sql), 13)

    def test_attach_accept_merges_favorites(self) -> None:
        out = attach_accept(
            {
                "domain": "DOM-SHOP",
                "capabilities": ["archive", "order_lines", "quota", "content", "org_users"],
                "schema": {"menus": {"user": [{"key": "cart", "label": "购物车"}]}},
            },
            "鲜花商城，支持收藏夹",
        )
        caps = out.get("capabilities") or []
        self.assertIn(FAVORITES_CAP, caps)
        menus = (out.get("schema") or {}).get("menus", {}).get("user") or []
        self.assertTrue(any(m.get("key") == "favorites" for m in menus))

    def test_apply_favorites_to_spec(self) -> None:
        spec = apply_favorites_to_spec(
            {
                "domain": "DOM-GENERIC",
                "capabilities": ["archive", "order_lines"],
                "schema": {},
            },
            "商品收藏功能",
        )
        self.assertIn(FAVORITES_CAP, spec.get("capabilities") or [])


if __name__ == "__main__":
    unittest.main()
