"""预约组页内构图 reserve_surface_style：域默认、手选、菜单保全。"""

from __future__ import annotations

import unittest

from app.bake.catalog import build_spec
from app.bake.themes import (
    RESERVE_SURFACE_DOMAINS,
    RESERVE_SURFACE_STYLES,
    normalize_reserve_surface_style,
    resolve_reserve_surface_style,
)


def _menu_key_sets(spec: dict) -> tuple[frozenset, frozenset, frozenset]:
    menus = (spec.get("schema") or {}).get("menus") or {}

    def keys(role: str) -> frozenset:
        return frozenset(
            str(m.get("key") or "")
            for m in (menus.get(role) or [])
            if m.get("key")
        )

    return keys("user"), keys("admin"), keys("staff")


class ReserveSurfaceStyleTests(unittest.TestCase):
    def test_catalog_ids(self) -> None:
        ids = {t["id"] for t in RESERVE_SURFACE_STYLES}
        self.assertEqual(ids, {"slotstrip", "roomstate", "vehiclecard"})

    def test_non_reserve_empty(self) -> None:
        self.assertEqual(
            resolve_reserve_surface_style("DOM-LIBRARY", None, "seed"),
            "",
        )
        self.assertEqual(
            resolve_reserve_surface_style("DOM-LIBRARY", "slotstrip", "seed"),
            "",
        )
        spec = build_spec(
            "图书借阅",
            "ARCH-CRUD",
            "DOM-LIBRARY",
            "lib-ink",
            False,
            "recommended",
            0.9,
        )
        self.assertEqual(spec["reserve_surface_style"], "")

    def test_domain_defaults(self) -> None:
        self.assertIn("DOM-HOSPITAL", RESERVE_SURFACE_DOMAINS)
        self.assertEqual(
            resolve_reserve_surface_style("DOM-HOSPITAL", None, "seed"),
            "slotstrip",
        )
        self.assertEqual(
            resolve_reserve_surface_style("DOM-MEETING", None, "seed"),
            "slotstrip",
        )
        self.assertEqual(
            resolve_reserve_surface_style("DOM-SALON", None, "seed"),
            "slotstrip",
        )
        self.assertEqual(
            resolve_reserve_surface_style("DOM-INSTRUMENT", None, "seed"),
            "slotstrip",
        )
        self.assertEqual(
            resolve_reserve_surface_style("DOM-HOTEL", None, "seed"),
            "roomstate",
        )
        self.assertEqual(
            resolve_reserve_surface_style("DOM-CARRENT", None, "seed"),
            "vehiclecard",
        )
        self.assertEqual(
            resolve_reserve_surface_style("DOM-PARKING", None, "seed"),
            "vehiclecard",
        )

    def test_metaphor_gates(self) -> None:
        self.assertEqual(
            resolve_reserve_surface_style("DOM-HOSPITAL", "roomstate", "seed"),
            "slotstrip",
        )
        self.assertEqual(
            resolve_reserve_surface_style("DOM-HOSPITAL", "vehiclecard", "seed"),
            "slotstrip",
        )
        self.assertEqual(
            resolve_reserve_surface_style("DOM-HOTEL", "vehiclecard", "seed"),
            "roomstate",
        )
        self.assertEqual(
            resolve_reserve_surface_style("DOM-CARRENT", "roomstate", "seed"),
            "vehiclecard",
        )
        self.assertEqual(
            resolve_reserve_surface_style("DOM-HOTEL", "roomstate", "seed"),
            "roomstate",
        )

    def test_override_hand_pick(self) -> None:
        self.assertEqual(normalize_reserve_surface_style("slotstrip"), "slotstrip")
        spec = build_spec(
            "号源预约",
            "ARCH-RESERVE",
            "DOM-HOSPITAL",
            "hosp-blue",
            False,
            "recommended",
            0.9,
            reserve_surface_style="slotstrip",
        )
        self.assertEqual(spec["reserve_surface_style"], "slotstrip")
        self.assertEqual(spec["reserve_surface_style_label"], "时段条/号源行")

    def test_hotel_default_in_spec(self) -> None:
        spec = build_spec(
            "客房预订",
            "ARCH-RESERVE",
            "DOM-HOTEL",
            "hotel-gold",
            False,
            "recommended",
            0.9,
        )
        self.assertEqual(spec["reserve_surface_style"], "roomstate")

    def test_menu_paths_stable_across_styles(self) -> None:
        """换构图不得增删交付菜单 key（菜单保全）。"""
        # 号源域只允许 slotstrip；越界手选回落后菜单仍须与默认一致
        specs = [
            build_spec(
                "号源预约",
                "ARCH-RESERVE",
                "DOM-HOSPITAL",
                "hosp-blue",
                False,
                "recommended",
                0.9,
                reserve_surface_style=style,
            )
            for style in ("slotstrip", "roomstate", "vehiclecard")
        ]
        ref = _menu_key_sets(specs[0])
        for spec in specs[1:]:
            self.assertEqual(_menu_key_sets(spec), ref)
            self.assertEqual(spec["reserve_surface_style"], "slotstrip")
        self.assertTrue(ref[0] or ref[1], "预约域应至少有用户或管理菜单")


if __name__ == "__main__":
    unittest.main()
