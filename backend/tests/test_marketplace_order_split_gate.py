# -*- coding: utf-8 -*-
"""多店跨店合单：骨架须按店拆单 + 商家整单独占才可改态。"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "skeletons" / "baseline" / "backend" / "src" / "main" / "java" / "com" / "thesis"
MYBATIS = (
    ROOT
    / "skeletons"
    / "overlays"
    / "persistence-mybatis"
    / "backend"
    / "src"
    / "main"
    / "java"
    / "com"
    / "thesis"
)
JPA = (
    ROOT
    / "skeletons"
    / "overlays"
    / "persistence-jpa"
    / "backend"
    / "src"
    / "main"
    / "java"
    / "com"
    / "thesis"
)


class MarketplaceOrderSplitGateTests(unittest.TestCase):
    def test_baseline_order_store_splits_and_sole_owner(self) -> None:
        text = (BASELINE / "capability" / "OrderStore.java").read_text(encoding="utf-8")
        self.assertIn("placeOrdersSplitByMerchant", text)
        self.assertIn("merchantSolelyOwnsOrder", text)
        self.assertIn("MARKETPLACE_SPLITTING", text)
        self.assertIn("suppressFulfillmentFees", text)

    def test_baseline_controller_requires_sole_owner(self) -> None:
        text = (BASELINE / "controller" / "OrderController.java").read_text(encoding="utf-8")
        self.assertIn("merchantSolelyOwnsOrder", text)
        self.assertIn("别家店铺的商品", text)

    def test_overlays_order_store_aligned(self) -> None:
        for label, path in (
            ("mybatis", MYBATIS / "capability" / "OrderStore.java"),
            ("jpa", JPA / "capability" / "OrderStore.java"),
        ):
            text = path.read_text(encoding="utf-8")
            self.assertIn("placeOrdersSplitByMerchant", text, msg=label)
            self.assertIn("merchantSolelyOwnsOrder", text, msg=label)

    def test_mybatis_mapper_count_order_lines(self) -> None:
        text = (MYBATIS / "mapper" / "OrderMapper.java").read_text(encoding="utf-8")
        self.assertIn("countOrderLines", text)

    def test_loyalty_peek_offset(self) -> None:
        for path in (
            BASELINE / "capability" / "LoyaltyStore.java",
            MYBATIS / "capability" / "LoyaltyStore.java",
            JPA / "capability" / "LoyaltyStore.java",
        ):
            self.assertIn("peekOffsetPoints", path.read_text(encoding="utf-8"), msg=str(path))


if __name__ == "__main__":
    unittest.main()
