"""泳道 E · C-02：LABSAFE 先考后申（挂 exam + require-before-ticket）。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.catalog import match_text
from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.exam import EXAM_CAP, scan_exam_gate_ticket

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples" / "考试预设开题"


class LabsafeExamGateC02Tests(unittest.TestCase):
    def test_gate_scan(self) -> None:
        self.assertTrue(scan_exam_gate_ticket("实验室安全准入考试与申请", "DOM-LABSAFE"))
        self.assertFalse(scan_exam_gate_ticket("实验室安全准入考试与申请", "DOM-EXAM"))
        self.assertFalse(scan_exam_gate_ticket("仅准入申请审核", "DOM-LABSAFE"))

    def test_match_labsafe(self) -> None:
        got = match_text(
            "基于 Spring Boot 的实验室安全准入考试与申请系统的设计与实现。"
            "主要功能：安全准入考试、考试通过后提交准入申请审核。"
        )
        self.assertEqual(got.domain, "DOM-LABSAFE", f"hits={got.hits[:12]}")

    def test_attach_adds_exam_and_gate(self) -> None:
        spec = attach_accept(
            {
                "domain": "DOM-LABSAFE",
                "title": "实验室安全准入考试与申请系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-LABSAFE"]),
                "archetype": "ARCH-FLOW",
            },
            "主要功能：先考试后申请；安全准入考试通过后提交入室许可申请。",
        )
        self.assertIn(EXAM_CAP, spec.get("capabilities") or [])
        sch = spec.get("schema") or {}
        self.assertTrue(sch.get("examGateTicket"))
        self.assertEqual(sch.get("examSkin"), "safety")
        ticket = (sch.get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("requireExamPass"))
        user_keys = {m.get("key") for m in (sch.get("menus") or {}).get("user") or []}
        self.assertIn("exam_papers", user_keys)

    def test_sql_and_yml(self) -> None:
        body = "安全准入考试、先考试后申请入室许可"
        sql = domain_sql(
            "DOM-LABSAFE",
            "t_labsafe_exam",
            title="实验室安全准入考试与申请系统",
            proposal_text=body,
        )
        self.assertIn("exam_question", sql)
        self.assertIn("gate_ticket", sql)
        self.assertIn("实验室安全准入考试卷", sql)
        spec = attach_accept(
            {
                "domain": "DOM-LABSAFE",
                "title": "实验室安全准入考试与申请系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-LABSAFE"]),
                "archetype": "ARCH-FLOW",
            },
            body,
        )
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-LABSAFE", spec)
        self.assertIn("exam-enabled: true", yml)
        self.assertIn("exam-require-before-ticket: true", yml)

    def test_sample(self) -> None:
        path = SAMPLES / "C-02-DOM-LABSAFE-实验室安全准入考试与申请.txt"
        self.assertTrue(path.is_file(), path)


if __name__ == "__main__":
    unittest.main()
