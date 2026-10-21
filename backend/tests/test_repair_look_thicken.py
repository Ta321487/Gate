"""报修组观感加厚（ticketfeed / faultboard）交付护栏。

钉住：
- MyTickets 两档 surface 类与 data-repair-surface；
- 进度流 / 故障看板 CSS 加厚（tone 走 CSS 变量，禁死色表）；
- 卡片绑定 data-ticket-tone（复用 statusTone.ticketTone）；
- 故障看板顶栏待派/处理中/超时统计。
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MY = (
    REPO
    / "skeletons"
    / "baseline"
    / "frontend"
    / "src"
    / "views"
    / "user"
    / "MyTickets.vue"
)
TONE = (
    REPO
    / "skeletons"
    / "baseline"
    / "frontend"
    / "src"
    / "utils"
    / "statusTone.js"
)


class RepairLookThickenTests(unittest.TestCase):
    def test_mytickets_surface_bindings(self) -> None:
        text = MY.read_text(encoding="utf-8")
        for needle in (
            "'surface-ticketfeed': repairSurface === 'ticketfeed'",
            "'surface-faultboard': repairSurface === 'faultboard'",
            ':data-repair-surface="repairSurface || undefined"',
            ':data-ticket-tone="repairSurface ? ticketTone(row.status) : undefined"',
            "const repairBoardStats = computed",
            'data-repair-board="stats"',
            "待派 {{ repairBoardStats.pending }}",
            "处理中 {{ repairBoardStats.progress }}",
            "超时 {{ repairBoardStats.overdue }}",
            'class="fault-cat"',
        ):
            self.assertIn(needle, text, f"MyTickets 缺 {needle}")

    def test_ticket_tone_shared(self) -> None:
        tone = TONE.read_text(encoding="utf-8")
        self.assertIn("export function ticketTone(status)", tone)
        text = MY.read_text(encoding="utf-8")
        self.assertIn(
            "import { multiApproveSteps, ticketTagType, ticketTone } from '../../utils/statusTone.js'",
            text,
        )

    def test_css_thicken_two_faces(self) -> None:
        text = MY.read_text(encoding="utf-8")
        for needle in (
            ".list.surface-ticketfeed .card[data-ticket-tone='pending']",
            ".list.surface-ticketfeed .card[data-ticket-tone='ok']",
            "var(--repair-tone)",
            ".list.surface-faultboard .card[data-ticket-tone='danger']",
            ".list.surface-faultboard .fault-cat",
            ".repair-board-bar",
        ):
            self.assertIn(needle, text, f"CSS 缺 {needle}")
        for dead in ("#6b8aa8", "#4f76d9", "#d08a32", "#4f9a6a", "#9aa3ad"):
            self.assertNotIn(dead, text, f"报修 CSS 仍留死色 {dead}")


if __name__ == "__main__":
    unittest.main()
