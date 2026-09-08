"""能力扩岛 E-09：周排班 staff_roster（开题扫词才挂，无域默认）。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES
from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.staff_roster import (
    STAFF_ROSTER_CAP,
    merge_staff_roster_capabilities,
    scan_staff_roster,
)
from tests.helpers.normalize import normalize_sql

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "skeletons" / "baseline"


class StaffRosterE09Tests(unittest.TestCase):
    def test_capability_registered_no_domain_default(self) -> None:
        self.assertEqual(CAPABILITIES[STAFF_ROSTER_CAP]["status"], "implemented")
        for dom in ("DOM-SALON", "DOM-DORM", "DOM-PROPERTY", "DOM-IT"):
            self.assertNotIn(STAFF_ROSTER_CAP, DOMAIN_CAPABILITIES.get(dom) or [], dom)

    def test_scan_terms(self) -> None:
        self.assertTrue(scan_staff_roster("支持技师排班与周排班。"))
        self.assertTrue(scan_staff_roster("维修排班与值班表。"))
        self.assertFalse(scan_staff_roster("报修派单与接单跟进。"))

    def test_merge_only_when_scanned(self) -> None:
        base = list(DOMAIN_CAPABILITIES["DOM-SALON"])
        no = merge_staff_roster_capabilities(base, "美业项目预约。", domain="DOM-SALON")
        self.assertNotIn(STAFF_ROSTER_CAP, no)
        yes = merge_staff_roster_capabilities(
            base, "美业预约；支持技师排班。", domain="DOM-SALON"
        )
        self.assertIn(STAFF_ROSTER_CAP, yes)

    def test_attach_accept_sql_yml_menu(self) -> None:
        plain = attach_accept(
            {
                "domain": "DOM-SALON",
                "title": "美业预约",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-SALON"]),
                "archetype": "ARCH-SLOT",
            },
            "美业项目时段预约。",
        )
        self.assertNotIn(STAFF_ROSTER_CAP, plain.get("capabilities") or [])
        menus0 = (plain.get("schema") or {}).get("menus", {}).get("admin") or []
        self.assertFalse(any(m.get("key") == "staff_roster" for m in menus0))

        rich = attach_accept(
            {
                "domain": "DOM-SALON",
                "title": "美业预约",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-SALON"]),
                "archetype": "ARCH-SLOT",
            },
            "美业预约；支持技师排班与值班表。",
        )
        caps = rich.get("capabilities") or []
        self.assertIn(STAFF_ROSTER_CAP, caps)
        menus = (rich.get("schema") or {}).get("menus", {}).get("admin") or []
        self.assertTrue(any(m.get("key") == "staff_roster" for m in menus))
        lead = ((rich.get("schema") or {}).get("labels") or {}).get(
            "staffRosterPageLead"
        ) or ""
        self.assertNotIn("演示", str(lead))
        self.assertIn("staff_roster", (rich.get("gate") or {}).get("flow_api") or {})

        yml = _patch_thesis_yml("thesis:\n  domain: DOM-SALON\n", "DOM-SALON", rich)
        self.assertIn("staff-roster-enabled: true", yml)

        sql = domain_sql(
            "DOM-SALON",
            "thesis_salon",
            capabilities=caps,
            proposal_text="美业预约；支持技师排班与值班表。",
        )
        n = normalize_sql(sql)
        self.assertIn("staff_roster", n)
        self.assertIn("work_date", n)

    def test_unmounted_no_roster_table(self) -> None:
        plain = attach_accept(
            {
                "domain": "DOM-DORM",
                "title": "宿舍报修",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-DORM"]),
                "archetype": "ARCH-FLOW",
            },
            "宿舍报修派单接单。",
        )
        sql = domain_sql(
            "DOM-DORM",
            "thesis_dorm",
            capabilities=plain.get("capabilities") or [],
            proposal_text="宿舍报修派单接单。",
        )
        self.assertNotIn("staff_roster", normalize_sql(sql))

    def test_baseline_store_controller_fe_hook(self) -> None:
        store = (
            BASELINE
            / "backend/src/main/java/com/thesis/capability/StaffRosterStore.java"
        ).read_text(encoding="utf-8")
        self.assertIn("onDuty", store)
        self.assertIn("create", store)
        ctrl = (
            BASELINE
            / "backend/src/main/java/com/thesis/controller/StaffRosterController.java"
        )
        self.assertTrue(ctrl.is_file())
        text = ctrl.read_text(encoding="utf-8")
        self.assertIn("/api/admin/staff-roster", text)
        self.assertIn("/api/staff-roster/on-duty", text)
        fe = BASELINE / "frontend/src/views/admin/StaffRosterAdmin.vue"
        self.assertTrue(fe.is_file())
        slot = (BASELINE / "frontend/src/views/user/SlotBook.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn("staff_roster", slot)
        self.assertIn("onDuty", slot)
        tickets = (
            BASELINE / "frontend/src/views/admin/TicketsAdmin.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("onDutyToday", tickets)
        ticket_ctrl = (
            BASELINE
            / "backend/src/main/java/com/thesis/controller/TicketController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("StaffRosterStore", ticket_ctrl)
        router = (BASELINE / "frontend/src/router/index.js").read_text(encoding="utf-8")
        self.assertIn("withStaffRosterRoutes", router)
        self.assertIn("StaffRosterAdmin", router)


if __name__ == "__main__":
    unittest.main()
