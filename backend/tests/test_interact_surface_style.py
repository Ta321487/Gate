"""互动组页内构图 interact_surface_style：域默认、手选、隐喻绑域、菜单保全。"""

from __future__ import annotations

import unittest

from app.bake.catalog import build_spec
from app.bake.themes import (
    INTERACT_SURFACE_DOMAINS,
    INTERACT_SURFACE_STYLES,
    normalize_interact_surface_style,
    resolve_interact_surface_style,
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


class InteractSurfaceStyleTests(unittest.TestCase):
    def test_catalog_ids(self) -> None:
        ids = {t["id"] for t in INTERACT_SURFACE_STYLES}
        self.assertEqual(ids, {"profilegrid", "mutualpick", "triprow"})

    def test_non_interact_empty(self) -> None:
        self.assertEqual(
            resolve_interact_surface_style("DOM-LIBRARY", None, "seed"),
            "",
        )
        # 考试/问卷/投票有专用页，不进本轴
        self.assertEqual(
            resolve_interact_surface_style("DOM-EXAM", "profilegrid", "seed"),
            "",
        )
        self.assertEqual(
            resolve_interact_surface_style("DOM-SURVEY", None, "seed"),
            "",
        )
        self.assertEqual(
            resolve_interact_surface_style("DOM-VOTE", None, "seed"),
            "",
        )

    def test_domain_defaults(self) -> None:
        self.assertIn("DOM-DATING", INTERACT_SURFACE_DOMAINS)
        self.assertEqual(
            resolve_interact_surface_style("DOM-DATING", None, "seed"),
            "profilegrid",
        )
        self.assertEqual(
            resolve_interact_surface_style("DOM-MUTUAL-TUTOR", None, "seed"),
            "mutualpick",
        )
        self.assertEqual(
            resolve_interact_surface_style("DOM-MUTUAL-TOPIC", None, "seed"),
            "mutualpick",
        )
        self.assertEqual(
            resolve_interact_surface_style("DOM-MUTUAL-TEAM", None, "seed"),
            "mutualpick",
        )
        self.assertEqual(
            resolve_interact_surface_style("DOM-CARPOOL", None, "seed"),
            "triprow",
        )
        self.assertEqual(
            resolve_interact_surface_style("DOM-TIMEBANK", None, "seed"),
            "triprow",
        )

    def test_metaphor_gates(self) -> None:
        self.assertEqual(
            resolve_interact_surface_style("DOM-DATING", "mutualpick", "seed"),
            "profilegrid",
        )
        self.assertEqual(
            resolve_interact_surface_style("DOM-MUTUAL-TUTOR", "triprow", "seed"),
            "mutualpick",
        )
        self.assertEqual(
            resolve_interact_surface_style("DOM-CARPOOL", "profilegrid", "seed"),
            "triprow",
        )

    def test_override_hand_pick(self) -> None:
        self.assertEqual(normalize_interact_surface_style("profilegrid"), "profilegrid")
        spec = build_spec(
            "校园交友",
            "ARCH-CRUD",
            "DOM-DATING",
            "dating-rose",
            False,
            "recommended",
            0.9,
            interact_surface_style="profilegrid",
        )
        self.assertEqual(spec["interact_surface_style"], "profilegrid")
        self.assertEqual(spec["interact_surface_style_label"], "资料卡片墙")

    def test_dating_default_in_spec(self) -> None:
        spec = build_spec(
            "校园交友",
            "ARCH-CRUD",
            "DOM-DATING",
            "dating-rose",
            False,
            "recommended",
            0.9,
        )
        self.assertEqual(spec["interact_surface_style"], "profilegrid")

    def test_menu_paths_stable_across_styles(self) -> None:
        """越界手选回落后菜单 key 不变。"""
        specs = [
            build_spec(
                "校园交友",
                "ARCH-CRUD",
                "DOM-DATING",
                "dating-rose",
                False,
                "recommended",
                0.9,
                interact_surface_style=style,
            )
            for style in ("profilegrid", "mutualpick", "triprow")
        ]
        ref = _menu_key_sets(specs[0])
        for spec in specs[1:]:
            self.assertEqual(_menu_key_sets(spec), ref)
            self.assertEqual(spec["interact_surface_style"], "profilegrid")
        self.assertTrue(ref[0] or ref[1], "互动域应至少有用户或管理菜单")


if __name__ == "__main__":
    unittest.main()
