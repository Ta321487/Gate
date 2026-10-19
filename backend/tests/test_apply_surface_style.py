"""报名组页内构图 apply_surface_style：域默认、手选、隐喻绑域、菜单保全。"""

from __future__ import annotations

import unittest

from app.bake.catalog import build_spec
from app.bake.themes import (
    APPLY_SURFACE_DOMAINS,
    APPLY_SURFACE_STYLES,
    normalize_apply_surface_style,
    resolve_apply_surface_style,
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


class ApplySurfaceStyleTests(unittest.TestCase):
    def test_catalog_ids(self) -> None:
        ids = {t["id"] for t in APPLY_SURFACE_STYLES}
        self.assertEqual(ids, {"eventposter", "coursetable", "noticeboard", "tourcard"})

    def test_non_apply_empty(self) -> None:
        self.assertEqual(
            resolve_apply_surface_style("DOM-LIBRARY", None, "seed"),
            "",
        )
        self.assertEqual(
            resolve_apply_surface_style("DOM-LIBRARY", "eventposter", "seed"),
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
        self.assertEqual(spec["apply_surface_style"], "")

    def test_domain_defaults(self) -> None:
        self.assertIn("DOM-ACTIVITY", APPLY_SURFACE_DOMAINS)
        self.assertEqual(
            resolve_apply_surface_style("DOM-ACTIVITY", None, "seed"),
            "eventposter",
        )
        self.assertEqual(
            resolve_apply_surface_style("DOM-COURSE", None, "seed"),
            "coursetable",
        )
        self.assertEqual(
            resolve_apply_surface_style("DOM-LOST", None, "seed"),
            "noticeboard",
        )
        self.assertEqual(
            resolve_apply_surface_style("DOM-TOUR", None, "seed"),
            "tourcard",
        )

    def test_metaphor_gates(self) -> None:
        self.assertEqual(
            resolve_apply_surface_style("DOM-ACTIVITY", "coursetable", "seed"),
            "eventposter",
        )
        self.assertEqual(
            resolve_apply_surface_style("DOM-COURSE", "tourcard", "seed"),
            "coursetable",
        )
        self.assertEqual(
            resolve_apply_surface_style("DOM-LOST", "eventposter", "seed"),
            "noticeboard",
        )
        self.assertEqual(
            resolve_apply_surface_style("DOM-TOUR", "noticeboard", "seed"),
            "tourcard",
        )

    def test_override_hand_pick(self) -> None:
        self.assertEqual(normalize_apply_surface_style("eventposter"), "eventposter")
        spec = build_spec(
            "社团活动报名",
            "ARCH-CRUD",
            "DOM-ACTIVITY",
            "act-coral",
            False,
            "recommended",
            0.9,
            apply_surface_style="eventposter",
        )
        self.assertEqual(spec["apply_surface_style"], "eventposter")
        self.assertEqual(spec["apply_surface_style_label"], "活动海报墙")

    def test_activity_default_in_spec(self) -> None:
        spec = build_spec(
            "社团活动报名",
            "ARCH-CRUD",
            "DOM-ACTIVITY",
            "act-coral",
            False,
            "recommended",
            0.9,
        )
        self.assertEqual(spec["apply_surface_style"], "eventposter")

    def test_menu_paths_stable_across_styles(self) -> None:
        """越界手选回落后菜单 key 不变。"""
        specs = [
            build_spec(
                "社团活动报名",
                "ARCH-CRUD",
                "DOM-ACTIVITY",
                "act-coral",
                False,
                "recommended",
                0.9,
                apply_surface_style=style,
            )
            for style in ("eventposter", "coursetable", "noticeboard", "tourcard")
        ]
        ref = _menu_key_sets(specs[0])
        for spec in specs[1:]:
            self.assertEqual(_menu_key_sets(spec), ref)
            self.assertEqual(spec["apply_surface_style"], "eventposter")
        self.assertTrue(ref[0] or ref[1], "报名域应至少有用户或管理菜单")


if __name__ == "__main__":
    unittest.main()
