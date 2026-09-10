"""订单增强：评价扫词、超时关单、券 SQL 注入。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import attach_accept
from app.bake.engine import count_create_tables, domain_sql
from app.bake.features.loyalty import apply_loyalty_to_spec
from app.bake.features.order_extras import (
    ORDER_REVIEW_CAP,
    apply_order_extras_to_spec,
    order_timeout_minutes,
    scan_order_review,
    scan_order_timeout,
)
from app.bake.sql.fragments import ensure_coupon_lifecycle_sql, ensure_order_review_sql
from tests.helpers.normalize import normalize_sql


class OrderExtrasTests(unittest.TestCase):
    def test_scan_review_and_timeout(self) -> None:
        self.assertTrue(scan_order_review("支持订单评价与星级评价"))
        self.assertTrue(scan_order_review("点餐外卖，评价退单，支付留言"))
        self.assertTrue(scan_order_review("用户评价与售后"))
        self.assertTrue(scan_order_review("买家评价、订单评分"))
        self.assertFalse(scan_order_review("仅购物车与订单"))
        self.assertFalse(scan_order_review("建立评价指标体系"))
        self.assertTrue(scan_order_timeout("未支付超时自动取消订单"))
        self.assertEqual(order_timeout_minutes("支付超时取消", ["order_lines"]), 30)
        self.assertEqual(order_timeout_minutes("", ["order_lines"]), 0)
        self.assertEqual(
            order_timeout_minutes(
                "",
                ["order_lines"],
                schema={"demoPay": True, "shopMarketplace": True},
            ),
            15,
        )

    def test_food_blank_opening_still_has_order_review(self) -> None:
        out = attach_accept(
            {
                "domain": "DOM-FOOD",
                "title": "校园食堂点餐",
                "capabilities": list(
                    c
                    for c in (
                        "archive",
                        "order_lines",
                        "quota",
                        "content",
                        "org_users",
                        "guestbook",
                    )
                ),
                "schema": {},
            },
            "食堂档口点餐与配送。",
        )
        self.assertIn(ORDER_REVIEW_CAP, out.get("capabilities") or [])
        admin = ((out.get("schema") or {}).get("menus") or {}).get("admin") or []
        self.assertTrue(any(m.get("key") == "order_reviews" for m in admin))

    def test_requires_order_lines(self) -> None:
        spec = apply_order_extras_to_spec(
            {"capabilities": ["archive", "ticket_flow"], "schema": {}},
            "订单评价 超时取消",
        )
        self.assertNotIn(ORDER_REVIEW_CAP, spec.get("capabilities") or [])
        self.assertNotIn("orderTimeoutMinutes", (spec.get("schema") or {}))

    def test_attach_accept_merges_review_timeout_coupon(self) -> None:
        out = attach_accept(
            {
                "domain": "DOM-SHOP",
                "capabilities": ["archive", "order_lines", "quota", "content", "org_users"],
                "schema": {"menus": {"user": [{"key": "cart", "label": "购物车"}]}},
            },
            "鲜花商城，优惠券领券，订单评价，支付超时自动取消",
        )
        caps = out.get("capabilities") or []
        self.assertIn("coupon", caps)
        self.assertIn(ORDER_REVIEW_CAP, caps)
        schema = out.get("schema") or {}
        self.assertEqual(schema.get("orderTimeoutMinutes"), 30)
        user = (schema.get("menus") or {}).get("user") or []
        self.assertTrue(any(m.get("key") == "coupons" for m in user))
        self.assertTrue(any(m.get("key") == "order_reviews" for m in user))

    def test_sql_injects_coupon_and_review(self) -> None:
        base = domain_sql("DOM-SHOP", "thesis_shop")
        with_c = ensure_coupon_lifecycle_sql(base, enabled=True)
        with_r = ensure_order_review_sql(with_c, enabled=True)
        n = normalize_sql(with_r)
        self.assertIn("promo_coupon", n)
        self.assertIn("user_coupon", n)
        self.assertIn("order_review", n)
        self.assertLessEqual(count_create_tables(with_r), 15)

    def test_loyalty_coupon_menus(self) -> None:
        spec = apply_loyalty_to_spec(
            {
                "domain": "DOM-GENERIC",
                "capabilities": ["archive", "order_lines", "coupon"],
                "schema": {},
            },
            "",
        )
        menus = (spec.get("schema") or {}).get("menus", {}).get("user") or []
        self.assertTrue(any(m.get("key") == "coupons" for m in menus))


if __name__ == "__main__":
    unittest.main()
