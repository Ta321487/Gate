"""features[].name 近义折叠：同能力只留规范名一条。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.features.feature_names import (
    FEATURE_ALIAS_GROUPS,
    FLASH_PRICE_FEATURE,
    MESSAGE_TEMPLATE_FEATURE,
    ORDER_TIMEOUT_FEATURE,
    REFUND_EXCHANGE_FEATURE,
    STOCK_NOTIFY_FEATURE,
    collapse_feature_aliases,
    ensure_feature,
)


class FeatureNamesCollapseTests(unittest.TestCase):
    def test_collapse_each_alias_group(self) -> None:
        for canon, aliases in FEATURE_ALIAS_GROUPS:
            raw = [{"name": a, "status": "flow"} for a in sorted(aliases)]
            raw.append({"name": "其它功能", "status": "module"})
            out = collapse_feature_aliases(raw)
            names = [f.get("name") for f in out if isinstance(f, dict)]
            self.assertEqual(names.count(canon), 1, msg=canon)
            for a in aliases:
                if a != canon:
                    self.assertNotIn(a, names, msg=f"{canon} still has {a}")
            self.assertIn("其它功能", names)

    def test_ensure_adds_once(self) -> None:
        out = ensure_feature([], ORDER_TIMEOUT_FEATURE, status="module")
        out2 = ensure_feature(out, ORDER_TIMEOUT_FEATURE, status="flow")
        names = [f.get("name") for f in out2 if isinstance(f, dict)]
        self.assertEqual(names, [ORDER_TIMEOUT_FEATURE])

    def test_cinema_timeout_single(self) -> None:
        out = attach_accept(
            {
                "domain": "DOM-CINEMA",
                "title": "潮汐演艺票务销售网站的设计与实现",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-CINEMA"]),
                "features": [],
                "archetype": "ARCH-TRADE",
                "schema": {"demoPay": True, "shopMarketplace": True},
            },
            "可视化选座购票、购物车、支付与电子票、订单超时自动取消。",
        )
        names = [
            f.get("name")
            for f in (out.get("features") or [])
            if isinstance(f, dict)
        ]
        self.assertEqual(names.count(ORDER_TIMEOUT_FEATURE), 1)
        self.assertNotIn("订单超时未付自动取消", names)

    def test_shop_stock_exchange_flash_single(self) -> None:
        out = attach_accept(
            {
                "domain": "DOM-SHOP",
                "title": "校园二手商城",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-SHOP"]) + ["flash_price"],
                "features": [],
                "archetype": "ARCH-TRADE",
                "schema": {"demoPay": True, "shopMarketplace": True},
            },
            "缺货到货通知、商品到货订阅、换货与仅换货、限时购与倒计时展示。",
        )
        names = [
            f.get("name")
            for f in (out.get("features") or [])
            if isinstance(f, dict)
        ]
        self.assertEqual(names.count(STOCK_NOTIFY_FEATURE), 1)
        self.assertNotIn("商品到货订阅", names)
        self.assertEqual(names.count(REFUND_EXCHANGE_FEATURE), 1)
        self.assertNotIn("仅换货不退款", names)
        self.assertEqual(names.count(FLASH_PRICE_FEATURE), 1)
        self.assertNotIn("限时购倒计时展示", names)

    def test_message_template_force_single(self) -> None:
        # 招聘域强制消息模板时不得再挂「站内消息模板」别名
        out = attach_accept(
            {
                "domain": "DOM-RECRUIT",
                "title": "校园招聘系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-RECRUIT"]),
                "features": [],
                "archetype": "ARCH-FOLLOW",
            },
            "录用通知与录用站内信、消息模板维护。",
        )
        names = [
            f.get("name")
            for f in (out.get("features") or [])
            if isinstance(f, dict)
        ]
        self.assertEqual(names.count(MESSAGE_TEMPLATE_FEATURE), 1)
        self.assertNotIn("站内消息模板", names)


if __name__ == "__main__":
    unittest.main()
