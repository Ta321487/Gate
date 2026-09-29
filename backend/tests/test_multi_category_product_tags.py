"""多维分类 multi_category + 商品标签 product_tags：开题扫词才挂；SHOP/FOOD/CINEMA。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES
from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.detail_attrs import DETAIL_ATTRS_CAP, parse_detail_labels
from app.bake.features.multi_category import (
    MULTI_CATEGORY_CAP,
    merge_multi_category_capabilities,
    parse_category_axes,
    scan_multi_category,
)
from app.bake.features.order_extras import FLASH_PRICE_CAP, scan_flash_price
from app.bake.features.product_tags import (
    PRODUCT_TAGS_CAP,
    merge_product_tags_capabilities,
    scan_product_tags,
)
from tests.helpers.normalize import normalize_sql

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "skeletons" / "baseline"

_SHOP_CAPS = list(DOMAIN_CAPABILITIES["DOM-SHOP"])
_MULTI_TEXT = "按用途分类、按目标分类，支持多条件筛选。"
_TAG_TEXT = "商品支持标签筛选与标签云展示。"
_BOTH_TEXT = "按用途分类与按材质分类；商品标签含热门与新品。"
_PLAIN_TEXT = "商品浏览、购物车、下单支付。"
_FOOD_ACCEPT = (
    "菜品按口味和荤素分类；详情显示辣度、份量、食材；限时折扣；热门菜品标签"
)
_CINEMA_ACCEPT = (
    "影片按类型和评分分类；详情显示多个属性字段；早鸟票；热映标签"
)


class MultiCategoryProductTagsTests(unittest.TestCase):
    def test_capabilities_registered_no_domain_default(self) -> None:
        self.assertEqual(CAPABILITIES[MULTI_CATEGORY_CAP]["status"], "implemented")
        self.assertEqual(CAPABILITIES[PRODUCT_TAGS_CAP]["status"], "implemented")
        for dom in ("DOM-SHOP", "DOM-FOOD", "DOM-FORUM", "DOM-LIBRARY"):
            caps = DOMAIN_CAPABILITIES.get(dom) or []
            self.assertNotIn(MULTI_CATEGORY_CAP, caps, dom)
            self.assertNotIn(PRODUCT_TAGS_CAP, caps, dom)

    def test_scan_multi_category(self) -> None:
        self.assertTrue(scan_multi_category(_MULTI_TEXT))
        self.assertTrue(scan_multi_category("支持按品牌分类和按场景分类。"))
        self.assertTrue(scan_multi_category("多维分类与多条件筛选。"))
        self.assertTrue(scan_multi_category("菜品按口味和荤素分类"))
        self.assertTrue(scan_multi_category("影片按类型和评分分类"))
        self.assertTrue(scan_multi_category("按多个维度对菜品分类"))
        self.assertFalse(scan_multi_category("分类浏览商品，热销日用配件。"))
        self.assertFalse(scan_multi_category(_PLAIN_TEXT))

    def test_scan_product_tags_requires_label_word(self) -> None:
        self.assertTrue(scan_product_tags(_TAG_TEXT))
        self.assertTrue(scan_product_tags("支持商品标签：包邮、自营。"))
        self.assertTrue(scan_product_tags("热门菜品标签"))
        self.assertTrue(scan_product_tags("热映标签"))
        self.assertFalse(scan_product_tags("全场包邮、自营发货、热门新品推荐。"))
        self.assertFalse(scan_product_tags(_PLAIN_TEXT))

    def test_merge_trade_domains(self) -> None:
        yes = merge_multi_category_capabilities(_SHOP_CAPS, _MULTI_TEXT, domain="DOM-SHOP")
        self.assertIn(MULTI_CATEGORY_CAP, yes)
        no = merge_multi_category_capabilities(_SHOP_CAPS, _PLAIN_TEXT, domain="DOM-SHOP")
        self.assertNotIn(MULTI_CATEGORY_CAP, no)
        food = merge_multi_category_capabilities(
            list(DOMAIN_CAPABILITIES["DOM-FOOD"]), _MULTI_TEXT, domain="DOM-FOOD"
        )
        self.assertIn(MULTI_CATEGORY_CAP, food)
        cinema = merge_multi_category_capabilities(
            list(DOMAIN_CAPABILITIES["DOM-CINEMA"]),
            "影片按类型和评分分类",
            domain="DOM-CINEMA",
        )
        self.assertIn(MULTI_CATEGORY_CAP, cinema)
        library = merge_multi_category_capabilities(
            list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]), _MULTI_TEXT, domain="DOM-LIBRARY"
        )
        self.assertNotIn(MULTI_CATEGORY_CAP, library)

        tags = merge_product_tags_capabilities(_SHOP_CAPS, _TAG_TEXT, domain="DOM-SHOP")
        self.assertIn(PRODUCT_TAGS_CAP, tags)
        food_tags = merge_product_tags_capabilities(
            list(DOMAIN_CAPABILITIES["DOM-FOOD"]), "热门菜品标签", domain="DOM-FOOD"
        )
        self.assertIn(PRODUCT_TAGS_CAP, food_tags)
        forum = merge_product_tags_capabilities(
            list(DOMAIN_CAPABILITIES["DOM-FORUM"]), "帖子标签筛选。", domain="DOM-FORUM"
        )
        self.assertNotIn(PRODUCT_TAGS_CAP, forum)

    def test_dual_hit_both_caps(self) -> None:
        both = merge_multi_category_capabilities(_SHOP_CAPS, _BOTH_TEXT, domain="DOM-SHOP")
        both = merge_product_tags_capabilities(both, _BOTH_TEXT, domain="DOM-SHOP")
        self.assertIn(MULTI_CATEGORY_CAP, both)
        self.assertIn(PRODUCT_TAGS_CAP, both)

    def test_unmounted_keeps_single_fk_sql(self) -> None:
        plain = attach_accept(
            {
                "domain": "DOM-SHOP",
                "title": "校园二手商城",
                "capabilities": _SHOP_CAPS,
                "archetype": "ARCH-TRADE",
            },
            _PLAIN_TEXT,
        )
        caps = plain.get("capabilities") or []
        self.assertNotIn(MULTI_CATEGORY_CAP, caps)
        self.assertNotIn(PRODUCT_TAGS_CAP, caps)
        arch = ((plain.get("schema") or {}).get("entities") or {}).get("archive") or {}
        self.assertFalse(bool(arch.get("multiCategory")))
        self.assertFalse(bool(arch.get("tagFilter")))

        sql = domain_sql(
            "DOM-SHOP",
            "thesis_shop",
            capabilities=caps,
            proposal_text=_PLAIN_TEXT,
        )
        n = normalize_sql(sql)
        self.assertNotIn("product_category", n)
        self.assertNotIn("product_tag", n)
        self.assertIn("category_id", n)
        self.assertNotIn("dimension", n)

    def test_mounted_multi_category_sql_and_schema(self) -> None:
        rich = attach_accept(
            {
                "domain": "DOM-SHOP",
                "title": "健身器材商城",
                "capabilities": _SHOP_CAPS,
                "archetype": "ARCH-TRADE",
            },
            _MULTI_TEXT,
        )
        caps = rich.get("capabilities") or []
        self.assertIn(MULTI_CATEGORY_CAP, caps)
        arch = ((rich.get("schema") or {}).get("entities") or {}).get("archive") or {}
        self.assertTrue(bool(arch.get("multiCategory")))
        keys = {f.get("key") for f in (arch.get("fields") or []) if isinstance(f, dict)}
        self.assertIn("categoryIds", keys)
        self.assertNotIn("category", keys)
        self.assertEqual(
            (rich.get("runtime") or {}).get("archive_item_category_table"),
            "product_category",
        )

        yml = _patch_thesis_yml("thesis:\n  domain: DOM-SHOP\n", "DOM-SHOP", rich)
        self.assertIn("multi-category-enabled: true", yml)
        self.assertIn("archive-item-category-table: product_category", yml)

        sql = domain_sql(
            "DOM-SHOP",
            "thesis_shop",
            capabilities=caps,
            proposal_text=_MULTI_TEXT,
        )
        n = normalize_sql(sql)
        self.assertIn("product_category", n)
        self.assertIn("dimension", n)
        self.assertIn("category_id", n)

    def test_mounted_product_tags_sql_and_schema(self) -> None:
        rich = attach_accept(
            {
                "domain": "DOM-SHOP",
                "title": "校园二手商城",
                "capabilities": _SHOP_CAPS,
                "archetype": "ARCH-TRADE",
            },
            _TAG_TEXT,
        )
        caps = rich.get("capabilities") or []
        self.assertIn(PRODUCT_TAGS_CAP, caps)
        arch = ((rich.get("schema") or {}).get("entities") or {}).get("archive") or {}
        self.assertTrue(bool(arch.get("tagFilter")))
        rt = rich.get("runtime") or {}
        self.assertEqual(rt.get("archive_tag_table"), "tag")
        self.assertEqual(rt.get("archive_item_tag_table"), "product_tag")

        yml = _patch_thesis_yml("thesis:\n  domain: DOM-SHOP\n", "DOM-SHOP", rich)
        self.assertIn("archive-tag-table: tag", yml)
        self.assertIn("archive-item-tag-table: product_tag", yml)

        sql = domain_sql(
            "DOM-SHOP",
            "thesis_shop",
            capabilities=caps,
            proposal_text=_TAG_TEXT,
        )
        n = normalize_sql(sql).lower()
        self.assertIn("product_tag", n)
        self.assertIn("create table if not exists tag", n)

    def test_baseline_runtime_and_fe(self) -> None:
        store = (
            BASELINE / "backend/src/main/java/com/thesis/capability/ArchiveStore.java"
        ).read_text(encoding="utf-8")
        self.assertIn("configureMultiCategory", store)
        self.assertIn("bindItemCategories", store)
        self.assertIn("syncItemCategories", store)
        self.assertIn("multiCategoryActive", store)

        binder = (
            BASELINE / "backend/src/main/java/com/thesis/config/DomainRuntimeBinder.java"
        ).read_text(encoding="utf-8")
        self.assertIn("multi-category-enabled", binder)
        self.assertIn("archive-item-category-table", binder)
        self.assertIn("configureMultiCategory", binder)

        browse = (BASELINE / "frontend/src/views/user/ArchiveBrowse.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn("multiCategory", browse)
        self.assertIn("categoryIds", browse)
        self.assertIn("tagNames", browse)

        admin = (BASELINE / "frontend/src/views/admin/ArchiveAdmin.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn("multiCategory", admin)
        self.assertIn("categoryIds", admin)

        cats = (BASELINE / "frontend/src/views/admin/CategoriesAdmin.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn("dimension", cats)
        self.assertIn("multiCategory", cats)

    def test_dual_axis_values_and_detail_attrs(self) -> None:
        text = (
            "茶叶零售管理系统。浏览搜索（按香型：花香/果香/焙火；按茶类：绿茶/红茶/乌龙）。"
            "查看商品详情（品牌、香型、净含量、适用人群、价格、简介、图片）。"
            "活动模块查看促销信息、节日优惠。"
            "留言反馈模块（与管理员沟通）。"
            "分类双维度。"
        )
        self.assertTrue(scan_multi_category(text))
        self.assertIn("品牌", parse_detail_labels(text))
        self.assertNotIn("价格", parse_detail_labels(text))
        spec = attach_accept(
            {
                "domain": "DOM-SHOP",
                "title": "茶叶零售",
                "capabilities": _SHOP_CAPS,
                "archetype": "ARCH-TRADE",
            },
            text,
        )
        caps = spec.get("capabilities") or []
        self.assertIn(MULTI_CATEGORY_CAP, caps)
        self.assertIn("detail_attrs", caps)
        self.assertIn("flash_price", caps)
        self.assertIn("dm", caps)
        fields = (
            ((spec.get("schema") or {}).get("entities") or {}).get("archive") or {}
        ).get("fields") or []
        labels = [f.get("label") for f in fields if isinstance(f, dict)]
        self.assertIn("品牌", labels)
        self.assertIn("净含量", labels)
        self.assertIn("适用人群", labels)
        yml = _patch_thesis_yml("thesis:\n  domain: DOM-SHOP\n", "DOM-SHOP", spec)
        self.assertIn("detail-attrs-enabled: true", yml)
        self.assertIn("brand", yml)
        sql = domain_sql(
            "DOM-SHOP",
            "thesis_shop",
            capabilities=caps,
            proposal_text=text,
            title="茶叶零售",
        )
        n = normalize_sql(sql)
        self.assertIn("花香", n)
        self.assertIn("绿茶", n)
        self.assertIn("brand", n)
        self.assertIn("net_content", n)
        self.assertIn("audience", n)
        self.assertNotIn("detail_json", n)
        self.assertNotIn("'自用'", n)

    def test_food_accept_opening_hangs_four(self) -> None:
        self.assertTrue(scan_multi_category(_FOOD_ACCEPT))
        self.assertEqual(
            {"辣度", "份量", "食材"}, set(parse_detail_labels(_FOOD_ACCEPT))
        )
        self.assertTrue(scan_flash_price(_FOOD_ACCEPT))
        self.assertTrue(scan_product_tags(_FOOD_ACCEPT))
        axes = parse_category_axes(_FOOD_ACCEPT)
        self.assertGreaterEqual(len(axes), 2)
        spec = attach_accept(
            {
                "domain": "DOM-FOOD",
                "title": "校园食堂点餐系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-FOOD"]),
                "archetype": "ARCH-TRADE",
            },
            _FOOD_ACCEPT,
        )
        caps = spec.get("capabilities") or []
        for want in (
            MULTI_CATEGORY_CAP,
            DETAIL_ATTRS_CAP,
            FLASH_PRICE_CAP,
            PRODUCT_TAGS_CAP,
        ):
            self.assertIn(want, caps, want)
        arch = ((spec.get("schema") or {}).get("entities") or {}).get("archive") or {}
        self.assertTrue(arch.get("multiCategory"))
        self.assertTrue(arch.get("flashPriceEnabled"))
        self.assertTrue(arch.get("tagFilter"))
        labels = {
            f.get("label") for f in (arch.get("fields") or []) if isinstance(f, dict)
        }
        self.assertIn("份量", labels)
        self.assertIn("食材", labels)
        sql = domain_sql(
            "DOM-FOOD",
            "thesis_food",
            capabilities=caps,
            proposal_text=_FOOD_ACCEPT,
            title="校园食堂点餐系统",
        )
        n = normalize_sql(sql)
        self.assertIn("product_category", n)
        self.assertIn("dimension", n)
        self.assertIn("portion_size", n)
        self.assertIn("ingredients", n)
        self.assertRegex(n, r"portion_size\s+DECIMAL\s*\(\s*10\s*,\s*2\s*\)")
        self.assertRegex(n, r"ingredients\s+VARCHAR\s*\(\s*80\s*\)")
        self.assertNotIn("detail_json", n)
        self.assertIn("promo_price", n)
        self.assertIn("product_tag", n)

    def test_cinema_accept_opening_hangs_four(self) -> None:
        """影院：多维/详情属性/限时/标签均可挂。"""
        self.assertTrue(scan_multi_category(_CINEMA_ACCEPT))
        self.assertTrue(scan_flash_price(_CINEMA_ACCEPT))
        self.assertTrue(scan_product_tags(_CINEMA_ACCEPT))
        spec = attach_accept(
            {
                "domain": "DOM-CINEMA",
                "title": "影院选座购票系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-CINEMA"]),
                "archetype": "ARCH-TRADE",
            },
            _CINEMA_ACCEPT,
        )
        caps = spec.get("capabilities") or []
        for want in (
            MULTI_CATEGORY_CAP,
            DETAIL_ATTRS_CAP,
            FLASH_PRICE_CAP,
            PRODUCT_TAGS_CAP,
        ):
            self.assertIn(want, caps, want)
        arch = ((spec.get("schema") or {}).get("entities") or {}).get("archive") or {}
        self.assertTrue(arch.get("multiCategory"))
        self.assertTrue(arch.get("flashPriceEnabled"))
        self.assertTrue(arch.get("tagFilter"))
        # 「详情显示多个属性字段」开岛；具体导演/主演等看开题再补字段
        self.assertIn("detailAttrKeys", (spec.get("schema") or {}))
        sql = domain_sql(
            "DOM-CINEMA",
            "thesis_cinema",
            capabilities=caps,
            proposal_text=_CINEMA_ACCEPT,
            title="影院选座购票系统",
        )
        n = normalize_sql(sql)
        self.assertIn("product_category", n)
        self.assertIn("promo_price", n)
        self.assertIn("product_tag", n)
        # 仅话术开岛、无具名属性 → 不加 detail_json，也不硬补列
        self.assertNotIn("detail_json", n)

    def test_cinema_named_detail_attrs_fields(self) -> None:
        text = "影片详情显示导演、主演、时长；早鸟票。"
        labels = parse_detail_labels(text)
        self.assertEqual({"导演", "主演", "时长"}, set(labels))
        spec = attach_accept(
            {
                "domain": "DOM-CINEMA",
                "title": "影院选座购票系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-CINEMA"]),
                "archetype": "ARCH-TRADE",
            },
            text,
        )
        self.assertIn(DETAIL_ATTRS_CAP, spec.get("capabilities") or [])
        fields = (
            ((spec.get("schema") or {}).get("entities") or {}).get("archive") or {}
        ).get("fields") or []
        have = {f.get("label") for f in fields if isinstance(f, dict)}
        self.assertTrue({"导演", "主演", "时长"}.issubset(have))
        sql = domain_sql(
            "DOM-CINEMA",
            "thesis_cinema",
            capabilities=spec.get("capabilities") or [],
            proposal_text=text,
            title="影院选座购票系统",
        )
        n = normalize_sql(sql)
        self.assertIn("director", n)
        self.assertIn("cast_names", n)
        self.assertIn("duration_min", n)
        self.assertRegex(n, r"duration_min\s+DECIMAL\s*\(\s*10\s*,\s*2\s*\)")
        self.assertRegex(n, r"director\s+VARCHAR\s*\(\s*80\s*\)")
        self.assertNotIn("detail_json", n)


if __name__ == "__main__":
    unittest.main()
