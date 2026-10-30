"""碎另案 i：商城各皮种子须撑起工作台 KPI/趋势（多态订单 + 日期；多店须归属）。"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from app.bake.sql.domain_scene_seed import apply_domain_scene_seed

_SHOP_SQL = Path(__file__).resolve().parents[1] / "app" / "bake" / "sql" / "templates" / "DOM-SHOP.sql"

# (题名, 正文, 是否多店)
_CASES: list[tuple[str, str, bool]] = [
    ("日用百货商城", "购物车下单配送", False),
    ("校园二手交易平台", "校园闲置教材数码自提", False),
    ("文印店在线下单系统", "打印装订耗材到店取", False),
    ("鲜花特产商城", "花束绿植蜂蜜配送", False),
    ("校园跑腿代买系统", "食堂代买宿舍配送", False),
    ("积分兑换商城", "积分兑换文创生活权益", False),
    ("农产品电商系统", "助农生鲜果蔬粮油", False),
    ("多商家入驻农产品电商", "多店入驻助农生鲜果蔬", True),
    ("多商家入驻百货商城", "多店入驻购物车下单", True),
]


class ShopWorkbenchSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = _SHOP_SQL.read_text(encoding="utf-8")

    def _seed(self, title: str, body: str) -> str:
        return apply_domain_scene_seed(
            "DOM-SHOP", self.raw, title=title, proposal_text=body
        )

    def test_each_skin_has_four_order_statuses_and_dates(self) -> None:
        for title, body, _mp in _CASES:
            with self.subTest(title=title):
                sql = self._seed(title, body)
                block = re.search(
                    r"INSERT IGNORE INTO biz_order\b[\s\S]*?;", sql, re.I
                )
                self.assertIsNotNone(block, f"{title}: 缺 biz_order 种子")
                chunk = block.group(0)
                for st in ("pending", "confirmed", "shipped", "completed"):
                    self.assertIn(f"'{st}'", chunk, f"{title}: 缺状态 {st}")
                self.assertIn(
                    "created_at",
                    chunk.lower(),
                    f"{title}: 订单须带 created_at（趋势图）",
                )
                self.assertIn(
                    "DATE_SUB",
                    chunk,
                    f"{title}: 订单日期须散开到近几天",
                )

    def test_marketplace_seeds_bind_owner_and_staff_post(self) -> None:
        for title, body, mp in _CASES:
            if not mp:
                continue
            with self.subTest(title=title):
                sql = self._seed(title, body)
                self.assertIn("owner_username", sql)
                self.assertIn("staff_post='shop_merchant'", sql)
                self.assertIn("'subadmin'", sql)
                self.assertIn("'merchant_b'", sql)


if __name__ == "__main__":
    unittest.main()
