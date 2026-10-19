"""内容组页内构图 content_surface_style：域默认、手选、菜单保全。"""

from __future__ import annotations

import unittest

from app.bake.catalog import build_spec
from app.bake.themes import (
    CONTENT_SURFACE_DOMAINS,
    CONTENT_SURFACE_STYLES,
    normalize_content_surface_style,
    resolve_content_surface_style,
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


class ContentSurfaceStyleTests(unittest.TestCase):
    def test_catalog_ids(self) -> None:
        ids = {t["id"] for t in CONTENT_SURFACE_STYLES}
        self.assertEqual(ids, {"folio", "coverwall", "ledger", "splitdesk"})

    def test_non_content_empty(self) -> None:
        self.assertEqual(
            resolve_content_surface_style("DOM-LIBRARY", None, "seed"),
            "",
        )
        self.assertEqual(
            resolve_content_surface_style("DOM-LIBRARY", "folio", "seed"),
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
        self.assertEqual(spec["content_surface_style"], "")

    def test_domain_defaults(self) -> None:
        self.assertIn("DOM-BLOG", CONTENT_SURFACE_DOMAINS)
        self.assertEqual(
            resolve_content_surface_style("DOM-BLOG", None, "seed"),
            "folio",
        )
        self.assertEqual(
            resolve_content_surface_style("DOM-FORUM", None, "seed"),
            "folio",
        )
        self.assertEqual(
            resolve_content_surface_style("DOM-MEDIA", None, "seed"),
            "coverwall",
        )
        self.assertEqual(
            resolve_content_surface_style("DOM-MUSIC", None, "seed"),
            "coverwall",
        )
        self.assertEqual(
            resolve_content_surface_style("DOM-DOCLIB", None, "seed"),
            "ledger",
        )

    def test_override_hand_pick(self) -> None:
        self.assertEqual(normalize_content_surface_style("splitdesk"), "splitdesk")
        spec = build_spec(
            "校园博客",
            "ARCH-CRUD",
            "DOM-BLOG",
            "blog-ink",
            False,
            "recommended",
            0.9,
            content_surface_style="splitdesk",
        )
        self.assertEqual(spec["content_surface_style"], "splitdesk")
        self.assertEqual(spec["content_surface_style_label"], "双栏阅读台")

    def test_media_default_in_spec(self) -> None:
        spec = build_spec(
            "影视点播",
            "ARCH-CRUD",
            "DOM-MEDIA",
            "media-cinema",
            False,
            "recommended",
            0.9,
        )
        self.assertEqual(spec["content_surface_style"], "coverwall")

    def test_menu_paths_stable_across_styles(self) -> None:
        """换构图不得增删交付菜单 key（菜单保全）。"""
        specs = [
            build_spec(
                "校园博客",
                "ARCH-CRUD",
                "DOM-BLOG",
                "blog-ink",
                False,
                "recommended",
                0.9,
                content_surface_style=style,
            )
            for style in ("folio", "coverwall", "ledger", "splitdesk")
        ]
        ref = _menu_key_sets(specs[0])
        for spec in specs[1:]:
            self.assertEqual(_menu_key_sets(spec), ref)
        self.assertTrue(ref[0] or ref[1], "内容域应至少有用户或管理菜单")


if __name__ == "__main__":
    unittest.main()
