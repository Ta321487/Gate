"""商城货皮氛围图：农产不得落到鞋服卖场查询/兜底。"""

from __future__ import annotations

import unittest

from app.bake.auth_hero import (
    _SHOP_KIND_AUTH_QUERY,
    _SHOP_KIND_FALLBACK,
    _pick_fallback_id,
    build_query,
)


class AuthHeroShopKindTests(unittest.TestCase):
    def test_farm_query_not_retail_aisle(self) -> None:
        retail = build_query("DOM-SHOP", "shop-leaf")
        farm = build_query("DOM-SHOP", "shop-leaf", catalog_kind="farm")
        self.assertIn("retail", retail.lower())
        self.assertIn("produce", farm.lower())
        self.assertNotIn("retail store", farm.lower())
        self.assertIn("farmers market", farm.lower())

    def test_farm_fallback_differs_from_shop_default(self) -> None:
        shop_id = _pick_fallback_id("DOM-SHOP", "shop-leaf")
        farm_id = _pick_fallback_id("DOM-SHOP", "shop-leaf", catalog_kind="farm")
        self.assertIn(farm_id, _SHOP_KIND_FALLBACK["farm"])
        self.assertNotEqual(farm_id, shop_id)
        self.assertTrue(_SHOP_KIND_AUTH_QUERY["farm"])

    def test_retail_niche_falls_back_to_domain_query(self) -> None:
        q = build_query("DOM-SHOP", "shop-leaf", catalog_kind="retail_pharmacy")
        self.assertIn("retail", q.lower())


if __name__ == "__main__":
    unittest.main()
