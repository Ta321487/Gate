"""交付复审：单调性、指纹与分区。"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from pathlib import Path

from app.services import delivery_review as dr


class DeliveryReviewTests(unittest.TestCase):
    def test_compare_monotonic_detects_checklist_regression(self):
        prev = [{"name": "登录", "result": "done"}, {"name": "报修", "result": "pending"}]
        new = [{"name": "登录", "result": "pending"}, {"name": "报修", "result": "pending"}]
        ok, reg = dr.compare_monotonic(prev_checklist=prev, new_checklist=new, prev_gates={}, new_gates={})
        self.assertFalse(ok)
        self.assertTrue(any(r["kind"] == "checklist" for r in reg))

    def test_compare_monotonic_gate_regression(self):
        prev_g = {"p2": {"ok": True, "label": "主流程"}}
        new_g = {"p2": {"ok": False, "label": "主流程"}}
        ok, reg = dr.compare_monotonic(
            prev_checklist=[],
            new_checklist=[],
            prev_gates=prev_g,
            new_gates=new_g,
            frozen_gates={"p2": True},
        )
        self.assertFalse(ok)
        self.assertTrue(any(r["kind"] == "gate" for r in reg))

    def test_partition_zones(self):
        checklist = [
            {"name": "登录", "result": "done"},
            {"name": "报修", "result": "pending"},
            {"name": "真支付", "result": "out_of_mvp"},
        ]
        zones = dr.partition_zones(checklist, [{"text": "a", "status": "open"}], ["登录"])
        self.assertEqual(len(zones["safe_zone"]), 1)
        self.assertEqual(len(zones["poison_zone"]), 1)

    def test_workspace_hash_stable(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws"
            (ws / "frontend/src").mkdir(parents=True)
            (ws / "sql").mkdir(parents=True)
            (ws / "README.md").write_text("demo", encoding="utf-8")
            (ws / "frontend/src/App.vue").write_text("<template>ok</template>", encoding="utf-8")
            h1 = dr.workspace_delivery_hash(ws)
            h2 = dr.workspace_delivery_hash(ws)
            self.assertEqual(h1, h2)
            (ws / "frontend/src/App.vue").write_text("<template>changed</template>", encoding="utf-8")
            self.assertNotEqual(h1, dr.workspace_delivery_hash(ws))

    def test_is_zip_stale(self):
        p = SimpleNamespace(
            workspace_path="",
            delivery_review={"workspace_hash_at_pack": "abc"},
        )
        self.assertFalse(dr.is_zip_stale(p))

    def test_can_repack_blocks_open_notes(self):
        verify = {"monotonic_ok": True, "round_pass": True}
        review = {"fix_notes": [{"id": "1", "text": "x", "status": "open"}]}
        ok, msg = dr.can_repack_after_verify(verify, review)
        self.assertFalse(ok)
        self.assertIn("偏差", msg)

    def test_apply_qa_warn_blocks_when_enabled(self):
        gates = {"overall": True, "zip_allowed": True, "p0a": {"ok": True}}
        qa = {
            "ok": True,
            "summary": "warn",
            "findings": [{"level": "warn", "msg": "措辞", "where": "x"}],
        }
        dr.apply_qa_to_gates(gates, qa, warn_blocks=True)
        self.assertFalse(gates["p3q"]["ok"])
        self.assertFalse(gates["zip_allowed"])

    def test_forbid_full_rebake_active_review(self):
        p = SimpleNamespace(delivery_review={"status": "active"})
        self.assertIsNone(dr.forbid_full_rebake(p, 0))
        self.assertIsNone(dr.forbid_full_rebake(p, 2))
        self.assertEqual(dr.forbid_full_rebake(p, 4), 4)


if __name__ == "__main__":
    unittest.main()
