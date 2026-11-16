"""门户首页构图：内容域可抽 editorial；商城货架可选手选；与登录版式同步。"""

from __future__ import annotations

import unittest

from app.bake.catalog import build_spec
from app.bake.themes import (
    CONTENT_PORTAL_HOME_DOMAINS,
    MALL_PORTAL_HOME_DOMAINS,
    normalize_portal_home_style,
    resolve_portal_home_style,
)


class PortalHomeStyleTests(unittest.TestCase):
    def test_non_content_defaults_cards(self) -> None:
        self.assertEqual(
            resolve_portal_home_style("DOM-LIBRARY", None, "seed"),
            "cards",
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
        self.assertEqual(spec["portal_home_style"], "cards")

    def test_content_domain_seed_pick(self) -> None:
        self.assertIn("DOM-BLOG", CONTENT_PORTAL_HOME_DOMAINS)
        a = resolve_portal_home_style("DOM-BLOG", None, "alpha|portal")
        b = resolve_portal_home_style("DOM-BLOG", None, "alpha|portal")
        self.assertEqual(a, b)
        self.assertIn(a, {"cards", "editorial"})

    def test_override_and_auth_sync(self) -> None:
        self.assertEqual(normalize_portal_home_style("editorial"), "editorial")
        spec = build_spec(
            "校园博客",
            "ARCH-CRUD",
            "DOM-BLOG",
            "blog-ink",
            False,
            "recommended",
            0.9,
            portal_home_style="editorial",
        )
        self.assertEqual(spec["portal_home_style"], "editorial")
        self.assertEqual(spec["auth_template"], "editorial")

    def test_force_cards_does_not_force_auth(self) -> None:
        """cards 不强制 auth=editorial；auth 仍按种子独立抽取（可能碰巧是 editorial）。"""
        title = "校园博客"
        domain = "DOM-BLOG"
        seed = f"{title}|{domain}"
        from app.bake.themes import pick_auth_template

        expected_auth = pick_auth_template(seed)
        spec = build_spec(
            title,
            "ARCH-CRUD",
            domain,
            "blog-ink",
            False,
            "recommended",
            0.9,
            portal_home_style="cards",
        )
        self.assertEqual(spec["portal_home_style"], "cards")
        self.assertEqual(spec["auth_template"], expected_auth)

    def test_mall_shop_ok_other_clamped(self) -> None:
        self.assertIn("DOM-SHOP", MALL_PORTAL_HOME_DOMAINS)
        self.assertEqual(normalize_portal_home_style("mall"), "mall")
        self.assertEqual(
            resolve_portal_home_style("DOM-SHOP", "mall", "seed"),
            "mall",
        )
        self.assertEqual(
            resolve_portal_home_style("DOM-FOOD", "mall", "seed"),
            "mall",
        )
        self.assertEqual(
            resolve_portal_home_style("DOM-LIBRARY", "mall", "seed"),
            "cards",
        )
        # 学生包不写 DOM-* 时 domain 可能空；手选 mall 不得被空串降成 cards
        self.assertEqual(
            resolve_portal_home_style("", "mall", "seed"),
            "mall",
        )
        self.assertEqual(
            resolve_portal_home_style("DOM-SHOP", None, "seed"),
            "mall",
        )
        self.assertEqual(
            resolve_portal_home_style("DOM-FOOD", None, "seed"),
            "mall",
        )
        spec = build_spec(
            "校园商城",
            "ARCH-TRADE",
            "DOM-SHOP",
            "shop-coral",
            False,
            "recommended",
            0.9,
        )
        self.assertEqual(spec["portal_home_style"], "mall")
        # mall 不强制登录版式
        self.assertNotEqual(spec.get("auth_template"), "mall")

    def test_mall_cats_tint_follows_brand_not_ink(self):
        """分类条禁止用 portal-ink 半透磨出工业灰（空横幅时尤其像工厂默认条）。"""
        import re
        from pathlib import Path

        root = Path(__file__).resolve().parents[2] / "skeletons/baseline/frontend/src"
        home = (root / "views/user/PortalHome.css").read_text(encoding="utf-8")
        voice = (root / "styles/cardVoice.css").read_text(encoding="utf-8")
        # 主规则（含 background）须跟 brand；media 里的布局覆盖可无色
        def strip_css_comments(text: str) -> str:
            return re.sub(r"/\*.*?\*/", "", text, flags=re.S)

        blocks = re.findall(r"\.mall-cats\s*\{([^}]*)\}", home)
        painted = [strip_css_comments(b) for b in blocks if "background" in b]
        self.assertTrue(painted, "expected .mall-cats background rule")
        for block in painted:
            self.assertIn("portal-brand", block)
            self.assertNotIn("portal-ink", block)
        story = strip_css_comments(
            voice.split("html[data-card-voice='story'] .mall-cats {", 1)[1].split(
                "}", 1
            )[0]
        )
        self.assertIn("portal-brand", story)
        self.assertNotIn("portal-ink", story)


if __name__ == "__main__":
    unittest.main()
