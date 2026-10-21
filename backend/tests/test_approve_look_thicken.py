"""审批组观感加厚（typelist / inboxsteps）交付护栏。

钉住：
- MyTickets 两档 surface + 事项类型短签 / 步骤条 tone；
- TicketsAdmin 收件箱顶栏待我审分档；
- CSS 走 portal / --approve-tone，禁死色表。
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FE = REPO / "skeletons" / "baseline" / "frontend" / "src" / "views"
MY = FE / "user" / "MyTickets.vue"
ADMIN = FE / "admin" / "TicketsAdmin.vue"


class ApproveLookThickenTests(unittest.TestCase):
    def test_mytickets_approve_faces(self) -> None:
        text = MY.read_text(encoding="utf-8")
        for needle in (
            "'surface-typelist': approveSurface === 'typelist'",
            "'surface-inboxsteps': approveSurface === 'inboxsteps'",
            ':data-approve-surface="approveSurface || undefined"',
            'class="matter-type"',
            ".list.surface-typelist .matter-type",
            ".list.surface-inboxsteps .card[data-ticket-tone='pending']",
            "--approve-tone",
        ):
            self.assertIn(needle, text, f"MyTickets 缺 {needle}")
        # 旧死色步骤点已撤（勿再硬画 ●○○）
        self.assertNotIn("content: '● ○ ○'", text)
        for dead in ("#6b8aa8", "#4f76d9", "#d08a32", "#4f9a6a", "#9aa3ad"):
            self.assertNotIn(dead, text, f"MyTickets 审批 CSS 仍留死色 {dead}")

    def test_tickets_admin_inbox_bar(self) -> None:
        text = ADMIN.read_text(encoding="utf-8")
        for needle in (
            "'surface-typelist': approveSurface === 'typelist'",
            "'surface-inboxsteps': approveSurface === 'inboxsteps'",
            "const approveInboxStats = computed",
            'data-approve-inbox="stats"',
            "待我审 {{ approveInboxStats.total }}",
            ".approve-inbox-bar",
            ".approve-desk.surface-typelist :deep(.el-table)",
        ):
            self.assertIn(needle, text, f"TicketsAdmin 缺 {needle}")
        for dead in ("#6b8aa8", "#4f76d9", "#d08a32", "#4f9a6a", "#9aa3ad"):
            self.assertNotIn(dead, text, f"TicketsAdmin CSS 仍留死色 {dead}")


if __name__ == "__main__":
    unittest.main()
