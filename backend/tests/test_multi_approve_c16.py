"""泳道 E · C-16：多级会签 multi_approve（固定三级状态机，非新域）。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES
from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.features.ticket_flow_opts import (
    MULTI_APPROVE_CAP,
    scan_three_level,
    scan_two_level,
)

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "data" / "samples" / "会签预设开题"
BASELINE = ROOT / "skeletons" / "baseline"
MYBATIS = ROOT / "skeletons" / "overlays" / "persistence-mybatis"
JPA = ROOT / "skeletons" / "overlays" / "persistence-jpa"


class MultiApproveC16Tests(unittest.TestCase):
    def test_capability(self) -> None:
        self.assertIn(MULTI_APPROVE_CAP, CAPABILITIES)
        self.assertEqual(CAPABILITIES[MULTI_APPROVE_CAP]["status"], "implemented")
        # 非域默认：SEAL 等申请域仍只有 ticket_flow
        self.assertNotIn(MULTI_APPROVE_CAP, DOMAIN_CAPABILITIES["DOM-SEAL"])

    def test_scan_positive_and_negation(self) -> None:
        self.assertTrue(scan_three_level("用章申请须初审复审终审三级审批。"))
        self.assertTrue(scan_three_level("支持三级会签与科长复审。"))
        self.assertTrue(scan_two_level("三级审批"))  # 三级隐含两级
        self.assertFalse(scan_three_level("多级会签引擎不在本期。"))
        self.assertFalse(scan_three_level("本期不实现三级审批。"))
        self.assertFalse(scan_three_level("仅单级审核通过或驳回。"))

    def test_p01_negation_sample_does_not_enable(self) -> None:
        p01 = (
            ROOT
            / "data"
            / "samples"
            / "申请预设开题"
            / "P-01-DOM-SEAL-学校行政印章使用申请审批系统.txt"
        )
        body = p01.read_text(encoding="utf-8")
        self.assertIn("多级会签引擎", body)
        self.assertFalse(scan_three_level(body))
        spec = attach_accept(
            {
                "domain": "DOM-SEAL",
                "title": "学校行政印章使用申请审批系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-SEAL"]),
                "features": [],
            },
            body,
        )
        ticket = ((spec.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(ticket.get("threeLevelApprove"))
        self.assertNotIn(MULTI_APPROVE_CAP, spec.get("capabilities") or [])

    def test_positive_mounts_states_cap_yml(self) -> None:
        body = (
            "学校行政印章使用申请审批系统。"
            "用章申请须办公室初审、部门复审与校长办公室终审三级审批；"
            "终审通过后办结。"
        )
        spec = attach_accept(
            {
                "domain": "DOM-SEAL",
                "title": "学校行政印章使用申请审批系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-SEAL"]),
                "features": [],
            },
            body,
        )
        ticket = ((spec.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("threeLevelApprove"))
        self.assertTrue(ticket.get("twoLevelApprove"))
        states = ticket.get("states") or {}
        self.assertIn("pending_mid", states)
        self.assertIn("pending_final", states)
        self.assertIn(MULTI_APPROVE_CAP, spec.get("capabilities") or [])
        feat_names = {
            str(f.get("name"))
            for f in (spec.get("features") or [])
            if isinstance(f, dict)
        }
        self.assertIn("三级会签审批", feat_names)
        self.assertNotIn("两级审批", feat_names)

        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-SEAL", spec)
        self.assertIn("ticket-three-level: true", yml)
        self.assertIn("ticket-two-level: true", yml)

    def test_runtime_paths(self) -> None:
        base_store = BASELINE / "backend/src/main/java/com/thesis/capability/TicketStore.java"
        text = base_store.read_text(encoding="utf-8")
        self.assertIn("threeLevelApprove", text)
        self.assertIn("pending_mid", text)
        self.assertIn("configureThreeLevel", text)
        for root in (BASELINE, MYBATIS, JPA):
            binder = root / "backend/src/main/java/com/thesis/config/DomainRuntimeBinder.java"
            bt = binder.read_text(encoding="utf-8")
            self.assertIn("ticket-three-level", bt, msg=str(binder))
            self.assertIn("configureThreeLevel", bt, msg=str(binder))
            store = root / "backend/src/main/java/com/thesis/capability/TicketStore.java"
            st = store.read_text(encoding="utf-8")
            self.assertIn("threeLevelApprove && first", st, msg=str(store))
            self.assertIn("pending_mid", st, msg=str(store))
        mapper_xml = MYBATIS / "backend/src/main/resources/mapper/TicketMapper.xml"
        self.assertIn("updateApproveStage", mapper_xml.read_text(encoding="utf-8"))
        admin = BASELINE / "frontend/src/views/admin/TicketsAdmin.vue"
        at = admin.read_text(encoding="utf-8")
        self.assertIn("threeLevelApprove", at)
        self.assertIn("pending_mid", at)
        my = BASELINE / "frontend/src/views/user/MyTickets.vue"
        self.assertIn("pending_mid", my.read_text(encoding="utf-8"))

    def test_sample_file(self) -> None:
        samples = list(SAMPLES.glob("C-16*.txt"))
        self.assertTrue(samples, "missing C-16 sample under 会签预设开题")
        body = samples[0].read_text(encoding="utf-8")
        self.assertTrue(scan_three_level(body))
        self.assertIn("DOM-SEAL", body)


if __name__ == "__main__":
    unittest.main()
