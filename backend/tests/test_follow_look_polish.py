"""跟进组软皮短签再磨护栏：看板/档案看责任人·栏目；挂牌看户型·地段。"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FE = REPO / "skeletons" / "baseline" / "frontend" / "src" / "views" / "user"
SETUP = FE / "ArchiveBrowse.setup.js"
CSS = FE / "ArchiveBrowse.css"


class FollowLookPolishTests(unittest.TestCase):
    def test_follow_short_tags(self) -> None:
        setup = SETUP.read_text(encoding="utf-8")
        fn = setup.find("function cardShortTags(row)")
        self.assertGreater(fn, 0)
        body = setup[fn:]
        for needle in (
            "followSurface.value === 'pipeline'",
            "followSurface.value === 'dossier'",
            "followSurface.value === 'listing'",
            "push('owner'",
            "push('layout'",
            "push('area'",
        ):
            self.assertIn(needle, body, f"cardShortTags 缺 {needle}")
        i_follow = body.find("followSurface.value === 'pipeline'")
        i_catalog = body.find("if (cardVoice.value !== 'catalog') return []")
        self.assertGreater(i_catalog, i_follow)

    def test_follow_short_tags_css(self) -> None:
        css = CSS.read_text(encoding="utf-8")
        for needle in (
            ".browse-surface.surface-pipeline .short-tags",
            ".browse-surface.surface-dossier .short-tags",
            ".browse-surface.surface-listing .short-tags",
        ):
            self.assertIn(needle, css, f"CSS 缺 {needle}")


if __name__ == "__main__":
    unittest.main()
