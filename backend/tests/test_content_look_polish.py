"""内容组软皮短签再磨护栏：刊头/封面墙/清单/双栏各有短签语义，禁价签腔。"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FE = REPO / "skeletons" / "baseline" / "frontend" / "src" / "views" / "user"
SETUP = FE / "ArchiveBrowse.setup.js"
CSS = FE / "ArchiveBrowse.css"


class ContentLookPolishTests(unittest.TestCase):
    def test_content_short_tags(self) -> None:
        setup = SETUP.read_text(encoding="utf-8")
        for needle in (
            "contentSurface.value === 'folio'",
            "contentSurface.value === 'coverwall'",
            "contentSurface.value === 'ledger'",
            "contentSurface.value === 'splitdesk'",
            "coverWallActive.value",
            "push('artist'",
            "push('kind'",
            "push('tag'",
        ):
            self.assertIn(needle, setup, f"setup 缺 {needle}")
        i_folio = setup.find("contentSurface.value === 'folio'")
        # 短签分支在 cardShortTags 内、catalog 早退之前
        fn = setup.find("function cardShortTags(row)")
        i_catalog = setup.find("if (cardVoice.value !== 'catalog') return []", fn)
        self.assertGreater(i_folio, fn)
        self.assertGreater(i_catalog, i_folio)

    def test_content_short_tags_css(self) -> None:
        css = CSS.read_text(encoding="utf-8")
        for needle in (
            ".surface-folio .short-tags",
            ".surface-coverwall .short-tags",
            ".surface-ledger .short-tags",
            ".surface-splitdesk-list .short-tags",
        ):
            self.assertIn(needle, css, f"CSS 缺 {needle}")


if __name__ == "__main__":
    unittest.main()
