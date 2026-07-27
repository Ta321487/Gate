"""泳道 E · C-17：浅进销存 stock_io + DOM-ASSET。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES, resolve_accept, scan_out_of_scope
from app.bake.catalog import match_text
from app.bake.domain_schema import attach_accept, build_domain_schema, validate_schema
from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.stock_io import STOCK_IO_CAP, scan_stock_io
from app.bake.menu_routes import shell_kind

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "data" / "samples" / "进销存预设开题"
BASELINE = ROOT / "skeletons" / "baseline"
MYBATIS = ROOT / "skeletons" / "overlays" / "persistence-mybatis"
JPA = ROOT / "skeletons" / "overlays" / "persistence-jpa"


class StockIoC17Tests(unittest.TestCase):
    def test_capability_and_domain(self) -> None:
        self.assertIn(STOCK_IO_CAP, CAPABILITIES)
        self.assertEqual(CAPABILITIES[STOCK_IO_CAP]["status"], "implemented")
        self.assertIn("DOM-ASSET", DOMAINS)
        caps = DOMAIN_CAPABILITIES["DOM-ASSET"]
        self.assertIn(STOCK_IO_CAP, caps)
        self.assertIn("ticket_flow", caps)
        self.assertIn("quota", caps)

    def test_scan_and_oos(self) -> None:
        self.assertTrue(scan_stock_io("仓储物资入库出库与库存台账管理"))
        self.assertTrue(scan_stock_io("支持浅进销存入出存登记"))
        # 裸进销存不再单独过重；须多仓/ERP 同伴
        shallow = "主要功能\n1. 物资目录\n2. 入库出库登记与库存流水\n3. 申领审核"
        self.assertNotIn("ERP/多仓进销存", scan_out_of_scope(shallow))
        erp = "主要功能\n实现进销存与多仓调拨，对接 WMS。"
        self.assertIn("ERP/多仓进销存", scan_out_of_scope(erp))
        self.assertIn("RFID全链路", scan_out_of_scope("主要功能\nRFID 全链路盘点与出入库。"))

    def test_match_neighbors(self) -> None:
        got = match_text(
            "基于 Spring Boot 的仓储物资入库出库与库存台账管理系统的设计与实现。"
            "主要功能：物资目录、入库登记、出库登记、库存流水、申领审核。"
        )
        self.assertEqual(got.domain, "DOM-ASSET", f"hits={got.hits[:12]}")
        cases = [
            ("仓储物资入库出库库存台账", "DOM-ASSET", "DOM-PROCURE"),
            ("物资采购申请与申购单审批", "DOM-PROCURE", "DOM-ASSET"),
        ]
        for phrase, want, avoid in cases:
            with self.subTest(phrase=phrase):
                m = match_text(f"基于 Spring Boot 的{phrase}系统的设计与实现")
                self.assertEqual(m.domain, want, f"hits={m.hits[:12]}")
                self.assertNotEqual(m.domain, avoid)

    def test_schema_menus_yml(self) -> None:
        schema = build_domain_schema("仓储物资入库出库管理系统", "DOM-ASSET")
        ok, errs = validate_schema(schema)
        self.assertTrue(ok, errs[:5])
        self.assertEqual(shell_kind(DOMAIN_CAPABILITIES["DOM-ASSET"]), "archive_ticket")
        spec = attach_accept(
            {
                "domain": "DOM-ASSET",
                "title": "仓储物资入库出库与库存台账管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-ASSET"]),
                "archetype": "ARCH-STOCK",
            },
            "入库出库登记；库存流水；申领审核。不做多仓 ERP 与 RFID。",
        )
        sch = spec.get("schema") or {}
        admin_keys = {m.get("key") for m in (sch.get("menus") or {}).get("admin") or []}
        self.assertIn("stock_moves", admin_keys)
        self.assertIn("stock_ledger", admin_keys)
        self.assertIn(STOCK_IO_CAP, spec.get("capabilities") or [])
        self.assertEqual(spec.get("accept"), "full", spec.get("accept_reason"))

        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-ASSET", spec)
        self.assertIn("stock-io-enabled: true", yml)

        sql = domain_sql(
            "DOM-ASSET",
            "t_asset",
            title="仓储物资入库出库管理系统",
            proposal_text="入库出库库存台账",
        )
        self.assertIn("stock_move", sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS asset", sql)

        d = resolve_accept(
            list(DOMAIN_CAPABILITIES["DOM-ASSET"]),
            "入库出库；库存流水；申领。",
            has_domain_overlay=True,
            has_baseline_runtime=True,
            archetypes=["ARCH-STOCK"],
            domain="DOM-ASSET",
            primary_archetype="ARCH-STOCK",
        )
        self.assertEqual(d["accept"], "full", d)

    def test_runtime_paths(self) -> None:
        for rel in (
            "backend/src/main/java/com/thesis/service/StockIoStore.java",
            "backend/src/main/java/com/thesis/controller/StockIoController.java",
            "frontend/src/views/admin/StockMovesAdmin.vue",
            "frontend/src/views/admin/StockLedgerAdmin.vue",
        ):
            self.assertTrue((BASELINE / rel).is_file(), rel)
        for root in (BASELINE, MYBATIS, JPA):
            binder = root / "backend/src/main/java/com/thesis/config/DomainRuntimeBinder.java"
            bt = binder.read_text(encoding="utf-8")
            self.assertIn("stock-io-enabled", bt, msg=str(binder))
            self.assertIn("StockIoStore.configure", bt, msg=str(binder))
            store = root / "backend/src/main/java/com/thesis/service/StockIoStore.java"
            self.assertTrue(store.is_file(), msg=str(store))
        self.assertTrue(
            (MYBATIS / "backend/src/main/java/com/thesis/mapper/StockIoMapper.java").is_file()
        )
        router = (BASELINE / "frontend/src/router/index.js").read_text(encoding="utf-8")
        self.assertIn("withStockIoRoutes", router)
        self.assertIn("stock_io", router)

    def test_sample_file(self) -> None:
        samples = list(SAMPLES.glob("C-17*.txt"))
        self.assertTrue(samples, "missing C-17 sample under 进销存预设开题")
        body = samples[0].read_text(encoding="utf-8")
        self.assertTrue(scan_stock_io(body))
        self.assertIn("DOM-ASSET", body)
        self.assertNotIn("ERP/多仓进销存", scan_out_of_scope(body))


if __name__ == "__main__":
    unittest.main()
