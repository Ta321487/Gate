"""跟进组页内构图 follow_surface_style：域默认、手选、隐喻绑域、菜单保全。"""

from __future__ import annotations

import unittest

from app.bake.catalog import build_spec
from app.bake.themes import (
    FOLLOW_SURFACE_DOMAINS,
    FOLLOW_SURFACE_STYLES,
    normalize_follow_surface_style,
    resolve_follow_surface_style,
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


class FollowSurfaceStyleTests(unittest.TestCase):
    def test_catalog_ids(self) -> None:
        ids = {t["id"] for t in FOLLOW_SURFACE_STYLES}
        self.assertEqual(ids, {"pipeline", "dossier", "listing"})

    def test_non_follow_empty(self) -> None:
        self.assertEqual(
            resolve_follow_surface_style("DOM-LIBRARY", None, "seed"),
            "",
        )
        self.assertEqual(
            resolve_follow_surface_style("DOM-LIBRARY", "pipeline", "seed"),
            "",
        )

    def test_domain_defaults(self) -> None:
        self.assertIn("DOM-CRM", FOLLOW_SURFACE_DOMAINS)
        self.assertEqual(
            resolve_follow_surface_style("DOM-CRM", None, "seed"),
            "pipeline",
        )
        self.assertEqual(
            resolve_follow_surface_style("DOM-LISTING", None, "seed"),
            "listing",
        )
        for domain in (
            "DOM-EVENT",
            "DOM-ATTEND",
            "DOM-FUND",
            "DOM-RECRUIT",
            "DOM-GRADE",
            "DOM-INTERN",
        ):
            self.assertEqual(
                resolve_follow_surface_style(domain, None, "seed"),
                "dossier",
            )

    def test_metaphor_gates(self) -> None:
        self.assertEqual(
            resolve_follow_surface_style("DOM-INTERN", "listing", "seed"),
            "dossier",
        )
        self.assertEqual(
            resolve_follow_surface_style("DOM-INTERN", "pipeline", "seed"),
            "dossier",
        )
        self.assertEqual(
            resolve_follow_surface_style("DOM-LISTING", "pipeline", "seed"),
            "listing",
        )
        self.assertEqual(
            resolve_follow_surface_style("DOM-CRM", "dossier", "seed"),
            "dossier",
        )
        self.assertEqual(
            resolve_follow_surface_style("DOM-LISTING", "dossier", "seed"),
            "dossier",
        )

    def test_override_hand_pick(self) -> None:
        self.assertEqual(normalize_follow_surface_style("pipeline"), "pipeline")
        spec = build_spec(
            "客户跟进",
            "ARCH-CRUD",
            "DOM-CRM",
            "crm-ocean",
            False,
            "recommended",
            0.9,
            follow_surface_style="pipeline",
        )
        self.assertEqual(spec["follow_surface_style"], "pipeline")
        self.assertEqual(spec["follow_surface_style_label"], "阶段看板")

    def test_listing_default_in_spec(self) -> None:
        spec = build_spec(
            "房源带看",
            "ARCH-CRUD",
            "DOM-LISTING",
            "listing-teal",
            False,
            "recommended",
            0.9,
        )
        self.assertEqual(spec["follow_surface_style"], "listing")

    def test_menu_paths_stable_across_styles(self) -> None:
        """越界手选回落后菜单 key 不变。"""
        specs = [
            build_spec(
                "客户跟进",
                "ARCH-CRUD",
                "DOM-CRM",
                "crm-ocean",
                False,
                "recommended",
                0.9,
                follow_surface_style=style,
            )
            for style in ("pipeline", "dossier", "listing")
        ]
        ref = _menu_key_sets(specs[0])
        for spec in specs[1:]:
            self.assertEqual(_menu_key_sets(spec), ref)
        self.assertEqual(specs[0]["follow_surface_style"], "pipeline")
        self.assertEqual(specs[1]["follow_surface_style"], "dossier")
        self.assertEqual(specs[2]["follow_surface_style"], "pipeline")
        self.assertTrue(ref[0] or ref[1], "跟进域应至少有用户或管理菜单")


if __name__ == "__main__":
    unittest.main()
