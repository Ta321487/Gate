"""可交互控件闸 C5：工厂摘要。"""

from __future__ import annotations

import unittest

from app.bake.form_controls_contract import PATTERN_IDS
from app.bake.form_controls_gate_status import form_controls_gate_snapshot


class FormControlsGateStatusTests(unittest.TestCase):
    def test_snapshot_shape_and_baseline_ok(self) -> None:
        snap = form_controls_gate_snapshot()
        self.assertIn("ok", snap)
        self.assertIn("summary", snap)
        self.assertIn("contract", snap)
        self.assertIn("bake", snap)
        self.assertTrue(snap["ok"], snap["summary"])
        self.assertTrue(snap["contract"]["ok"], snap["contract"])
        self.assertEqual(snap["contract"]["finding_count"], 0)
        self.assertEqual(set(snap["patterns"]), set(PATTERN_IDS))
        self.assertEqual(snap["bake"]["gate_key"], "p3controls")

    def test_known_debt_surfaced(self) -> None:
        snap = form_controls_gate_snapshot()
        # C1 allow-create + C2/C3 记账须仍被扫到
        self.assertGreaterEqual(snap["contract"]["known_debt_count"], 18)
        self.assertGreaterEqual(snap["contract"]["hit_count"], 18)


if __name__ == "__main__":
    unittest.main()
