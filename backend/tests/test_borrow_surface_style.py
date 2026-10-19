"""借用组页内构图 borrow_surface_style：域默认、手选、菜单保全。"""

from __future__ import annotations

import unittest

from app.bake.catalog import build_spec
from app.bake.themes import (
    BORROW_SURFACE_DOMAINS,
    BORROW_SURFACE_STYLES,
    normalize_borrow_surface_style,
    resolve_borrow_surface_style,
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


class BorrowSurfaceStyleTests(unittest.TestCase):
    def test_catalog_ids(self) -> None:
        ids = {t["id"] for t in BORROW_SURFACE_STYLES}
        self.assertEqual(ids, {"bookshelf", "stockrow", "bedblocks", "parcelshelf"})

    def test_non_borrow_empty(self) -> None:
        self.assertEqual(
            resolve_borrow_surface_style("DOM-SHOP", None, "seed"),
            "",
        )
        self.assertEqual(
            resolve_borrow_surface_style("DOM-SHOP", "bookshelf", "seed"),
            "",
        )
        spec = build_spec(
            "校园商城",
            "ARCH-CRUD",
            "DOM-SHOP",
            "shop-coral",
            False,
            "recommended",
            0.9,
        )
        self.assertEqual(spec["borrow_surface_style"], "")

    def test_domain_defaults(self) -> None:
        self.assertIn("DOM-LIBRARY", BORROW_SURFACE_DOMAINS)
        self.assertEqual(
            resolve_borrow_surface_style("DOM-LIBRARY", None, "seed"),
            "bookshelf",
        )
        self.assertEqual(
            resolve_borrow_surface_style("DOM-ASSET", None, "seed"),
            "stockrow",
        )
        self.assertEqual(
            resolve_borrow_surface_style("DOM-EQUIP", None, "seed"),
            "stockrow",
        )
        self.assertEqual(
            resolve_borrow_surface_style("DOM-PROCURE", None, "seed"),
            "stockrow",
        )
        self.assertEqual(
            resolve_borrow_surface_style("DOM-BED", None, "seed"),
            "bedblocks",
        )
        self.assertEqual(
            resolve_borrow_surface_style("DOM-PARCEL", None, "seed"),
            "parcelshelf",
        )

    def test_metaphor_gates(self) -> None:
        self.assertEqual(
            resolve_borrow_surface_style("DOM-LIBRARY", "bedblocks", "seed"),
            "bookshelf",
        )
        self.assertEqual(
            resolve_borrow_surface_style("DOM-LIBRARY", "parcelshelf", "seed"),
            "bookshelf",
        )
        self.assertEqual(
            resolve_borrow_surface_style("DOM-BED", "bookshelf", "seed"),
            "bedblocks",
        )
        self.assertEqual(
            resolve_borrow_surface_style("DOM-PARCEL", "stockrow", "seed"),
            "parcelshelf",
        )
        self.assertEqual(
            resolve_borrow_surface_style("DOM-LIBRARY", "stockrow", "seed"),
            "stockrow",
        )
        self.assertEqual(
            resolve_borrow_surface_style("DOM-ASSET", "stockrow", "seed"),
            "stockrow",
        )

    def test_override_hand_pick(self) -> None:
        self.assertEqual(normalize_borrow_surface_style("stockrow"), "stockrow")
        spec = build_spec(
            "图书借阅",
            "ARCH-CRUD",
            "DOM-LIBRARY",
            "lib-ink",
            False,
            "recommended",
            0.9,
            borrow_surface_style="stockrow",
        )
        self.assertEqual(spec["borrow_surface_style"], "stockrow")
        self.assertEqual(spec["borrow_surface_style_label"], "库存台账行")

    def test_library_default_in_spec(self) -> None:
        spec = build_spec(
            "图书借阅",
            "ARCH-CRUD",
            "DOM-LIBRARY",
            "lib-ink",
            False,
            "recommended",
            0.9,
        )
        self.assertEqual(spec["borrow_surface_style"], "bookshelf")

    def test_menu_paths_stable_across_styles(self) -> None:
        """换构图不得增删交付菜单 key（菜单保全）。"""
        # 图书允许 bookshelf/stockrow；越界 bedblocks/parcelshelf 回落后菜单仍一致
        specs = [
            build_spec(
                "图书借阅",
                "ARCH-CRUD",
                "DOM-LIBRARY",
                "lib-ink",
                False,
                "recommended",
                0.9,
                borrow_surface_style=style,
            )
            for style in ("bookshelf", "stockrow", "bedblocks", "parcelshelf")
        ]
        ref = _menu_key_sets(specs[0])
        for spec in specs[1:]:
            self.assertEqual(_menu_key_sets(spec), ref)
        self.assertEqual(specs[0]["borrow_surface_style"], "bookshelf")
        self.assertEqual(specs[1]["borrow_surface_style"], "stockrow")
        self.assertEqual(specs[2]["borrow_surface_style"], "bookshelf")
        self.assertEqual(specs[3]["borrow_surface_style"], "bookshelf")
        self.assertTrue(ref[0] or ref[1], "借用域应至少有用户或管理菜单")


if __name__ == "__main__":
    unittest.main()
