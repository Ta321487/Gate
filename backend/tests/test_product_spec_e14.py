"""能力扩岛 E-14：商品规格说明 product_spec（开题扫词才挂，无域默认）。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES
from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.product_spec import (
    PRODUCT_SPEC_CAP,
    merge_product_spec_capabilities,
    scan_product_spec,
    scan_product_spec_matrix_block,
)
from tests.helpers.normalize import normalize_sql

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "skeletons" / "baseline"


class ProductSpecE14Tests(unittest.TestCase):
    def test_capability_registered_no_domain_default(self) -> None:
        self.assertEqual(CAPABILITIES[PRODUCT_SPEC_CAP]["status"], "implemented")
        for dom in ("DOM-SHOP", "DOM-FOOD", "DOM-LIBRARY"):
            self.assertNotIn(PRODUCT_SPEC_CAP, DOMAIN_CAPABILITIES.get(dom) or [], dom)

    def test_scan_terms_and_matrix_block(self) -> None:
        self.assertTrue(scan_product_spec("支持商品规格与产地规格说明。"))
        self.assertTrue(scan_product_spec("填写规格参数。"))
        self.assertFalse(scan_product_spec("购物车下单与库存扣减。"))
        self.assertTrue(scan_product_spec_matrix_block("支持多规格库存与色码矩阵。"))
        self.assertFalse(scan_product_spec("开题写完整多规格 SKU 独立库存。"))

    def test_merge_only_when_scanned_on_order_domain(self) -> None:
        base = list(DOMAIN_CAPABILITIES["DOM-SHOP"])
        self.assertIn("order_lines", base)
        no = merge_product_spec_capabilities(base, "购物车下单支付。", domain="DOM-SHOP")
        self.assertNotIn(PRODUCT_SPEC_CAP, no)
        yes = merge_product_spec_capabilities(
            base, "商品浏览；规格参数可填写。", domain="DOM-SHOP"
        )
        self.assertIn(PRODUCT_SPEC_CAP, yes)
        blocked = merge_product_spec_capabilities(
            base, "支持多规格库存与每规格独立库存。", domain="DOM-SHOP"
        )
        self.assertNotIn(PRODUCT_SPEC_CAP, blocked)
        lib = merge_product_spec_capabilities(
            list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
            "图书规格？",
            domain="DOM-LIBRARY",
        )
        self.assertNotIn(PRODUCT_SPEC_CAP, lib)

    def test_attach_accept_sql_yml_fields(self) -> None:
        plain = attach_accept(
            {
                "domain": "DOM-SHOP",
                "title": "校园二手商城",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-SHOP"]),
                "archetype": "ARCH-TRADE",
            },
            "商品浏览、购物车、下单、支付。",
        )
        self.assertNotIn(PRODUCT_SPEC_CAP, plain.get("capabilities") or [])
        arch0 = ((plain.get("schema") or {}).get("entities") or {}).get("archive") or {}
        keys0 = {f.get("key") for f in (arch0.get("fields") or []) if isinstance(f, dict)}
        self.assertNotIn("specNote", keys0)
        self.assertFalse(bool(arch0.get("productSpecEnabled")))

        rich = attach_accept(
            {
                "domain": "DOM-SHOP",
                "title": "校园二手商城",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-SHOP"]),
                "archetype": "ARCH-TRADE",
            },
            "商品浏览购物车；支持规格参数与产地规格说明。",
        )
        caps = rich.get("capabilities") or []
        self.assertIn(PRODUCT_SPEC_CAP, caps)
        arch = ((rich.get("schema") or {}).get("entities") or {}).get("archive") or {}
        keys = {f.get("key") for f in (arch.get("fields") or []) if isinstance(f, dict)}
        self.assertIn("specNote", keys)
        self.assertTrue(bool(arch.get("productSpecEnabled")))
        self.assertEqual(arch.get("productSpecSource"), "specNote")
        labels = (rich.get("schema") or {}).get("labels") or {}
        self.assertEqual(labels.get("productSpecLabel"), "规格")
        hint = str(labels.get("productSpecHint") or "")
        self.assertNotIn("演示", hint)
        self.assertIn("矩阵", hint)

        food = attach_accept(
            {
                "domain": "DOM-FOOD",
                "title": "农产品商城",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-FOOD"]),
                "archetype": "ARCH-TRADE",
            },
            "货架浏览下单；商品规格说明。",
        )
        if PRODUCT_SPEC_CAP in (food.get("capabilities") or []):
            farch = ((food.get("schema") or {}).get("entities") or {}).get("archive") or {}
            self.assertEqual(farch.get("productSpecSource"), "isbn")

        gate = rich.get("gate") or {}
        self.assertIn("product_spec", (gate.get("flow_api") or {}))

        yml = _patch_thesis_yml("thesis:\n  domain: DOM-SHOP\n", "DOM-SHOP", rich)
        self.assertIn("product-spec-enabled: true", yml)

        sql = domain_sql(
            "DOM-SHOP",
            "thesis_shop",
            capabilities=caps,
            proposal_text="商品浏览购物车；支持规格参数与产地规格说明。",
        )
        n = normalize_sql(sql)
        self.assertIn("spec_note", n)

    def test_unmounted_sql_no_forced_spec_ui(self) -> None:
        plain = attach_accept(
            {
                "domain": "DOM-SHOP",
                "title": "校园二手商城",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-SHOP"]),
                "archetype": "ARCH-TRADE",
            },
            "商品浏览、购物车、下单。",
        )
        domain_sql(
            "DOM-SHOP",
            "thesis_shop",
            capabilities=plain.get("capabilities") or [],
            proposal_text="商品浏览、购物车、下单。",
        )
        arch = ((plain.get("schema") or {}).get("entities") or {}).get("archive") or {}
        self.assertFalse(bool(arch.get("productSpecEnabled")))
        self.assertNotIn(PRODUCT_SPEC_CAP, plain.get("capabilities") or [])

    def test_baseline_runtime_and_fe(self) -> None:
        store = (
            BASELINE
            / "backend/src/main/java/com/thesis/capability/ArchiveStore.java"
        ).read_text(encoding="utf-8")
        self.assertIn("configureProductSpec", store)
        self.assertIn("productSpecText", store)
        self.assertIn("lineTitleWithSpec", store)
        self.assertIn("specNote", store)
        order = (
            BASELINE
            / "backend/src/main/java/com/thesis/capability/OrderStore.java"
        ).read_text(encoding="utf-8")
        self.assertIn("lineTitleWithSpec", order)
        binder = (
            BASELINE
            / "backend/src/main/java/com/thesis/config/DomainRuntimeBinder.java"
        ).read_text(encoding="utf-8")
        self.assertIn("product-spec-enabled", binder)
        self.assertIn("configureProductSpec", binder)
        fe = (
            BASELINE / "frontend/src/views/user/ArchiveBrowse.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("product_spec", fe)
        self.assertIn("productSpecText", fe)
        self.assertIn("productSpecLabel", fe)


if __name__ == "__main__":
    unittest.main()
