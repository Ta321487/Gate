"""交易组页内构图 trade_surface_style：域默认、手选、菜单保全。"""

from __future__ import annotations

import unittest

from app.bake.catalog import build_spec
from app.bake.themes import (
    TRADE_SURFACE_DOMAINS,
    TRADE_SURFACE_STYLES,
    normalize_trade_surface_style,
    resolve_trade_surface_style,
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


class TradeSurfaceStyleTests(unittest.TestCase):
    def test_catalog_ids(self) -> None:
        ids = {t["id"] for t in TRADE_SURFACE_STYLES}
        self.assertEqual(ids, {"shelfgrid", "menuboard", "showtime"})

    def test_non_trade_empty(self) -> None:
        self.assertEqual(
            resolve_trade_surface_style("DOM-LIBRARY", None, "seed"),
            "",
        )
        self.assertEqual(
            resolve_trade_surface_style("DOM-LIBRARY", "shelfgrid", "seed"),
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
        self.assertEqual(spec["trade_surface_style"], "")

    def test_domain_defaults(self) -> None:
        self.assertIn("DOM-SHOP", TRADE_SURFACE_DOMAINS)
        self.assertEqual(
            resolve_trade_surface_style("DOM-SHOP", None, "seed"),
            "shelfgrid",
        )
        self.assertEqual(
            resolve_trade_surface_style("DOM-FOOD", None, "seed"),
            "menuboard",
        )
        self.assertEqual(
            resolve_trade_surface_style("DOM-CINEMA", None, "seed"),
            "showtime",
        )

    def test_override_hand_pick(self) -> None:
        self.assertEqual(normalize_trade_surface_style("menuboard"), "menuboard")
        spec = build_spec(
            "食堂点餐",
            "ARCH-TRADE",
            "DOM-FOOD",
            "food-chili",
            False,
            "recommended",
            0.9,
            trade_surface_style="shelfgrid",
        )
        self.assertEqual(spec["trade_surface_style"], "shelfgrid")
        self.assertEqual(spec["trade_surface_style_label"], "货架密铺")

    def test_metaphor_gates(self) -> None:
        self.assertEqual(
            resolve_trade_surface_style("DOM-SHOP", "showtime", "seed"),
            "shelfgrid",
        )
        self.assertEqual(
            resolve_trade_surface_style("DOM-SHOP", "menuboard", "seed"),
            "shelfgrid",
        )
        self.assertEqual(
            resolve_trade_surface_style("DOM-FOOD", "showtime", "seed"),
            "menuboard",
        )
        self.assertEqual(
            resolve_trade_surface_style("DOM-CINEMA", "menuboard", "seed"),
            "showtime",
        )
        self.assertEqual(
            resolve_trade_surface_style("DOM-FOOD", "shelfgrid", "seed"),
            "shelfgrid",
        )
        self.assertEqual(
            resolve_trade_surface_style("DOM-CINEMA", "showtime", "seed"),
            "showtime",
        )
        spec = build_spec(
            "校园商城",
            "ARCH-TRADE",
            "DOM-SHOP",
            "shop-coral",
            False,
            "recommended",
            0.9,
            trade_surface_style="showtime",
        )
        self.assertEqual(spec["trade_surface_style"], "shelfgrid")

    def test_cinema_default_in_spec(self) -> None:
        spec = build_spec(
            "影院售票",
            "ARCH-TRADE",
            "DOM-CINEMA",
            "cinema-night",
            False,
            "recommended",
            0.9,
        )
        self.assertEqual(spec["trade_surface_style"], "showtime")

    def test_menu_paths_stable_across_styles(self) -> None:
        """换构图不得增删交付菜单 key（菜单保全）。"""
        # 影院允许 shelfgrid/showtime；越界 menuboard 回落后菜单仍一致
        specs = [
            build_spec(
                "影院售票",
                "ARCH-TRADE",
                "DOM-CINEMA",
                "cinema-night",
                False,
                "recommended",
                0.9,
                trade_surface_style=style,
            )
            for style in ("shelfgrid", "menuboard", "showtime")
        ]
        ref = _menu_key_sets(specs[0])
        for spec in specs[1:]:
            self.assertEqual(_menu_key_sets(spec), ref)
        self.assertEqual(specs[0]["trade_surface_style"], "shelfgrid")
        self.assertEqual(specs[1]["trade_surface_style"], "showtime")
        self.assertEqual(specs[2]["trade_surface_style"], "showtime")
        self.assertTrue(ref[0] or ref[1], "交易域应至少有用户或管理菜单")


if __name__ == "__main__":
    unittest.main()
