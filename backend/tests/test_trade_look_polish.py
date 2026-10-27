"""交易组观感再磨（menuboard / showtime + 短签接线）护栏。

钉住：
- ArchiveBrowse 列表短签芯片接线（cardShortTags / short-tags / more-hint）；
- 档口菜单板 / 排片行 CSS 加厚异于 shelfgrid；
- 主信号：档口看价、排片看余座。
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FE = REPO / "skeletons" / "baseline" / "frontend" / "src" / "views" / "user"
VUE = FE / "ArchiveBrowse.vue"
SETUP = FE / "ArchiveBrowse.setup.js"
CSS = FE / "ArchiveBrowse.css"


class TradeLookPolishTests(unittest.TestCase):
    def test_short_tags_wired(self) -> None:
        vue = VUE.read_text(encoding="utf-8")
        for needle in (
            "cardShortTags(row)",
            'class="short-tags"',
            'class="short-tag"',
            'class="short-tag-k"',
            'class="short-tag-v"',
            'class="more-hint"',
            'class="promo promo-bar"',
            "cardVoice === 'story' ? cardPreviewFields : []",
        ):
            self.assertIn(needle, vue, f"vue 缺 {needle}")
        # 「另有 N 项」在 card-foot；货架面关掉（真实货架无此元信息）
        foot_at = vue.find('class="card-foot"')
        self.assertGreater(foot_at, 0)
        foot_chunk = vue[foot_at : foot_at + 900]
        self.assertIn('class="more-hint"', foot_chunk)
        self.assertIn("tradeSurface !== 'shelfgrid'", foot_chunk)
        short_at = vue.find('class="short-tags"')
        between = vue[short_at:foot_at]
        self.assertNotIn('class="more-hint"', between)

    def test_trade_primary_and_tags(self) -> None:
        setup = SETUP.read_text(encoding="utf-8")
        for needle in (
            "tradeSurface.value === 'menuboard'",
            "tradeSurface.value === 'showtime'",
            "余座",
            "已满座",
            "function cardShortTags(row)",
        ):
            self.assertIn(needle, setup, f"setup 缺 {needle}")
        # catalog 短签：只出值芯片（禁表单「规格型号：」腔；亦禁空格硬拼）
        fn = setup.find("function cardShortTags(row)")
        catalog = setup[fn:]
        self.assertIn("push('productSpec', spec)", catalog)
        self.assertIn("push(f.key, v)", catalog)
        self.assertNotIn("push('productSpec', spec, productSpecLabel.value)", catalog)
        self.assertNotIn("push(f.key, v, f.label)", catalog)
        self.assertNotIn("${lab} ${spec}", catalog)
        self.assertNotIn("${lab} ${v}", catalog)
        self.assertIn("禁止「规格型号：」", catalog)

    def test_css_menuboard_showtime_thicken(self) -> None:
        css = CSS.read_text(encoding="utf-8")
        for needle in (
            ".browse-surface.surface-menuboard .main-signal",
            ".browse-surface.surface-menuboard .short-tags",
            ".browse-surface.surface-showtime .main-signal",
            ".browse-surface.surface-showtime .short-tag",
            "border-left: 4px solid var(--portal-accent, #C4A574)",
            ".short-tag-k",
            ".short-tag-v",
            "content: '：'",
        ):
            self.assertIn(needle, css, f"CSS 缺 {needle}")
        # 货架同行等高 + 底栏齐底；主 CTA 钉底行、次钮轻量在上
        shelf = css[css.find(".browse-surface.surface-shelfgrid .grid") :]
        self.assertIn("align-items: stretch", shelf[:400])
        card = css[css.find(".browse-surface.surface-shelfgrid .card {") :]
        self.assertIn("height: 100%", card[:280])
        foot = css[css.find(".browse-surface.surface-shelfgrid .card-foot") :]
        self.assertIn("margin-top: auto", foot[:160])
        acts = css[css.find(".browse-surface.surface-shelfgrid .card-acts .act-primary") :]
        self.assertIn("grid-row: 2", acts[:120])
        sec = css[css.find(".browse-surface.surface-shelfgrid .card-acts .act-secondary") :]
        self.assertIn("grid-row: 1", sec[:80])


if __name__ == "__main__":
    unittest.main()
