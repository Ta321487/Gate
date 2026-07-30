"""开题扫词挂两级审 / 附件 / 申报截止：只增不减。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import attach_accept, build_domain_schema
from app.bake.engine_sql import domain_sql
from app.bake.features.ticket_flow_opts import (
    enrich_ticket_flags_from_proposal,
    scan_apply_deadline,
    scan_require_attach,
    scan_two_level,
)
from app.bake.schema.templates import SCHEMA_BUILDERS


class TicketFlowOptsScanTests(unittest.TestCase):
    def test_scan_positive_and_negation(self) -> None:
        self.assertTrue(scan_two_level("学院初审通过后由资助办终审。"))
        self.assertTrue(scan_two_level("支持两级审批与待终审。"))
        self.assertFalse(scan_two_level("本期不实现两级审批。"))
        self.assertFalse(scan_two_level("仅单级审核通过或驳回。"))

        self.assertTrue(scan_require_attach("学生须上传证明与佐证材料。"))
        self.assertTrue(scan_require_attach("报修请上传现场照片。"))
        self.assertFalse(scan_require_attach("本期不要求上传附件。"))
        self.assertFalse(scan_require_attach("在线填写申请理由即可。"))

        self.assertTrue(scan_apply_deadline("各项目设置申报截止日期。"))
        self.assertTrue(scan_apply_deadline("活动报名截止后不可再报。"))
        self.assertFalse(scan_apply_deadline("本期不实现申报截止，随到随审。"))
        self.assertFalse(scan_apply_deadline("系统支持审核与办结。"))  # 裸词不够

    def test_enrich_flags_only_adds(self) -> None:
        base = {"twoLevelApprove": True, "requireAttach": False}
        out = enrich_ticket_flags_from_proposal(base, "请上传材料后提交")
        self.assertTrue(out["twoLevelApprove"])  # 原 True 保留
        self.assertTrue(out["requireAttach"])
        untouched = enrich_ticket_flags_from_proposal(
            {"twoLevelApprove": False, "requireAttach": False},
            "普通审核与办结",
        )
        self.assertFalse(untouched.get("twoLevelApprove"))
        self.assertFalse(untouched.get("requireAttach"))

    def test_fund_default_unchanged_without_signals(self) -> None:
        schema = build_domain_schema("高校学生资助系统", "DOM-FUND", proposal_text="")
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertFalse(ticket.get("twoLevelApprove"))
        self.assertFalse(ticket.get("requireAttach"))
        arch = (schema.get("entities") or {}).get("archive") or {}
        keys = {f.get("key") for f in (arch.get("fields") or []) if isinstance(f, dict)}
        self.assertNotIn("applyDeadlineAt", keys)

        spec = attach_accept(
            {
                "domain": "DOM-FUND",
                "title": "高校学生资助系统",
                "capabilities": ["archive", "ticket_flow", "content", "org_users"],
                "features": [],
            },
            "学生浏览资助项目并提交申请，管理人员审核通过或驳回。",
        )
        ticket2 = ((spec.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(ticket2.get("twoLevelApprove"))
        self.assertFalse(ticket2.get("requireAttach"))
        sql = domain_sql(
            "DOM-FUND",
            "thesis_test",
            title="高校学生资助系统",
            proposal_text="学生提交申请，管理人员审核。",
        )
        self.assertNotIn("attach_url", sql)
        # 模板本身无申报截止列
        self.assertNotIn("apply_deadline_at", sql)

    def test_fund_proposal_mounts_all_three(self) -> None:
        body = (
            "学生资助申请须学院初审与资助办终审；"
            "提交时上传证明与佐证材料；"
            "各项目设置申报截止日期，逾期不可申请。"
        )
        spec = attach_accept(
            {
                "domain": "DOM-FUND",
                "title": "高校学生资助奖学金申请系统",
                "capabilities": ["archive", "ticket_flow", "content", "org_users"],
                "features": [],
            },
            body,
        )
        ticket = ((spec.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("twoLevelApprove"))
        self.assertTrue(ticket.get("requireAttach"))
        self.assertIn("pending_final", ticket.get("states") or {})
        arch = ((spec.get("schema") or {}).get("entities") or {}).get("archive") or {}
        fields = {f.get("key"): f for f in (arch.get("fields") or []) if isinstance(f, dict)}
        self.assertIn("applyDeadlineAt", fields)
        self.assertEqual(fields["applyDeadlineAt"].get("label"), "申报截止")
        feat_names = {
            str(f.get("name"))
            for f in (spec.get("features") or [])
            if isinstance(f, dict)
        }
        self.assertIn("两级审批", feat_names)
        self.assertIn("附件上传", feat_names)
        self.assertIn("申报截止", feat_names)

        sql = domain_sql(
            "DOM-FUND",
            "thesis_test",
            title="高校学生资助奖学金申请系统",
            proposal_text=body,
            ticket_flags=ticket,
        )
        self.assertIn("attach_url", sql)
        self.assertIn("apply_deadline_at", sql)
        # 不得误加借阅逾期壳
        self.assertNotIn("fine_yuan", sql.split("fund_apply")[1].split("CREATE TABLE")[0])

    def test_dorm_default_two_level_survives_empty_proposal(self) -> None:
        """宿舍域默认两级+附件：空开题不得关掉。"""
        schema = SCHEMA_BUILDERS["DOM-DORM"]("宿舍报修")
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("twoLevelApprove"))
        self.assertTrue(ticket.get("requireAttach"))
        spec = attach_accept(
            {
                "domain": "DOM-DORM",
                "title": "宿舍报修系统",
                "capabilities": ["ticket_flow", "content", "org_users"],
                "features": [],
            },
            "学生提交报修，宿管受理。",
        )
        ticket2 = ((spec.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket2.get("twoLevelApprove"))
        self.assertTrue(ticket2.get("requireAttach"))

    def test_library_deadline_cap_untouched(self) -> None:
        """借阅逾期能力不由本扫词模块加减。"""
        from app.bake.domains import DOMAIN_CAPABILITIES

        self.assertIn("deadline", DOMAIN_CAPABILITIES["DOM-LIBRARY"])
        spec = attach_accept(
            {
                "domain": "DOM-LIBRARY",
                "title": "图书借阅",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
                "features": [],
            },
            "借还图书，支持催还。设置申报截止也不应改变借阅逾期壳归属。",
        )
        self.assertIn("deadline", spec.get("capabilities") or [])


if __name__ == "__main__":
    unittest.main()
