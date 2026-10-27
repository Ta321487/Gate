"""起包前布局闸 D5：工厂摘要（对账+结构；视觉全表不在摘要里跑）。"""

from __future__ import annotations

import unittest

from app.bake.layout_gate_status import layout_gate_snapshot


class LayoutGateStatusTests(unittest.TestCase):
    def test_snapshot_shape_and_baseline_ok(self) -> None:
        snap = layout_gate_snapshot()
        self.assertIn("ok", snap)
        self.assertIn("summary", snap)
        self.assertIn("inventory", snap)
        self.assertIn("contract", snap)
        self.assertIn("smoke", snap)
        self.assertTrue(snap["inventory"]["ok"], snap["inventory"])
        self.assertTrue(snap["contract"]["ok"], snap["contract"])
        self.assertTrue(snap["ok"], snap["summary"])
        self.assertEqual(snap["smoke"]["status"], "not_run")
        self.assertGreater(snap["inventory"]["row_count"], 100)
        # 已知债可非零；意外须为零
        self.assertEqual(snap["inventory"]["issue_count"], 0)
        self.assertEqual(snap["contract"]["finding_count"], 0)

    def test_known_debt_cleared(self) -> None:
        """共享结构债消红后摘要不得再挂登记例外。"""
        snap = layout_gate_snapshot()
        self.assertEqual(snap["inventory"]["known_debt_count"], 0, snap["inventory"])
        self.assertEqual(snap["contract"]["known_debt_count"], 0, snap["contract"])
        self.assertEqual(snap["inventory"]["known_debt"], [])
        self.assertEqual(snap["contract"]["known_debt"], [])


if __name__ == "__main__":
    unittest.main()
