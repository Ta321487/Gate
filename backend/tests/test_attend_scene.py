"""DOM-ATTEND：题名/开题双扫（同 _food_schema），走学工或人事口径。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import attach_accept, build_domain_schema
from app.bake.schema.templates import SCHEMA_BUILDERS


class AttendTitleCopyTests(unittest.TestCase):
    def test_student_title_campus_copy(self) -> None:
        schema = SCHEMA_BUILDERS["DOM-ATTEND"]("学生请假销假管理系统")
        roles = schema["roles"]
        self.assertEqual(roles["user"]["label"], "学生")
        self.assertEqual(roles["admin"]["label"], "学工主管（总管）")
        self.assertEqual(roles["subadmin"]["label"], "辅导员")
        self.assertEqual(schema["labels"]["noticePageTitle"], "学工公告")
        self.assertEqual(schema["menus"]["user"][0]["label"], "学生名册")
        fields = {f["key"]: f["label"] for f in schema["entities"]["archive"]["fields"]}
        self.assertEqual(fields["author"], "院系/班级")
        self.assertEqual(fields["isbn"], "学号备注")
        self.assertEqual(fields["category"], "学生类型")
        leads = " ".join(b.get("lead", "") for b in schema.get("portalBanners") or [])
        self.assertNotIn("人事", leads)
        self.assertNotIn("工号", leads)
        self.assertNotIn("岗位类型", leads)

    def test_proposal_body_without_student_in_title(self) -> None:
        """题名不含学生时，开题正文写到仍走学工口径。"""
        schema = build_domain_schema(
            "请销假在线审批系统",
            "DOM-ATTEND",
            proposal_text=(
                "本系统面向高校学生请假与销假管理，由辅导员审批，维护院系与学号。"
            ),
        )
        self.assertEqual(schema["roles"]["user"]["label"], "学生")
        self.assertEqual(schema["roles"]["admin"]["label"], "学工主管（总管）")
        self.assertEqual(schema["roles"]["subadmin"]["label"], "辅导员")

    def test_attach_accept_rebuilds_from_proposal(self) -> None:
        spec = {
            "title": "假勤管理系统",
            "domain": "DOM-ATTEND",
            "archetype": "ARCH-FLOW",
            "schema": SCHEMA_BUILDERS["DOM-ATTEND"]("假勤管理系统"),
        }
        self.assertEqual(spec["schema"]["roles"]["admin"]["label"], "人事主管（总管）")
        out = attach_accept(
            spec,
            "主要功能：学生请假申请、班级辅导员审批与销假台账。",
        )
        self.assertEqual(out["schema"]["roles"]["user"]["label"], "学生")
        self.assertEqual(out["schema"]["roles"]["admin"]["label"], "学工主管（总管）")

    def test_staff_posts_follow_subadmin(self) -> None:
        schema = build_domain_schema("学生请假销假管理系统", "DOM-ATTEND")
        self.assertEqual(schema["roles"]["subadmin"]["label"], "辅导员")
        posts = schema["roles"].get("staff_posts") or []
        attend = next(p for p in posts if p.get("id") == "attend_clerk")
        self.assertEqual(attend["label"], "辅导员")

    def test_enterprise_title_keeps_hr_copy(self) -> None:
        schema = SCHEMA_BUILDERS["DOM-ATTEND"]("企业员工考勤请假管理系统")
        self.assertEqual(schema["roles"]["user"]["label"], "员工/学生")
        self.assertEqual(schema["roles"]["admin"]["label"], "人事主管（总管）")
        self.assertEqual(schema["labels"]["noticePageTitle"], "人事公告")

    def test_golden_title_unchanged(self) -> None:
        schema = SCHEMA_BUILDERS["DOM-ATTEND"]("测试课题")
        self.assertEqual(schema["roles"]["admin"]["label"], "人事主管（总管）")
        self.assertEqual(schema["roles"]["user"]["label"], "员工/学生")

    def test_profile_student_first(self) -> None:
        schema = build_domain_schema("学生请假销假管理系统", "DOM-ATTEND")
        ident = next(f for f in schema["profileFields"] if f["key"] == "identityType")
        self.assertEqual(ident["options"][0], "学生")
        dept = next(f for f in schema["profileFields"] if f["key"] == "dept")
        self.assertEqual(dept["label"], "院系/班级")


if __name__ == "__main__":
    unittest.main()
