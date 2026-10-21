"""互动组软皮短签再磨护栏：资料/双选/行程各有短签语义。"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FE = REPO / "skeletons" / "baseline" / "frontend" / "src" / "views" / "user"
SETUP = FE / "ArchiveBrowse.setup.js"
CSS = FE / "ArchiveBrowse.css"


class InteractLookPolishTests(unittest.TestCase):
    def test_interact_short_tags(self) -> None:
        setup = SETUP.read_text(encoding="utf-8")
        fn = setup.find("function cardShortTags(row)")
        self.assertGreater(fn, 0)
        body = setup[fn:]
        for needle in (
            "interactSurface.value === 'profilegrid'",
            "interactSurface.value === 'mutualpick'",
            "interactSurface.value === 'triprow'",
            "push('major'",
            "push('dept'",
            "push('vehicle'",
        ):
            self.assertIn(needle, body, f"cardShortTags 缺 {needle}")
        i_interact = body.find("interactSurface.value === 'profilegrid'")
        i_catalog = body.find("if (cardVoice.value !== 'catalog') return []")
        self.assertGreater(i_catalog, i_interact)

    def test_interact_short_tags_css(self) -> None:
        css = CSS.read_text(encoding="utf-8")
        for needle in (
            ".browse-surface.surface-profilegrid .short-tags",
            ".browse-surface.surface-mutualpick .short-tags",
            ".browse-surface.surface-triprow .short-tags",
        ):
            self.assertIn(needle, css, f"CSS 缺 {needle}")


if __name__ == "__main__":
    unittest.main()
