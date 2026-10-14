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
        # 同名兄弟行：购物车「换规格」依赖同 title 多条在售
        self.assertIn("10 斤装", sql)
        self.assertGreaterEqual(sql.count("'红富士苹果'"), 2)
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
        by_key = {f["key"]: f for f in schema["entities"]["archive"]["fields"]}
        self.assertEqual(by_key["harvestOn"]["type"], "date")
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

    def test_all_registry_niches_bake_without_generic_retail(self) -> None:
        """登记表每个 niche：分类+首 SKU+眉标贴题，且不落回百货种子。"""
        from app.bake.engine_sql import domain_sql
        from app.bake.scene_scan import shop_catalog_kind
        from app.bake.shop_retail_niches import all_retail_niche_packs

        # (title hint that hits niche, pack)
        probes = {
            "pharmacy": "校园药店药品零售",
            "pet": "宠物用品在线商城",
            "auto": "汽车配件销售管理",
            "beauty": "化妆品美妆商城",
            "market": "社区超市便利店",
            "office": "办公用品文具商城",
            "agri": "农资肥料销售",
            "gift": "定制礼品刻字商城",
            "fitness": "健身用品电商平台",
            "sports": "体育用品商城系统",
        }
        for pack in all_retail_niche_packs():
            with self.subTest(niche=pack.id):
                title = probes[pack.id]
                self.assertEqual(shop_catalog_kind(title, ""), f"retail_{pack.id}")
                schema = _shop_schema(title, "")
                self.assertEqual(schema["labels"]["authEyebrow"], pack.eyebrow)
                sql = domain_sql("DOM-SHOP", "t", title=title, proposal_text="")
                self.assertIn(pack.categories[0], sql)
                self.assertIn(pack.skus[0][0], sql)
                self.assertNotIn("日用收纳盒", sql)

    def test_builders_slot_forbids_niche_equals(self) -> None:
        """新皮只改登记表：builders_slot 禁止再写 niche ==。"""
        from pathlib import Path

        text = (
            Path(__file__).resolve().parents[1]
            / "app"
            / "bake"
            / "schema"
            / "builders_slot.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn('niche == "', text)
        self.assertNotIn("niche == '", text)

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

    def test_sports_catalog_seed_and_marketplace_skin(self) -> None:
        """体育用品商城：≠ 健身哑铃皮、≠ 器材借用。"""
        from app.bake.engine_sql import domain_sql
        from app.bake.features.ai_assistant import (
            build_ai_knowledge_seed_sql,
            resolve_ai_knowledge_skin,
        )
        from app.bake.scene_scan import shop_catalog_kind, shop_product_kind

        title = "体育用品商城系统"
        body = "浏览球类器材鞋服护具，购物车下单，申请售后"
        self.assertEqual(shop_product_kind(title, body), "retail")
        self.assertEqual(shop_catalog_kind(title, body), "retail_sports")
        schema = _shop_schema(title, body)
        self.assertEqual(schema["labels"]["authEyebrow"], "体育用品")
        self.assertEqual(schema["entities"]["archive"]["label"], "体育用品")

        sql = domain_sql("DOM-SHOP", "t", title=title, proposal_text=body)
        self.assertIn("球类器材", sql)
        self.assertIn("篮球", sql)
        self.assertNotIn("日用收纳盒", sql)
        self.assertNotIn("六角哑铃", sql)

        self.assertEqual(
            resolve_ai_knowledge_skin("DOM-SHOP", title, body),
            "shop_retail_sports",
        )
        faq = build_ai_knowledge_seed_sql("DOM-SHOP", title, body)
        self.assertIn("球类器材", faq)

        mp_body = (
            "用户端、商家端、管理员端。"
            "商家功能模块：店铺信息编辑、体育用品管理、订单发货、售后审核。"
            "管理员：商家管理、体育用品分类、活动审核。"
        )
        mp_schema = _shop_schema(title, mp_body)
        self.assertEqual(mp_schema["labels"]["authEyebrow"], "多商家体育商城")
        mp_sql = domain_sql("DOM-SHOP", "t", title=title, proposal_text=mp_body)
        self.assertIn("球类器材店", mp_sql)

    def test_fitness_catalog_seed_and_marketplace_skin(self) -> None:
        """健身用品电商（≠ SALON 私教）：单店/多店皮与种子贴题。"""
        from app.bake.engine_sql import domain_sql
        from app.bake.features.ai_assistant import (
            build_ai_knowledge_seed_sql,
            resolve_ai_knowledge_skin,
        )
        from app.bake.scene_scan import shop_catalog_kind, shop_product_kind

        title = "方木健身用品电商平台的设计与实现"
        body = "浏览搜索健身用品（哑铃/杠铃/瑜伽垫/弹力带/护具），按增肌减脂塑形康复选购"
        self.assertEqual(shop_product_kind(title, body), "retail")
        self.assertEqual(shop_catalog_kind(title, body), "retail_fitness")
        schema = _shop_schema(title, body)
        self.assertEqual(schema["labels"]["authEyebrow"], "健身用品")
        self.assertEqual(schema["seeds"]["noticeTitle"], "健身选购须知")
        self.assertEqual(schema["entities"]["archive"]["label"], "健身用品")
        fields = {
            f["key"]: f["label"]
            for f in schema["entities"]["archive"]["fields"]
        }
        self.assertEqual(fields["title"], "健身用品名称")
        self.assertEqual(fields["isbn"], "规格型号")

        sql = domain_sql("DOM-SHOP", "t", title=title, proposal_text=body)
        self.assertIn("增肌训练", sql)
        self.assertIn("哑铃", sql)
        self.assertIn("瑜伽垫", sql)
        self.assertNotIn("日用收纳盒", sql)
        self.assertNotIn("红富士苹果", sql)

        self.assertEqual(
            resolve_ai_knowledge_skin("DOM-SHOP", title, body),
            "shop_retail_fitness",
        )
        faq = build_ai_knowledge_seed_sql("DOM-SHOP", title, body)
        self.assertIn("增肌训练", faq)
        self.assertNotIn("配件缺货", faq)

        mp_body = (
            "用户端、商家端、管理员端。"
            "商家功能模块：店铺信息编辑、健身用品管理、订单发货、售后审核。"
            "管理员：商家管理、健身用品分类、活动审核。"
        )
        mp_schema = _shop_schema(title, mp_body)
        self.assertTrue(mp_schema.get("shopMarketplace"))
        self.assertEqual(mp_schema["labels"]["authEyebrow"], "多商家健身商城")
        menus = {
            m.get("key"): m.get("label")
            for m in (mp_schema.get("menus") or {}).get("admin") or []
            if isinstance(m, dict)
        }
        self.assertEqual(menus.get("archive"), "健身用品管理")
        self.assertEqual(menus.get("category"), "健身用品分类")
        self.assertEqual(menus.get("dashboard"), "数据分析")
        self.assertEqual(menus.get("content"), "活动管理")

        mp_sql = domain_sql("DOM-SHOP", "t", title=title, proposal_text=mp_body)
        self.assertIn("力量器材店", mp_sql)
        self.assertIn("塑形家居店", mp_sql)
        self.assertNotIn("方木力量店", mp_sql)
        self.assertIn("六角哑铃", mp_sql)
        self.assertIn("owner_username", mp_sql)
        self.assertNotIn("日用收纳盒", mp_sql)
        self.assertNotIn("烟台果园店", mp_sql)


if __name__ == "__main__":
    unittest.main()
