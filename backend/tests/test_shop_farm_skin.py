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
        self.assertIn("region", sql)
        self.assertIn("harvest_on", sql)
        self.assertIn("山东烟台", sql)
        self.assertIn("5 斤装", sql)
        self.assertIn("'shipped'", sql)
        self.assertNotIn("日用收纳盒", sql)
        self.assertNotIn("'热销'", sql)
        self.assertNotIn("康乃馨", sql)
        self.assertNotIn("食堂代买套餐", sql)
        self.assertNotIn("黑白打印", sql)

    def test_farm_field_labels_match_opening_semantics(self) -> None:
        schema = _shop_schema("XX农产品销售网站", "产地采摘时间规格价格简介")
        fields = {
            f["key"]: f["label"]
            for f in schema["entities"]["archive"]["fields"]
        }
        self.assertEqual(fields["title"], "农产品名称")
        self.assertEqual(fields["author"], "价格")
        self.assertEqual(fields["isbn"], "规格")
        self.assertEqual(fields["region"], "产地")
        self.assertEqual(fields["harvestOn"], "采摘时间")
        self.assertEqual(fields["sellerNote"], "简介")
        self.assertEqual(schema["entities"]["archive"]["label"], "农产品")
        self.assertEqual(schema["roles"]["admin"]["label"], "农产主管（总管）")

    def test_retail_not_injected_farm_columns(self) -> None:
        raw = _SHOP_SQL.read_text(encoding="utf-8")
        sql = apply_domain_scene_seed(
            "DOM-SHOP",
            raw,
            title="日用百货商城",
            proposal_text="购物车下单",
        )
        # CREATE product 不得被农产列污染
        m = __import__("re").search(
            r"CREATE TABLE IF NOT EXISTS\s+product\s*\((.*?)\n\s*created_at\b",
            sql,
            __import__("re").I | __import__("re").S,
        )
        self.assertIsNotNone(m)
        body = m.group(1)
        self.assertNotIn("harvest_on", body)
        self.assertNotIn("region VARCHAR", body)


class ShopRetailNicheTests(unittest.TestCase):
    """零售软皮：一次 bake 分类/SKU/FAQ/eyebrow 贴题，能力仍为购物车商城。"""

    def test_pharmacy_catalog_and_seed(self) -> None:
        from app.bake.engine_sql import domain_sql
        from app.bake.features.ai_assistant import (
            build_ai_knowledge_seed_sql,
            resolve_ai_knowledge_skin,
        )
        from app.bake.scene_scan import shop_catalog_kind, shop_product_kind
        from app.bake.schema.builders_slot import _shop_schema

        title = "校园药店药品零售管理系统"
        body = "OTC 药品与保健护理上架"
        self.assertEqual(shop_product_kind(title, body), "retail")
        self.assertEqual(shop_catalog_kind(title, body), "retail_pharmacy")
        schema = _shop_schema(title, body)
        self.assertEqual(schema["labels"]["authEyebrow"], "药店选购")
        sql = domain_sql("DOM-SHOP", "t", title=title, proposal_text=body)
        self.assertIn("药品", sql)
        self.assertIn("感冒药", sql)
        self.assertNotIn("日用收纳盒", sql)
        self.assertNotIn("'配件'", sql)
        self.assertEqual(
            resolve_ai_knowledge_skin("DOM-SHOP", title, body),
            "shop_retail_pharmacy",
        )
        faq = build_ai_knowledge_seed_sql("DOM-SHOP", title, body)
        self.assertIn("药品", faq)
        self.assertNotIn("配件缺货", faq)

    def test_pet_and_auto_niches(self) -> None:
        from app.bake.engine_sql import domain_sql
        from app.bake.scene_scan import shop_catalog_kind

        self.assertEqual(
            shop_catalog_kind("宠物用品在线商城", "宠粮洗护"),
            "retail_pet",
        )
        pet_sql = domain_sql(
            "DOM-SHOP", "t", title="宠物用品在线商城", proposal_text="宠粮洗护"
        )
        self.assertIn("主粮", pet_sql)
        self.assertIn("猫粮", pet_sql)
        self.assertEqual(
            shop_catalog_kind("汽车配件销售管理系统", ""),
            "retail_auto",
        )
        auto_sql = domain_sql(
            "DOM-SHOP", "t", title="汽车配件销售管理系统", proposal_text=""
        )
        self.assertIn("保养件", auto_sql)
        self.assertIn("机油", auto_sql)


if __name__ == "__main__":
    unittest.main()
