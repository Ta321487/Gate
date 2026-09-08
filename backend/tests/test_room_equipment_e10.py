"""能力扩岛 E-10：会议室设备清单 room_equipment（开题扫词才挂，无域默认）。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES
from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.room_equipment import (
    ROOM_EQUIPMENT_CAP,
    merge_room_equipment_capabilities,
    scan_room_equipment,
)
from tests.helpers.normalize import normalize_sql

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "skeletons" / "baseline"


class RoomEquipmentE10Tests(unittest.TestCase):
    def test_capability_registered_no_domain_default(self) -> None:
        self.assertEqual(CAPABILITIES[ROOM_EQUIPMENT_CAP]["status"], "implemented")
        for dom in ("DOM-MEETING", "DOM-SALON", "DOM-EQUIP", "DOM-LIBRARY"):
            self.assertNotIn(ROOM_EQUIPMENT_CAP, DOMAIN_CAPABILITIES.get(dom) or [], dom)

    def test_scan_terms(self) -> None:
        self.assertTrue(scan_room_equipment("会议室配套设备清单。"))
        self.assertTrue(scan_room_equipment("投影音响清单可维护。"))
        self.assertFalse(scan_room_equipment("会议室预约与审核。"))

    def test_merge_meeting_only_not_equip(self) -> None:
        meeting = list(DOMAIN_CAPABILITIES["DOM-MEETING"])
        no = merge_room_equipment_capabilities(
            meeting, "会议室预约审核。", domain="DOM-MEETING"
        )
        self.assertNotIn(ROOM_EQUIPMENT_CAP, no)
        yes = merge_room_equipment_capabilities(
            meeting, "会议室预约；配套设备清单。", domain="DOM-MEETING"
        )
        self.assertIn(ROOM_EQUIPMENT_CAP, yes)

        equip = list(DOMAIN_CAPABILITIES.get("DOM-EQUIP") or [])
        blocked = merge_room_equipment_capabilities(
            equip, "设备清单与借用。", domain="DOM-EQUIP"
        )
        self.assertNotIn(ROOM_EQUIPMENT_CAP, blocked)

    def test_attach_accept_sql_yml_menus(self) -> None:
        plain = attach_accept(
            {
                "domain": "DOM-MEETING",
                "title": "会议室预约系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-MEETING"]),
                "archetype": "ARCH-RESERVE",
            },
            "会议室预约与审核。",
        )
        self.assertNotIn(ROOM_EQUIPMENT_CAP, plain.get("capabilities") or [])
        menus0 = (plain.get("schema") or {}).get("menus", {}).get("admin") or []
        self.assertFalse(any(m.get("key") == "equipment_dict" for m in menus0))

        rich = attach_accept(
            {
                "domain": "DOM-MEETING",
                "title": "会议室预约系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-MEETING"]),
                "archetype": "ARCH-RESERVE",
            },
            "会议室预约；支持会议室设备清单与配套设备维护。",
        )
        caps = rich.get("capabilities") or []
        self.assertIn(ROOM_EQUIPMENT_CAP, caps)
        menus = (rich.get("schema") or {}).get("menus", {}).get("admin") or []
        self.assertTrue(any(m.get("key") == "equipment_dict" for m in menus))
        self.assertIn("room_equipment", (rich.get("gate") or {}).get("flow_api") or {})

        yml = _patch_thesis_yml("thesis:\n  domain: DOM-MEETING\n", "DOM-MEETING", rich)
        self.assertIn("room-equipment-enabled: true", yml)

        sql = domain_sql(
            "DOM-MEETING",
            "thesis_meeting",
            capabilities=caps,
            proposal_text="会议室预约；支持会议室设备清单与配套设备维护。",
        )
        n = normalize_sql(sql)
        self.assertIn("sys_equipment_dict", n)
        self.assertIn("equipment_json", n)

    def test_unmounted_no_equip_sql(self) -> None:
        plain = attach_accept(
            {
                "domain": "DOM-MEETING",
                "title": "会议室预约系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-MEETING"]),
                "archetype": "ARCH-RESERVE",
            },
            "会议室预约与审核。",
        )
        sql = domain_sql(
            "DOM-MEETING",
            "thesis_meeting",
            capabilities=plain.get("capabilities") or [],
            proposal_text="会议室预约与审核。",
        )
        n = normalize_sql(sql)
        self.assertNotIn("sys_equipment_dict", n)

    def test_baseline_files(self) -> None:
        store = (
            BASELINE
            / "backend/src/main/java/com/thesis/capability/EquipmentDictStore.java"
        )
        ctrl = (
            BASELINE
            / "backend/src/main/java/com/thesis/controller/EquipmentDictController.java"
        )
        admin = BASELINE / "frontend/src/views/admin/EquipmentDictAdmin.vue"
        self.assertTrue(store.is_file())
        self.assertTrue(ctrl.is_file())
        self.assertTrue(admin.is_file())
        self.assertIn("optionNames", store.read_text(encoding="utf-8"))
        self.assertIn("/api/admin/equipment-dict", ctrl.read_text(encoding="utf-8"))
        archive = (
            BASELINE
            / "backend/src/main/java/com/thesis/capability/ArchiveStore.java"
        ).read_text(encoding="utf-8")
        self.assertIn("configureRoomEquipment", archive)
        self.assertIn("equipment_json", archive)
        fe_browse = (
            BASELINE / "frontend/src/views/user/ArchiveBrowse.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("room_equipment", fe_browse)
        fe_slot = (
            BASELINE / "frontend/src/views/user/SlotBook.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("room_equipment", fe_slot)
        fe_admin = (
            BASELINE / "frontend/src/views/admin/ArchiveAdmin.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("equipmentNames", fe_admin)
        router = (BASELINE / "frontend/src/router/index.js").read_text(encoding="utf-8")
        self.assertIn("EquipmentDictAdmin", router)


if __name__ == "__main__":
    unittest.main()
