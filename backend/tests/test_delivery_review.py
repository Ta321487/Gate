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
            {"name": "曾通过现挂", "result": "pending"},
        ]
        # frozen 不得把当前 pending 画进安全区
        zones = dr.partition_zones(
            checklist, [{"text": "a", "status": "open"}], ["登录", "曾通过现挂"]
        )
        safe_names = {x["name"] for x in zones["safe_zone"]}
        poison_names = {x["name"] for x in zones["poison_zone"]}
        self.assertEqual(safe_names, {"登录"})
        self.assertEqual(poison_names, {"报修", "曾通过现挂"})

    def test_verify_fail_reasons_lists_pending(self):
        reasons = dr.verify_fail_reasons(
            mono_ok=True,
            zip_allowed=True,
            poison_pending=[{"name": "商家入驻"}, {"name": "库存预警"}],
            open_notes=[],
        )
        self.assertTrue(any("商家入驻" in r for r in reasons))

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

    def test_blocking_gates_listed(self):
        gates = {
            "overall": False,
            "zip_allowed": False,
            "p0a": {"ok": True, "label": "结构"},
            "p3q": {"ok": False, "label": "交付质量摘要", "desc": "2 项 error"},
        }
        blocked = dr.blocking_gates(gates)
        self.assertEqual(len(blocked), 1)
        self.assertEqual(blocked[0]["key"], "p3q")
        self.assertIn("质量摘要", blocked[0]["label"])

    def test_can_repack_mentions_blocking_gate(self):
        verify = {
            "monotonic_ok": True,
            "round_pass": False,
            "gates": {
                "p3q": {"ok": False, "label": "交付质量摘要", "desc": "error"},
                "zip_allowed": False,
            },
            "round": {"pending_count": 0},
        }
        ok, msg = dr.can_repack_after_verify(verify, {})
        self.assertFalse(ok)
        self.assertIn("质量检查", msg)
        self.assertIn("交付质量摘要", msg)

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

    def test_review_status_of(self):
        p = SimpleNamespace(delivery_review={"status": "active"})
        self.assertEqual(dr.review_status_of(p), "active")
        p = SimpleNamespace(delivery_review={})
        self.assertEqual(dr.review_status_of(p), "idle")

    def test_require_pre_generate_ack_no_material(self):
        p = SimpleNamespace(source_path=None, source_filename=None, delivery_review={})
        self.assertIsNone(dr.require_pre_generate_ack(p))


if __name__ == "__main__":
    unittest.main()
