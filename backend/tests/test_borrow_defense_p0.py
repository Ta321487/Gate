"""借用/占用域答辩补强：book_lost / parcel_shelf / parcel_ship / EQUIP 验图皮。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES
from app.bake.domain_schema import attach_accept, build_domain_schema
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.book_lost import BOOK_LOST_CAP, merge_book_lost_capabilities
from app.bake.features.parcel_shelf import PARCEL_SHELF_CAP, merge_parcel_shelf_capabilities
from app.bake.features.parcel_ship import (
    PARCEL_SHIP_CAP,
    merge_parcel_ship_capabilities,
    scan_parcel_ship,
)
from tests.helpers.normalize import normalize_sql

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "skeletons" / "baseline"


def _spec(domain: str, title: str, body: str = "") -> dict:
    schema = build_domain_schema(title, domain, proposal_text=body)
    return attach_accept(
        {
            "domain": domain,
            "title": title,
            "capabilities": list(DOMAIN_CAPABILITIES[domain]),
            "schema": schema,
            "accept": "full",
        },
        body,
    )


class BorrowDefenseP0Tests(unittest.TestCase):
    def test_caps_registered(self) -> None:
        for cap in (BOOK_LOST_CAP, PARCEL_SHELF_CAP, PARCEL_SHIP_CAP):
            self.assertEqual(CAPABILITIES[cap]["status"], "implemented", cap)

    def test_library_book_lost_domain_default(self) -> None:
        self.assertIn(BOOK_LOST_CAP, DOMAIN_CAPABILITIES["DOM-LIBRARY"])
        out = _spec("DOM-LIBRARY", "高校图书借阅管理系统", "借还逾期")
        self.assertIn(BOOK_LOST_CAP, out["capabilities"])
        ticket = out["schema"]["entities"]["ticket"]
        self.assertTrue(ticket.get("allowBookLost"))
        states = ticket.get("states") or {}
        self.assertEqual(states.get("lost"), "丢失申报")
        self.assertEqual(states.get("compensated"), "赔偿完成")
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-LIBRARY", out)
        self.assertIn("ticket-allow-book-lost: true", yml)

    def test_equip_return_attach_and_repair_stage(self) -> None:
        out = _spec("DOM-EQUIP", "高校实验室设备借用系统", "借用归还")
        ticket = out["schema"]["entities"]["ticket"]
        self.assertTrue(ticket.get("requireReturnAttach"))
        fields = out["schema"]["entities"]["archive"].get("fields") or []
        stage = next((f for f in fields if f.get("key") == "stage"), None)
        self.assertIsNotNone(stage)
        self.assertIn("维修中", stage.get("options") or [])
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-EQUIP", out)
        self.assertIn("ticket-require-return-attach: true", yml)
        sql = domain_sql("DOM-EQUIP", "t", title="设备借用", proposal_text="借用")
        self.assertIn("stage", normalize_sql(sql).lower())

    def test_parcel_shelf_default_and_exception_stages(self) -> None:
        self.assertIn(PARCEL_SHELF_CAP, DOMAIN_CAPABILITIES["DOM-PARCEL"])
        out = _spec("DOM-PARCEL", "校园快递驿站", "取件核销")
        self.assertIn(PARCEL_SHELF_CAP, out["capabilities"])
        menus = [m.get("key") for m in out["schema"]["menus"]["admin"]]
        self.assertIn("parcel_shelf", menus)
        fields = out["schema"]["entities"]["archive"].get("fields") or []
        stage = next((f for f in fields if f.get("key") == "stage"), None)
        self.assertIsNotNone(stage)
        for opt in ("损坏", "误领", "拒收"):
            self.assertIn(opt, stage.get("options") or [])
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-PARCEL", out)
        self.assertIn("parcel-shelf-enabled: true", yml)

    def test_parcel_ship_scan_only(self) -> None:
        self.assertNotIn(PARCEL_SHIP_CAP, DOMAIN_CAPABILITIES["DOM-PARCEL"])
        self.assertTrue(scan_parcel_ship("寄件登记与取件"))
        self.assertFalse(scan_parcel_ship("仅取件核销"))
        caps = merge_parcel_ship_capabilities(
            list(DOMAIN_CAPABILITIES["DOM-PARCEL"]),
            "寄件登记",
            domain="DOM-PARCEL",
        )
        self.assertIn(PARCEL_SHIP_CAP, caps)
        out = _spec("DOM-PARCEL", "校园快递驿站", "寄件登记与取件核销")
        self.assertIn(PARCEL_SHIP_CAP, out["capabilities"])
        menus_u = [m.get("key") for m in out["schema"]["menus"]["user"]]
        menus_a = [m.get("key") for m in out["schema"]["menus"]["admin"]]
        self.assertIn("parcel_ship", menus_u)
        self.assertIn("parcel_ship", menus_a)
        sql = domain_sql(
            "DOM-PARCEL",
            "t",
            title="驿站",
            proposal_text="寄件登记与取件",
            capabilities=out["capabilities"],
        )
        self.assertIn("parcel_ship", normalize_sql(sql).lower())

    def test_skeleton_files_exist(self) -> None:
        for rel in (
            "backend/src/main/java/com/thesis/capability/ParcelShelfStore.java",
            "backend/src/main/java/com/thesis/controller/ParcelShelfController.java",
            "backend/src/main/java/com/thesis/capability/ParcelShipStore.java",
            "backend/src/main/java/com/thesis/controller/ParcelShipController.java",
            "frontend/src/views/admin/ParcelShelfAdmin.vue",
            "frontend/src/views/user/ParcelShip.vue",
            "frontend/src/views/admin/ParcelShipAdmin.vue",
        ):
            self.assertTrue((BASELINE / rel).is_file(), rel)
        store = (BASELINE / "backend/src/main/java/com/thesis/capability/TicketStore.java").read_text(
            encoding="utf-8"
        )
        self.assertIn("reportLost", store)
        self.assertIn("markCompensated", store)
        self.assertIn("requireReturnAttach", store)
        self.assertIn("hotItemSeries", store)

    def test_merge_idempotent(self) -> None:
        base = list(DOMAIN_CAPABILITIES["DOM-LIBRARY"])
        a = merge_book_lost_capabilities(base, "", domain="DOM-LIBRARY")
        b = merge_book_lost_capabilities(a, "", domain="DOM-LIBRARY")
        self.assertEqual(a, b)
        p = merge_parcel_shelf_capabilities(
            list(DOMAIN_CAPABILITIES["DOM-PARCEL"]), "", domain="DOM-PARCEL"
        )
        self.assertEqual(
            p,
            merge_parcel_shelf_capabilities(p, "", domain="DOM-PARCEL"),
        )


if __name__ == "__main__":
    unittest.main()
