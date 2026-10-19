"""报修组页内构图 repair_surface_style：域默认、手选、越界回落、菜单保全。"""

from __future__ import annotations

import unittest

from app.bake.catalog import build_spec
from app.bake.themes import (
    REPAIR_SURFACE_DOMAINS,
    REPAIR_SURFACE_STYLES,
    normalize_repair_surface_style,
    resolve_repair_surface_style,
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


class RepairSurfaceStyleTests(unittest.TestCase):
    def test_catalog_ids(self) -> None:
        ids = {t["id"] for t in REPAIR_SURFACE_STYLES}
        self.assertEqual(ids, {"ticketfeed", "faultboard"})

    def test_non_repair_empty(self) -> None:
        self.assertEqual(
            resolve_repair_surface_style("DOM-LIBRARY", None, "seed"),
            "",
        )
        self.assertEqual(
            resolve_repair_surface_style("DOM-LIBRARY", "faultboard", "seed"),
            "",
        )

    def test_domain_defaults(self) -> None:
        for domain in ("DOM-DORM", "DOM-PROPERTY", "DOM-IT"):
            self.assertIn(domain, REPAIR_SURFACE_DOMAINS)
            self.assertEqual(
                resolve_repair_surface_style(domain, None, "seed"),
                "ticketfeed",
            )

    def test_hand_pick_stays(self) -> None:
        self.assertEqual(normalize_repair_surface_style("faultboard"), "faultboard")
        for domain in ("DOM-DORM", "DOM-PROPERTY", "DOM-IT"):
            self.assertEqual(
                resolve_repair_surface_style(domain, "faultboard", "seed"),
                "faultboard",
            )
        spec = build_spec(
            "宿舍报修",
            "ARCH-FLOW",
            "DOM-DORM",
            "dorm-sky",
            False,
            "recommended",
            0.9,
            repair_surface_style="faultboard",
        )
        self.assertEqual(spec["repair_surface_style"], "faultboard")
        self.assertEqual(spec["repair_surface_style_label"], "分类故障看板")

    def test_unknown_falls_back(self) -> None:
        self.assertEqual(
            resolve_repair_surface_style("DOM-DORM", "pipeline", "seed"),
            "ticketfeed",
        )

    def test_menu_paths_stable_across_styles(self) -> None:
        specs = [
            build_spec(
                "宿舍报修",
                "ARCH-FLOW",
                "DOM-DORM",
                "dorm-sky",
                False,
                "recommended",
                0.9,
                repair_surface_style=style,
            )
            for style in ("ticketfeed", "faultboard", "pipeline")
        ]
        ref = _menu_key_sets(specs[0])
        for spec in specs[1:]:
            self.assertEqual(_menu_key_sets(spec), ref)
        self.assertEqual(specs[0]["repair_surface_style"], "ticketfeed")
        self.assertEqual(specs[1]["repair_surface_style"], "faultboard")
        self.assertEqual(specs[2]["repair_surface_style"], "ticketfeed")
        self.assertTrue(ref[0] or ref[1], "报修域应至少有用户或管理菜单")


if __name__ == "__main__":
    unittest.main()
