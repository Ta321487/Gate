# -*- coding: utf-8 -*-
"""门户脸：检索占位、card_voice、壳色。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.shell_face import (
    _DOMAIN_CARD_VOICE,
    _DOMAIN_SEARCH_PLACEHOLDER,
    _DOMAIN_SHELL_COLORS,
    known_face_domains,
    resolve_card_voice,
    resolve_shell_colors,
    resolve_shell_nav_style,
    shell_colors_from_theme,
    top_search_placeholder,
)


class ShellFaceTests(unittest.TestCase):
    def test_all_domains_have_face_tables(self) -> None:
        doms = set(DOMAIN_CAPABILITIES.keys())
        self.assertEqual(doms, set(known_face_domains()))
        self.assertEqual(doms, set(_DOMAIN_SEARCH_PLACEHOLDER))
        self.assertEqual(doms, set(_DOMAIN_CARD_VOICE))
        self.assertEqual(doms, set(_DOMAIN_SHELL_COLORS))
        for d in sorted(doms):
            ph = top_search_placeholder(d)
            self.assertTrue(ph and ph != "搜索名称", d)
            self.assertNotEqual(ph, "搜索", d)
            voice = resolve_card_voice(d)
            self.assertIn(voice, {"catalog", "story", "board"}, d)
            colors = resolve_shell_colors(d)
            for key in ("brand", "accent", "bg", "surface", "ink", "glow"):
                self.assertTrue(str(colors.get(key) or "").startswith("#"), f"{d}.{key}")
            cover = str(colors.get("cover") or "")
            self.assertTrue(cover.startswith("linear-gradient"), f"{d}.cover")
            self.assertIn(colors["brand"], cover, d)
            self.assertIn(colors["accent"], cover, d)

    def test_shell_brands_not_all_identical(self) -> None:
        brands = {resolve_shell_colors(d)["brand"] for d in DOMAIN_CAPABILITIES}
        self.assertGreaterEqual(len(brands), 20)

    def test_farm_voice_and_green_shell(self) -> None:
        title = "助农生鲜商城"
        body = "水果蔬菜产地直供，支持购物车下单。"
        self.assertEqual(resolve_card_voice("DOM-SHOP", title, body), "story")
        colors = resolve_shell_colors("DOM-SHOP", title, body)
        self.assertEqual(colors.get("brand"), "#1F6B4A")
        self.assertIn("产地", top_search_placeholder("DOM-SHOP", title, body))

    def test_fitness_voice_and_dark_shell(self) -> None:
        title = "健身器材商城"
        body = "哑铃跑步机，按训练目标与器材类型浏览。"
        self.assertEqual(resolve_card_voice("DOM-SHOP", title, body), "catalog")
        # 无 theme：货架兜底仍可橙；有 theme：必须跟行业配色，禁止另喷橙盖海蓝
        colors = resolve_shell_colors("DOM-SHOP", title, body)
        self.assertEqual(colors.get("brand"), "#12151A")
        self.assertEqual(colors.get("accent"), "#E85D04")
        ocean = resolve_shell_colors("DOM-SHOP", title, body, theme="shop-ocean")
        self.assertEqual(ocean.get("accent"), "#0e74b4")
        self.assertNotEqual(ocean.get("accent"), "#E85D04")
        self.assertEqual(resolve_shell_nav_style("DOM-SHOP", title, body), "storefront")

    def test_theme_shell_colors_from_css(self) -> None:
        coral = shell_colors_from_theme("shop-coral")
        self.assertIsNotNone(coral)
        assert coral is not None
        self.assertEqual(coral["accent"], "#e1453d")
        self.assertTrue(str(coral["cover"]).startswith("linear-gradient"))
        self.assertIsNone(shell_colors_from_theme("not-a-real-theme-xyz"))

    def test_farm_marketplace_nav_vs_fitness_storefront(self) -> None:
        self.assertEqual(
            resolve_shell_nav_style("DOM-SHOP", "助农生鲜商城", "水果蔬菜产地直供"),
            "marketplace",
        )
        self.assertEqual(
            resolve_shell_nav_style("DOM-SHOP", "方木健身用品电商", "哑铃杠铃健身器材"),
            "storefront",
        )
        self.assertEqual(resolve_shell_nav_style("DOM-LIBRARY", "图书", "借还"), "storefront")

    def test_library_catalog_voice(self) -> None:
        self.assertEqual(
            resolve_card_voice("DOM-LIBRARY", "图书借阅", "借还书"),
            "catalog",
        )
        self.assertIn("书名", top_search_placeholder("DOM-LIBRARY"))

    def test_attach_accept_writes_face(self) -> None:
        out = attach_accept(
            {
                "domain": "DOM-LIBRARY",
                "title": "图书借阅管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
                "features": [],
                "archetype": "ARCH-FLOW",
            },
            "实现图书借阅与归还。",
        )
        self.assertEqual(out.get("card_voice"), "catalog")
        self.assertIsInstance(out.get("shell_colors"), dict)
        self.assertTrue((out.get("shell_colors") or {}).get("brand"))
        self.assertEqual(out.get("domain_group"), "borrow")
        self.assertEqual(out.get("shell_nav_style"), "storefront")
        flags = ((out.get("schema") or {}).get("listCrosscut") or {})
        self.assertTrue(flags.get("globalSearch"))

    def test_attach_accept_theme_drives_shop_shell(self) -> None:
        """商城带 theme 时壳色跟下拉，不跟健身货架橙。"""
        out = attach_accept(
            {
                "domain": "DOM-SHOP",
                "title": "方木健身用品电商平台",
                "theme": "shop-ocean",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-SHOP"]),
                "features": [],
                "archetype": "ARCH-CRUD",
            },
            "哑铃杠铃瑜伽垫，购物车下单与订单发货。",
        )
        colors = out.get("shell_colors") or {}
        self.assertEqual(colors.get("accent"), "#0e74b4")
        self.assertNotEqual(colors.get("accent"), "#E85D04")


if __name__ == "__main__":
    unittest.main()
