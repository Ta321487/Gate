"""能力扩岛 E-05：限时购 flash_price（开题扫词才挂，无域默认）。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES
from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.order_extras import (
    FLASH_PRICE_CAP,
    merge_order_extras_capabilities,
    scan_flash_price,
)
from tests.helpers.normalize import normalize_sql

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "skeletons" / "baseline"


class FlashPriceE05Tests(unittest.TestCase):
    def test_capability_registered_no_domain_default(self) -> None:
        self.assertEqual(CAPABILITIES[FLASH_PRICE_CAP]["status"], "implemented")
        for dom in ("DOM-SHOP", "DOM-FOOD", "DOM-LIBRARY"):
            self.assertNotIn(FLASH_PRICE_CAP, DOMAIN_CAPABILITIES.get(dom) or [], dom)

    def test_scan_terms(self) -> None:
        self.assertTrue(scan_flash_price("支持限时购与活动价。"))
        self.assertTrue(scan_flash_price("限时特价窗口。"))
        self.assertTrue(scan_flash_price("开题写秒杀（时段特价）。"))
        self.assertFalse(scan_flash_price("购物车下单与库存扣减。"))

    def test_merge_only_when_scanned_on_order_domain(self) -> None:
        base = list(DOMAIN_CAPABILITIES["DOM-SHOP"])
        self.assertIn("order_lines", base)
        no = merge_order_extras_capabilities(base, "购物车下单支付。", domain="DOM-SHOP")
        self.assertNotIn(FLASH_PRICE_CAP, no)
        yes = merge_order_extras_capabilities(
            base, "商城支持限时购活动价。", domain="DOM-SHOP"
        )
        self.assertIn(FLASH_PRICE_CAP, yes)
        # 无订单壳不挂
        lib = merge_order_extras_capabilities(
            list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
            "图书限时购？",
            domain="DOM-LIBRARY",
        )
        self.assertNotIn(FLASH_PRICE_CAP, lib)

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
        self.assertNotIn(FLASH_PRICE_CAP, plain.get("capabilities") or [])
        arch0 = ((plain.get("schema") or {}).get("entities") or {}).get("archive") or {}
        keys0 = {f.get("key") for f in (arch0.get("fields") or []) if isinstance(f, dict)}
        self.assertNotIn("promoPrice", keys0)

        rich = attach_accept(
            {
                "domain": "DOM-SHOP",
                "title": "校园二手商城",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-SHOP"]),
                "archetype": "ARCH-TRADE",
            },
            "商品浏览购物车；支持限时购与活动价窗口。",
        )
        caps = rich.get("capabilities") or []
        self.assertIn(FLASH_PRICE_CAP, caps)
        arch = ((rich.get("schema") or {}).get("entities") or {}).get("archive") or {}
        keys = {f.get("key") for f in (arch.get("fields") or []) if isinstance(f, dict)}
        self.assertIn("promoPrice", keys)
        self.assertIn("promoStart", keys)
        self.assertIn("promoEnd", keys)
        self.assertTrue(bool(arch.get("flashPriceEnabled")))
        labels = (rich.get("schema") or {}).get("labels") or {}
        self.assertIn("活动价", str(labels.get("flashPriceBadge") or "活动价"))
        hint = str(labels.get("flashPriceHint") or "")
        self.assertNotIn("演示", hint)
        self.assertNotIn("秒杀引擎", hint)

        gate = rich.get("gate") or {}
        self.assertIn("flash_price", (gate.get("flow_api") or {}))

        yml = _patch_thesis_yml("thesis:\n  domain: DOM-SHOP\n", "DOM-SHOP", rich)
        self.assertIn("flash-price-enabled: true", yml)

        sql = domain_sql(
            "DOM-SHOP",
            "thesis_shop",
            capabilities=caps,
            proposal_text="商品浏览购物车；支持限时购与活动价窗口。",
        )
        n = normalize_sql(sql)
        self.assertIn("promo_price", n)
        self.assertIn("promo_start", n)
        self.assertIn("promo_end", n)

    def test_unmounted_sql_no_promo_columns(self) -> None:
        plain = attach_accept(
            {
                "domain": "DOM-SHOP",
                "title": "校园二手商城",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-SHOP"]),
                "archetype": "ARCH-TRADE",
            },
            "商品浏览、购物车、下单。",
        )
        sql = domain_sql(
            "DOM-SHOP",
            "thesis_shop",
            capabilities=plain.get("capabilities") or [],
            proposal_text="商品浏览、购物车、下单。",
        )
        n = normalize_sql(sql)
        self.assertNotIn("promo_price", n)
        self.assertNotIn("promo_start", n)

    def test_baseline_effective_price_and_fe(self) -> None:
        store = (
            BASELINE
            / "backend/src/main/java/com/thesis/capability/ArchiveStore.java"
        ).read_text(encoding="utf-8")
        self.assertIn("configureFlashPrice", store)
        self.assertIn("effectiveUnitPrice", store)
        self.assertIn("isPromoActive", store)
        self.assertIn("promoActive", store)
        order = (
            BASELINE
            / "backend/src/main/java/com/thesis/capability/OrderStore.java"
        ).read_text(encoding="utf-8")
        self.assertIn("effectiveUnitPrice", order)
        binder = (
            BASELINE
            / "backend/src/main/java/com/thesis/config/DomainRuntimeBinder.java"
        ).read_text(encoding="utf-8")
        self.assertIn("flash-price-enabled", binder)
        fe = (
            BASELINE / "frontend/src/views/user/ArchiveBrowse.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("flash_price", fe)
        self.assertIn("promoActive", fe)
        self.assertIn("flashBadge", fe)


if __name__ == "__main__":
    unittest.main()
