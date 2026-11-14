"""出包门禁快照：按 Job 落库、历史不覆盖。"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from app.services.gate_report import (
    GATE_ROW_KEYS,
    attach_gate_report,
    build_gate_report,
    gate_rows_from_map,
)


class GateReportBuildTests(unittest.TestCase):
    def test_rows_match_console_shape(self) -> None:
        gates = {
            "overall": False,
            "zip_allowed": False,
            "p0a": {"ok": True, "label": "后端骨架", "desc": ""},
            "p0b": {"ok": True, "label": "前端骨架", "desc": ""},
            "p2": {
                "ok": False,
                "label": "领域主流程 E2E",
                "desc": "申请借阅 → 审核 → 归还",
            },
            "p3lean": {
                "ok": False,
                "label": "学生包瘦身 · ZIP 最终确认",
                "desc": "死依赖：pom:lombok",
            },
            "p3layout": {
                "ok": False,
                "label": "布局检查",
                "desc": "结构契约 14：…共 14 条",
                "detail": {"findings": ["a"] * 14},
            },
            "checklist": [{"name": "借阅", "result": "done"}],
        }
        report = build_gate_report(gates)
        self.assertFalse(report["overall"])
        self.assertFalse(report["zip_allowed"])
        keys = [r["key"] for r in report["rows"]]
        self.assertEqual(keys, ["p0a", "p0b", "p2", "p3lean", "p3layout"])
        lean = next(r for r in report["rows"] if r["key"] == "p3lean")
        self.assertEqual(lean["level"], "P3")
        self.assertFalse(lean["ok"])
        self.assertIn("lombok", lean["desc"])
        self.assertEqual(report["checklist"][0]["name"], "借阅")
        self.assertNotIn("checklist", report["gates"])
        # 落库瘦身：不带 detail / findings
        self.assertNotIn("detail", report["gates"]["p3layout"])
        self.assertIn("共 14 条", report["gates"]["p3layout"]["desc"])

    def test_checklist_arg_overrides_embedded(self) -> None:
        report = build_gate_report(
            {"p1": {"ok": True, "label": "登录", "desc": ""}, "checklist": [{"name": "旧"}]},
            checklist=[{"name": "新", "result": "pending"}],
        )
        self.assertEqual(report["checklist"][0]["name"], "新")

    def test_desc_soft_cap(self) -> None:
        huge = "x" * 9000
        rows = gate_rows_from_map({"p2": {"ok": False, "label": "E2E", "desc": huge}})
        self.assertEqual(len(rows), 1)
        self.assertLessEqual(len(rows[0]["desc"]), 4000)
        self.assertTrue(rows[0]["desc"].endswith("…"))

    def test_row_key_order_stable(self) -> None:
        gate_map = {k: {"ok": True, "label": k, "desc": ""} for k in reversed(GATE_ROW_KEYS)}
        keys = [r["key"] for r in gate_rows_from_map(gate_map)]
        self.assertEqual(keys, list(GATE_ROW_KEYS))


class GateReportAttachTests(unittest.TestCase):
    def test_each_job_keeps_own_snapshot(self) -> None:
        """两次出包 = 两个 Job；后一次写入不得改前一次。"""
        job1 = SimpleNamespace(gate_report=None)
        job2 = SimpleNamespace(gate_report=None)
        attach_gate_report(
            job1,
            {"overall": False, "p2": {"ok": False, "label": "E2E", "desc": "第一次红"}},
        )
        attach_gate_report(
            job2,
            {"overall": True, "p2": {"ok": True, "label": "E2E", "desc": "第二次绿"}},
        )
        self.assertIn("第一次红", job1.gate_report["rows"][0]["desc"])
        self.assertFalse(job1.gate_report["overall"])
        self.assertIn("第二次绿", job2.gate_report["rows"][0]["desc"])
        self.assertTrue(job2.gate_report["overall"])
        # 再改 job2 也不应动到 job1
        attach_gate_report(
            job2,
            {"overall": False, "p3lean": {"ok": False, "label": "瘦身", "desc": "第三次"}},
        )
        self.assertIn("第一次红", job1.gate_report["rows"][0]["desc"])
        self.assertEqual(job2.gate_report["rows"][0]["key"], "p3lean")


if __name__ == "__main__":
    unittest.main()
