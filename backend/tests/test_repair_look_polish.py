"""报修组短签轻磨护栏：进度流地点/类型芯片 + 故障看板分类短签。"""

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


class RepairLookPolishTests(unittest.TestCase):
    def test_ticket_short_chips(self) -> None:
        text = MY.read_text(encoding="utf-8")
        for needle in (
            'class="fault-cat"',
            'class="ticket-chip"',
            "repairSurface === 'ticketfeed' && (row.location || row.typeName)",
            ".list.surface-ticketfeed .ticket-chip",
            ".list.surface-faultboard .fault-cat",
        ):
            self.assertIn(needle, text, f"MyTickets 缺 {needle}")


if __name__ == "__main__":
    unittest.main()
