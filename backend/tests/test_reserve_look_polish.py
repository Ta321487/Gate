"""预约组软皮短签再磨护栏：号源/房态/车型各有短签语义，禁商城价签腔。"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FE = REPO / "skeletons" / "baseline" / "frontend" / "src" / "views" / "user"
SETUP = FE / "ArchiveBrowse.setup.js"
CSS = FE / "ArchiveBrowse.css"


class ReserveLookPolishTests(unittest.TestCase):
    def test_reserve_short_tags(self) -> None:
        setup = SETUP.read_text(encoding="utf-8")
        for needle in (
            "reserveSurface.value === 'slotstrip'",
            "reserveSurface.value === 'roomstate'",
            "reserveSurface.value === 'vehiclecard'",
            "push('seats'",
            "push('when'",
            "slotHint",
        ):
            self.assertIn(needle, setup, f"setup 缺 {needle}")
        # 短签块在 catalog 早退之前
        i_slot = setup.find("reserveSurface.value === 'slotstrip'")
        i_catalog = setup.find("if (cardVoice.value !== 'catalog') return []")
        self.assertGreater(i_slot, 0)
        self.assertGreater(i_catalog, i_slot)

    def test_reserve_short_tags_css(self) -> None:
        css = CSS.read_text(encoding="utf-8")
        for needle in (
            ".browse-surface.surface-slotstrip .short-tags",
            ".browse-surface.surface-roomstate .short-tags",
            ".browse-surface.surface-vehiclecard .short-tags",
        ):
            self.assertIn(needle, css, f"CSS 缺 {needle}")


if __name__ == "__main__":
    unittest.main()
