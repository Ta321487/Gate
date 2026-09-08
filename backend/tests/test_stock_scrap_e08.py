"""能力扩岛 E-08：报废 stock_scrap / 盘点 stock_count（开题扫词才挂，无域默认）。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES
from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.features.stock_scrap import (
    STOCK_COUNT_CAP,
    STOCK_IO_CAP,
    STOCK_SCRAP_CAP,
    merge_stock_scrap_capabilities,
    scan_stock_count,
    scan_stock_scrap,
)

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "skeletons" / "baseline"


class StockScrapE08Tests(unittest.TestCase):
    def test_capability_registered_no_domain_default(self) -> None:
        self.assertEqual(CAPABILITIES[STOCK_SCRAP_CAP]["status"], "implemented")
        self.assertEqual(CAPABILITIES[STOCK_COUNT_CAP]["status"], "implemented")
        for cap in (STOCK_SCRAP_CAP, STOCK_COUNT_CAP):
            self.assertNotIn(cap, DOMAIN_CAPABILITIES.get("DOM-ASSET") or [], cap)

    def test_scan_terms(self) -> None:
        self.assertTrue(scan_stock_scrap("支持物资报废登记与原因留痕。"))
        self.assertTrue(scan_stock_count("支持库存盘点，录入实盘数。"))
        self.assertFalse(scan_stock_scrap("仅入库出库登记。"))
        self.assertFalse(scan_stock_count("仅入库出库登记。"))

    def test_merge_and_attach(self) -> None:
        base = list(DOMAIN_CAPABILITIES["DOM-ASSET"])
        no = merge_stock_scrap_capabilities(base, "物资领用与入出库。", domain="DOM-ASSET")
        self.assertNotIn(STOCK_SCRAP_CAP, no)
        self.assertNotIn(STOCK_COUNT_CAP, no)

        scrap = merge_stock_scrap_capabilities(
            base, "物资领用；支持报废登记。", domain="DOM-ASSET"
        )
        self.assertIn(STOCK_SCRAP_CAP, scrap)
        self.assertIn(STOCK_IO_CAP, scrap)

        both = merge_stock_scrap_capabilities(
            ["archive"], "报废与库存盘点。", domain="DOM-SHOP"
        )
        self.assertIn(STOCK_IO_CAP, both)
        self.assertIn(STOCK_SCRAP_CAP, both)
        self.assertIn(STOCK_COUNT_CAP, both)

        plain = attach_accept(
            {
                "domain": "DOM-ASSET",
                "title": "物资领用",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-ASSET"]),
                "archetype": "ARCH-FLOW",
            },
            "物资领用审批与入出库。",
        )
        self.assertNotIn(STOCK_SCRAP_CAP, plain.get("capabilities") or [])
        self.assertNotIn(STOCK_COUNT_CAP, plain.get("capabilities") or [])

        rich = attach_accept(
            {
                "domain": "DOM-ASSET",
                "title": "物资领用",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-ASSET"]),
                "archetype": "ARCH-FLOW",
            },
            "物资领用；支持报废与盘点。",
        )
        caps = rich.get("capabilities") or []
        self.assertIn(STOCK_SCRAP_CAP, caps)
        self.assertIn(STOCK_COUNT_CAP, caps)
        labels = (rich.get("schema") or {}).get("labels") or {}
        self.assertIn("报废", str(labels.get("stockMovesLead") or ""))
        self.assertIn("盘点", str(labels.get("stockMovesLead") or ""))
        self.assertNotIn("演示", str(labels.get("stockMovesLead") or ""))

    def test_baseline_store_and_fe(self) -> None:
        store = BASELINE / "backend/src/main/java/com/thesis/service/StockIoStore.java"
        binder = BASELINE / "backend/src/main/java/com/thesis/config/DomainRuntimeBinder.java"
        moves = BASELINE / "frontend/src/views/admin/StockMovesAdmin.vue"
        ledger = BASELINE / "frontend/src/views/admin/StockLedgerAdmin.vue"
        text = store.read_text(encoding="utf-8")
        self.assertIn("postCount", text)
        self.assertIn("scrapEnabled", text)
        self.assertIn('"scrap"', text)
        bt = binder.read_text(encoding="utf-8")
        self.assertIn("stock-scrap-enabled", bt)
        self.assertIn("stockScrapEnabled", bt)
        mv = moves.read_text(encoding="utf-8")
        self.assertIn("stock_scrap", mv)
        self.assertIn("stock_count", mv)
        self.assertIn("报废", mv)
        self.assertIn("盘点", mv)
        self.assertIn("actualQty", mv)
        ld = ledger.read_text(encoding="utf-8")
        self.assertIn("stock_scrap", ld)
        self.assertIn("scrap", ld)


if __name__ == "__main__":
    unittest.main()
