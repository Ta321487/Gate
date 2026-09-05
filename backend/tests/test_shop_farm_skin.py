"""农产品（shop_product_kind=farm）皮与种子：勿落成零售日用或「履约」空壳文案。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.schema.builders_slot import _shop_schema
from app.bake.scene_scan import shop_product_kind
from app.bake.sql.domain_scene_seed import apply_domain_scene_seed

_SHOP_SQL = Path(__file__).resolve().parents[1] / "app" / "bake" / "sql" / "templates" / "DOM-SHOP.sql"


class ShopFarmSkinTests(unittest.TestCase):
    def test_kind_and_eyebrow(self) -> None:
        title = "基于 Spring Boot 与 Vue 的农产品电商系统"
        body = "助农生鲜果蔬粮油选购"
        self.assertEqual(shop_product_kind(title, body), "farm")
        schema = _shop_schema(title, body)
        self.assertEqual(schema["labels"]["authEyebrow"], "助农商城")
        self.assertEqual(schema["seeds"]["noticeTitle"], "农产选购须知")
        self.assertIn("水果蔬菜粮油", schema["seeds"]["noticeBody"])
        states = schema["entities"]["order"]["states"]
        self.assertEqual(states.get("shipped"), "配送中")

    def test_farm_seed_not_retail(self) -> None:
        raw = _SHOP_SQL.read_text(encoding="utf-8")
        sql = apply_domain_scene_seed(
            "DOM-SHOP",
            raw,
            title="农产品电商",
            proposal_text="助农生鲜果蔬粮油",
        )
        self.assertIn("红富士苹果", sql)
        self.assertIn("水果", sql)
        self.assertIn("脆甜多汁", sql)
        self.assertIn("seller_note", sql)
        self.assertIn("'shipped'", sql)
        self.assertNotIn("日用收纳盒", sql)
        self.assertNotIn("'热销'", sql)
        self.assertNotIn("康乃馨", sql)
        self.assertNotIn("食堂代买套餐", sql)
        self.assertNotIn("黑白打印", sql)


if __name__ == "__main__":
    unittest.main()
