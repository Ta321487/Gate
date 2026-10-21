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
            'class="more-hint"',
            'class="promo promo-bar"',
            "cardVoice === 'story' ? cardPreviewFields : []",
        ):
            self.assertIn(needle, vue, f"vue 缺 {needle}")

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

    def test_css_menuboard_showtime_thicken(self) -> None:
        css = CSS.read_text(encoding="utf-8")
        for needle in (
            ".browse-surface.surface-menuboard .main-signal",
            ".browse-surface.surface-menuboard .short-tags",
            ".browse-surface.surface-showtime .main-signal",
            ".browse-surface.surface-showtime .short-tag",
            "border-left: 4px solid var(--portal-accent, #C4A574)",
        ):
            self.assertIn(needle, css, f"CSS 缺 {needle}")


if __name__ == "__main__":
    unittest.main()
