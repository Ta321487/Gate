"""审批组短签轻磨护栏：事项清单与待审步骤均挂 matter-type。"""

from __future__ import annotations

from tests._vue_src import vue_src

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


class ApproveLookPolishTests(unittest.TestCase):
    def test_matter_type_on_both_faces(self) -> None:
        text = vue_src(MY)
        for needle in (
            "(approveSurface === 'typelist' || approveSurface === 'inboxsteps') && row.typeName",
            'class="matter-type"',
            ".list.surface-typelist .matter-type",
            ".list.surface-inboxsteps .matter-type",
        ):
            self.assertIn(needle, text, f"MyTickets 缺 {needle}")


if __name__ == "__main__":
    unittest.main()
