"""报名组软皮短签再磨护栏：海报/课表/启事/线路各有短签语义。"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FE = REPO / "skeletons" / "baseline" / "frontend" / "src" / "views" / "user"
SETUP = FE / "ArchiveBrowse.setup.js"
CSS = FE / "ArchiveBrowse.css"


class ApplyLookPolishTests(unittest.TestCase):
    def test_apply_short_tags(self) -> None:
        setup = SETUP.read_text(encoding="utf-8")
        fn = setup.find("function cardShortTags(row)")
        self.assertGreater(fn, 0)
        for needle in (
            "applySurface.value === 'eventposter'",
            "applySurface.value === 'coursetable'",
            "applySurface.value === 'noticeboard'",
            "applySurface.value === 'tourcard'",
            "push('place'",
            "push('room'",
            "push('teacher'",
            "push('dest'",
        ):
            self.assertIn(needle, setup[fn:], f"cardShortTags 缺 {needle}")
        i_apply = setup.find("applySurface.value === 'eventposter'", fn)
        i_catalog = setup.find("if (cardVoice.value !== 'catalog') return []", fn)
        self.assertGreater(i_catalog, i_apply)

    def test_apply_short_tags_css(self) -> None:
        css = CSS.read_text(encoding="utf-8")
        for needle in (
            ".browse-surface.surface-eventposter .short-tags",
            ".browse-surface.surface-coursetable .short-tags",
            ".browse-surface.surface-noticeboard .short-tags",
            ".browse-surface.surface-tourcard .short-tags",
        ):
            self.assertIn(needle, css, f"CSS 缺 {needle}")


if __name__ == "__main__":
    unittest.main()
