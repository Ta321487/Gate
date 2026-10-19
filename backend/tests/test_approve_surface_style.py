"""审批组页内构图 approve_surface_style：域默认、手选、越界回落、菜单保全。"""

from __future__ import annotations

import unittest

from app.bake.catalog import build_spec
from app.bake.themes import (
    APPROVE_SURFACE_DOMAINS,
    APPROVE_SURFACE_STYLES,
    normalize_approve_surface_style,
    resolve_approve_surface_style,
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


class ApproveSurfaceStyleTests(unittest.TestCase):
    def test_catalog_ids(self) -> None:
        ids = {t["id"] for t in APPROVE_SURFACE_STYLES}
        self.assertEqual(ids, {"typelist", "inboxsteps"})

    def test_non_approve_empty(self) -> None:
        self.assertEqual(
            resolve_approve_surface_style("DOM-DORM", None, "seed"),
            "",
        )
        self.assertEqual(
            resolve_approve_surface_style("DOM-DORM", "inboxsteps", "seed"),
            "",
        )

    def test_domain_defaults(self) -> None:
        self.assertEqual(len(APPROVE_SURFACE_DOMAINS), 23)
        for domain in APPROVE_SURFACE_DOMAINS:
            self.assertEqual(
                resolve_approve_surface_style(domain, None, "seed"),
                "typelist",
            )

    def test_hand_pick_stays(self) -> None:
        self.assertEqual(normalize_approve_surface_style("inboxsteps"), "inboxsteps")
        spec = build_spec(
            "证明开具",
            "ARCH-FLOW",
            "DOM-CERT",
            "cert-teal",
            False,
            "recommended",
            0.9,
            approve_surface_style="inboxsteps",
        )
        self.assertEqual(spec["approve_surface_style"], "inboxsteps")
        self.assertEqual(spec["approve_surface_style_label"], "待审收件箱+步骤条")

    def test_unknown_falls_back(self) -> None:
        self.assertEqual(
            resolve_approve_surface_style("DOM-CERT", "faultboard", "seed"),
            "typelist",
        )

    def test_menu_paths_stable_across_styles(self) -> None:
        specs = [
            build_spec(
                "证明开具",
                "ARCH-FLOW",
                "DOM-CERT",
                "cert-teal",
                False,
                "recommended",
                0.9,
                approve_surface_style=style,
            )
            for style in ("typelist", "inboxsteps", "faultboard")
        ]
        ref = _menu_key_sets(specs[0])
        for spec in specs[1:]:
            self.assertEqual(_menu_key_sets(spec), ref)
        self.assertEqual(specs[0]["approve_surface_style"], "typelist")
        self.assertEqual(specs[1]["approve_surface_style"], "inboxsteps")
        self.assertEqual(specs[2]["approve_surface_style"], "typelist")
        self.assertTrue(ref[0] or ref[1], "审批域应至少有用户或管理菜单")


if __name__ == "__main__":
    unittest.main()
