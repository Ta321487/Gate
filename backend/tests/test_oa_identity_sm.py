# -*- coding: utf-8 -*-
"""OA/车证场景身份 + 审批完结状态机回归。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import build_domain_schema
from app.bake.engine_sql import domain_sql
from app.bake.identity_align import check_identity_alignment
from app.bake.profile_fields import profile_fields_for
from app.bake.scene_scan import scene_for


def _id_opts(domain: str, title: str, body: str = "") -> list[str]:
    fields = profile_fields_for(domain, title=title, proposal_text=body)
    for f in fields:
        if f.get("key") == "identityType":
            return list(f.get("options") or [])
    return []


def _aef(domain: str, title: str) -> bool:
    sch = build_domain_schema(title, domain, proposal_text=title)
    ents = sch.get("entities") or {}
    if isinstance(ents, dict):
        for ent in ents.values():
            if isinstance(ent, dict) and "approveEndsFlow" in ent:
                return bool(ent.get("approveEndsFlow"))
    elif isinstance(ents, list):
        for ent in ents:
            if isinstance(ent, dict) and "approveEndsFlow" in ent:
                return bool(ent.get("approveEndsFlow"))
    return False


def _states(domain: str, title: str) -> dict:
    sch = build_domain_schema(title, domain, proposal_text=title)
    ents = sch.get("entities") or {}
    if isinstance(ents, dict):
        for ent in ents.values():
            if isinstance(ent, dict) and ent.get("states"):
                return dict(ent.get("states") or {})
    elif isinstance(ents, list):
        for ent in ents:
            if isinstance(ent, dict) and ent.get("states"):
                return dict(ent.get("states") or {})
    return {}


class OaCarpassIdentityTests(unittest.TestCase):
    def test_expense_enterprise_no_campus_identity(self) -> None:
        title = "企业差旅经费报销管理系统"
        body = "公司员工提交报销单，财务审批"
        self.assertEqual(scene_for("DOM-EXPENSE", title, body), "enterprise")
        opts = _id_opts("DOM-EXPENSE", title, body)
        self.assertIn("员工", opts)
        self.assertNotIn("学生", opts)
        self.assertNotIn("教职工", opts)
        sql = domain_sql("DOM-EXPENSE", "t", title=title, proposal_text=body)
        issues = check_identity_alignment(
            "DOM-EXPENSE", title=title, proposal_text=body, sql=sql
        )
        self.assertEqual(issues, [])

    def test_expense_campus_keeps_campus_identity(self) -> None:
        title = "高校差旅经费报销管理系统"
        self.assertEqual(scene_for("DOM-EXPENSE", title, ""), "campus")
        opts = _id_opts("DOM-EXPENSE", title, "")
        self.assertIn("教职工", opts)

    def test_seal_enterprise_identity(self) -> None:
        title = "公司行政用章申请审批系统"
        self.assertEqual(scene_for("DOM-SEAL", title, ""), "enterprise")
        opts = _id_opts("DOM-SEAL", title, "")
        self.assertNotIn("学生", opts)

    def test_carpass_park_enterprise(self) -> None:
        title = "产业园区临时车辆通行证备案系统"
        self.assertEqual(scene_for("DOM-CARPASS", title, ""), "enterprise")
        opts = _id_opts("DOM-CARPASS", title, "")
        self.assertIn("员工", opts)
        self.assertNotIn("学生", opts)
        sql = domain_sql("DOM-CARPASS", "t", title=title, proposal_text="")
        issues = check_identity_alignment(
            "DOM-CARPASS", title=title, proposal_text="", sql=sql
        )
        self.assertEqual(issues, [])

    def test_fitout_community_owner(self) -> None:
        title = "小区业主装修备案与进场施工申请系统"
        self.assertEqual(scene_for("DOM-FITOUT", title, ""), "community")
        opts = _id_opts("DOM-FITOUT", title, "")
        self.assertIn("业主", opts)
        self.assertNotIn("学生", opts)


class ApproveEndsFlowTests(unittest.TestCase):
    def test_oa_and_stuwork_approve_ends(self) -> None:
        cases = [
            ("DOM-EXPENSE", "经费报销系统"),
            ("DOM-SEAL", "用章申请系统"),
            ("DOM-CREDIT", "第二课堂学分认定系统"),
            ("DOM-MORAL", "综测申报系统"),
            ("DOM-LABOR", "劳动时长认定系统"),
            ("DOM-AWARD", "成果登记系统"),
            ("DOM-CARPASS", "车辆通行证系统"),
        ]
        for dom, title in cases:
            with self.subTest(domain=dom):
                self.assertTrue(_aef(dom, title), f"{dom} approveEndsFlow")
                st = _states(dom, title)
                self.assertNotIn("overdue", st, f"{dom} dead overdue")


if __name__ == "__main__":
    unittest.main()
