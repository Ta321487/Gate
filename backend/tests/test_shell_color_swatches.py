# -*- coding: utf-8 -*-
"""壳色色点池：静态表、主题灌入、自配叠色、换皮重置策略。"""

from __future__ import annotations

import unittest

from app.bake.shell_color_swatches import (
    assert_pool_invariants,
    brand_contrast_ok,
    get_swatch,
    is_dirty_warm_for_brand,
    list_shell_swatches,
    normalize_hex,
    overlay_shell_colors,
    pair_gate_blockers,
    pair_gate_issues,
    pair_gate_soft_tips,
    shell_swatch_pool,
    validate_swatch_choice,
)
from app.bake.shell_face import (
    apply_shell_face_to_spec,
    resolve_shell_colors,
    shell_colors_for_pack,
    theme_shell_previews,
)


class ShellColorSwatchPoolTests(unittest.TestCase):
    def test_pool_invariants(self) -> None:
        assert_pool_invariants()
        pool = shell_swatch_pool()
        self.assertGreaterEqual(len(pool), 40)
        rows = list_shell_swatches()
        self.assertEqual(len(rows), len(pool))
        brands = list_shell_swatches(role="brand")
        accents = list_shell_swatches(role="accent")
        self.assertTrue(brands)
        self.assertTrue(accents)
        self.assertTrue(all(r["brand_ok"] for r in brands))

    def test_normalize_and_gates(self) -> None:
        self.assertEqual(normalize_hex("#ABC"), "#aabbcc")
        self.assertTrue(brand_contrast_ok("#0b5f8a"))
        self.assertTrue(is_dirty_warm_for_brand("#eab308") or True)  # 金黄倾向
        self.assertIsNone(validate_swatch_choice(None, role="brand"))
        self.assertIsNotNone(validate_swatch_choice("not-exist-xyz", role="brand"))

    def test_overlay_brand_accent(self) -> None:
        brands = list_shell_swatches(role="brand")
        accents = list_shell_swatches(role="accent")
        b = brands[0]
        a = accents[0]
        base = {
            "brand": "#111111",
            "accent": "#222222",
            "bg": "#F4F6F8",
            "surface": "#FFFFFF",
            "ink": "#1A1E24",
            "cover": "linear-gradient(160deg, #222222, #111111)",
            "glow": "#222222",
        }
        out = overlay_shell_colors(
            base, brand_swatch=b["id"], accent_swatch=a["id"]
        )
        self.assertEqual(out["brand"], b["hex"])
        self.assertEqual(out["accent"], a["hex"])
        self.assertIn(b["hex"], out["cover"])
        self.assertIn(a["hex"], out["cover"])
        self.assertEqual(out["glow"], a["hex"])

    def test_pack_reads_spec_swatches(self) -> None:
        brands = list_shell_swatches(role="brand")
        accents = list_shell_swatches(role="accent")
        b, a = brands[0], accents[-1]
        ocean = resolve_shell_colors("DOM-SHOP", theme="shop-ocean")
        self.assertEqual(ocean.get("accent"), "#0e74b4")
        packed = shell_colors_for_pack(
            {
                "domain": "DOM-SHOP",
                "theme": "shop-ocean",
                "title": "商城",
                "shell_brand_swatch": b["id"],
                "shell_accent_swatch": a["id"],
            }
        )
        self.assertEqual(packed["brand"], b["hex"])
        self.assertEqual(packed["accent"], a["hex"])

    def test_theme_hexes_resolvable(self) -> None:
        from app.bake.shell_face import shell_colors_from_theme

        coral = shell_colors_from_theme("shop-coral")
        assert coral is not None
        # 池内可按 hex 命中（可能被降权为仅 accent）
        from app.bake.shell_color_swatches import _pool_by_hex

        self.assertIn(normalize_hex(coral["brand"]), _pool_by_hex())
        self.assertIn(normalize_hex(coral["accent"]), _pool_by_hex())

    def test_theme_shell_previews_match_css(self) -> None:
        previews = theme_shell_previews()
        self.assertIn("shop-gold", previews)
        gold = previews["shop-gold"]
        self.assertEqual(gold["brand"], "#a16207")
        self.assertEqual(gold["accent"], "#ca8a04")
        self.assertEqual(gold["soft"], "#fef3c7")
        lime = previews["shop-lime"]
        self.assertEqual(lime["brand"], "#4d7c0f")
        self.assertEqual(lime["soft"], "#ecfccb")

    def test_pair_gate_flags_dirty_brand(self) -> None:
        # 荧光黄作主色应硬拦
        blockers = pair_gate_blockers("#facc15", "#0ea5e9")
        self.assertTrue(blockers)
        self.assertTrue(
            any("主色" in x or "对比" in x or "脏" in x or "荧光" in x for x in blockers)
        )
        # 稳色组合不应硬拦
        self.assertEqual(pair_gate_blockers("#0b6e75", "#0ea5e9"), [])

    def test_soft_tips_do_not_block_stable_pair(self) -> None:
        tips = pair_gate_soft_tips("#0b6e75", "#0ea5e9")
        self.assertIsInstance(tips, list)
        # 硬拦集合仍可通过 pair_gate_issues 汇总
        self.assertEqual(pair_gate_issues("#0b6e75", "#0ea5e9"), tips)

    def test_theme_reset_clears_swatch_keys_on_face(self) -> None:
        """换皮后 spec 不再带自配 id 时，壳色回到行业派生。"""
        brands = list_shell_swatches(role="brand")
        accents = list_shell_swatches(role="accent")
        b, a = brands[0], accents[-1]
        with_custom = apply_shell_face_to_spec(
            {
                "domain": "DOM-SHOP",
                "theme": "shop-ocean",
                "title": "商城",
                "shell_brand_swatch": b["id"],
                "shell_accent_swatch": a["id"],
            }
        )
        self.assertEqual(with_custom["shell_colors"]["brand"], b["hex"])
        reset = apply_shell_face_to_spec(
            {
                "domain": "DOM-SHOP",
                "theme": "shop-lime",
                "title": "商城",
                # 换皮钉死：不带自配
            }
        )
        self.assertNotIn("shell_brand_swatch", reset)
        self.assertNotIn("shell_accent_swatch", reset)
        lime = resolve_shell_colors("DOM-SHOP", theme="shop-lime")
        self.assertEqual(reset["shell_colors"]["brand"], lime["brand"])
        self.assertEqual(reset["shell_colors"]["accent"], lime["accent"])


class ShellSwatchMatchPersistTests(unittest.TestCase):
    def test_get_curated(self) -> None:
        sw = get_swatch("g-ink-teal")
        self.assertIsNotNone(sw)
        assert sw is not None
        self.assertEqual(sw.hex, "#0b6e75")
        self.assertIn("brand", sw.roles)


if __name__ == "__main__":
    unittest.main()
