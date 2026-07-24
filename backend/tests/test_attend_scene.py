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

    def test_profile_enterprise_employee(self) -> None:
        schema = build_domain_schema("企业员工考勤请假管理系统", "DOM-ATTEND")
        ident = next(f for f in schema["profileFields"] if f["key"] == "identityType")
        self.assertEqual(ident["options"], ["员工", "兼职"])
        keys = {f["key"] for f in schema["profileFields"]}
        self.assertNotIn("studentNo", keys)
        dept = next(f for f in schema["profileFields"] if f["key"] == "dept")
        self.assertEqual(dept["label"], "部门/岗位")

    def test_crm_asset_event_parcel_meeting_profiles(self) -> None:
        """资料页身份跟开题场景：企业/社区不得残留教职工学号档。"""
        crm = build_domain_schema(
            "中小企业客户跟进管理系统",
            "DOM-CRM",
            proposal_text="销售人员登录与个人资料；客户档案与跟进记录。",
        )
        crm_keys = {f["key"] for f in crm["profileFields"]}
        self.assertNotIn("studentNo", crm_keys)
        crm_ident = next(f for f in crm["profileFields"] if f["key"] == "identityType")
        self.assertEqual(crm_ident["options"], ["销售", "运营", "其他"])
        self.assertNotIn("教职工", crm_ident["options"])

        asset = build_domain_schema(
            "物资领用系统",
            "DOM-ASSET",
            proposal_text="企业仓储部门办公物资与耗材申领出库。",
        )
        asset_ident = next(f for f in asset["profileFields"] if f["key"] == "identityType")
        self.assertEqual(asset_ident["options"], ["员工", "外包", "其他"])
        asset_dept = next(f for f in asset["profileFields"] if f["key"] == "dept")
        self.assertEqual(asset_dept["label"], "部门")

        asset_campus = build_domain_schema(
            "高校固定资产与耗材申领管理系统",
            "DOM-ASSET",
            proposal_text="学院行政与教学单位办公物资申领。",
        )
        ac_ident = next(
            f for f in asset_campus["profileFields"] if f["key"] == "identityType"
        )
        self.assertIn("教职工", ac_ident["options"])
        self.assertIn("学生", ac_ident["options"])

        event = build_domain_schema(
            "社区健康监测系统",
            "DOM-EVENT",
            proposal_text="社区网格员维护居民档案并健康打卡上报。",
        )
        ev_ident = next(f for f in event["profileFields"] if f["key"] == "identityType")
        self.assertEqual(ev_ident["options"], ["居民", "志愿者", "访客"])
        ev_keys = {f["key"] for f in event["profileFields"]}
        self.assertNotIn("studentNo", ev_keys)

        parcel = build_domain_schema(
            "快递代收系统",
            "DOM-PARCEL",
            proposal_text="小区菜鸟驿站包裹入库与取件核销。",
        )
        parcel_keys = {f["key"] for f in parcel["profileFields"]}
        self.assertNotIn("campusNo", parcel_keys)
        self.assertIn("receiveAddress", parcel_keys)

        meeting = build_domain_schema(
            "企业会议室预约系统",
            "DOM-MEETING",
            proposal_text="公司各部门会议室时段预约与会务管理。",
        )
        m_ident = next(f for f in meeting["profileFields"] if f["key"] == "identityType")
        self.assertEqual(m_ident["options"], ["员工", "访客"])
        self.assertNotIn("学生", m_ident["options"])

        seat = build_domain_schema("图书馆座位预约管理系统", "DOM-MEETING")
        s_ident = next(f for f in seat["profileFields"] if f["key"] == "identityType")
        self.assertIn("学生", s_ident["options"])

        adopt = build_domain_schema(
            "宠物领养管理系统",
            "DOM-LOST",
            proposal_text="待领养档案浏览、领养申请与审核。",
        )
        adopt_keys = {f["key"] for f in adopt["profileFields"]}
        self.assertNotIn("campusNo", adopt_keys)
        self.assertIn("homeAddress", adopt_keys)

    def test_recruit_event_asset_parking_parcel_scenes(self) -> None:
        recruit = SCHEMA_BUILDERS["DOM-RECRUIT"](
            "岗位投递系统",
            proposal_text="面向高校毕业生的校园招聘与就业办初筛。",
        )
        self.assertEqual(recruit["roles"]["admin"]["label"], "就业办主管（总管）")
        self.assertEqual(recruit["labels"]["authEyebrow"], "校园招聘")

        event = SCHEMA_BUILDERS["DOM-EVENT"](
            "健康监测系统",
            proposal_text="校园传染病防控晨午检与因病缺课上报。",
        )
        self.assertEqual(event["roles"]["subadmin"]["label"], "班主任")
        self.assertEqual(event["labels"]["authEyebrow"], "校园晨午检")

        asset = SCHEMA_BUILDERS["DOM-ASSET"](
            "物资领用系统",
            proposal_text="高校行政部门与教学单位办公物资申领。",
        )
        self.assertEqual(asset["labels"]["authEyebrow"], "高校物资")

        parking = SCHEMA_BUILDERS["DOM-PARKING"](
            "车位预约系统",
            proposal_text="校园教职工与访客车位时段预约。",
        )
        self.assertEqual(parking["labels"]["authEyebrow"], "校园车位")

        parcel = SCHEMA_BUILDERS["DOM-PARCEL"](
            "快递代收系统",
            proposal_text="小区菜鸟驿站包裹入库与取件核销。",
        )
        self.assertEqual(parcel["labels"]["authEyebrow"], "快递代收")
        self.assertNotEqual(parcel["labels"]["authEyebrow"], "校园驿站")

    def test_library_seat_matches_meeting(self) -> None:
        from app.bake.catalog import match_text

        m = match_text("图书馆座位预约管理系统")
        self.assertEqual(m.domain, "DOM-MEETING")
        self.assertEqual(m.archetype, "ARCH-RESERVE")

    def test_vaccine_and_adopt_scene_copy(self) -> None:
        """HPV 疫苗 → HOSPITAL 号源壳；宠物领养 → LOST 认领壳（同 _meeting 分支写法）。"""
        from app.bake.catalog import match_text

        v = match_text("HPV疫苗预约系统的设计与实现")
        self.assertEqual(v.domain, "DOM-HOSPITAL")
        self.assertEqual(v.archetype, "ARCH-RESERVE")
        vs = SCHEMA_BUILDERS["DOM-HOSPITAL"]("HPV疫苗预约系统")
        self.assertEqual(vs["labels"]["authEyebrow"], "疫苗预约")
        self.assertEqual(vs["roles"]["user"]["label"], "接种人")

        a = match_text("springboot宠物领养系统的设计与实现")
        self.assertEqual(a.domain, "DOM-LOST")
        self.assertEqual(a.archetype, "ARCH-FLOW")
        as_ = SCHEMA_BUILDERS["DOM-LOST"]("宠物领养管理系统")
        self.assertEqual(as_["labels"]["authEyebrow"], "宠物领养")
        self.assertEqual(as_["roles"]["subadmin"]["label"], "领养专员")
        self.assertEqual(as_["entities"]["ticket"]["label"], "领养单")

        # 开题正文双扫：题名无领养词时正文写到仍换皮
        body = build_domain_schema(
            "流浪动物管理系统",
            "DOM-LOST",
            proposal_text="主要功能：待领养档案浏览、领养申请与审核。",
        )
        self.assertEqual(body["labels"]["authEyebrow"], "宠物领养")

    def test_seat_gym_pet_scene_copy(self) -> None:
        seat = SCHEMA_BUILDERS["DOM-MEETING"]("图书馆座位预约管理系统")
        self.assertEqual(seat["labels"]["authEyebrow"], "座位预约")
        archive_admin = next(m for m in seat["menus"]["admin"] if m.get("key") == "archive")
        self.assertIn("座位", archive_admin["label"])

        gym = SCHEMA_BUILDERS["DOM-SALON"]("健身房私教预约管理系统")
        self.assertEqual(gym["labels"]["authEyebrow"], "健身预约")
        self.assertEqual(gym["roles"]["user"]["label"], "会员")

        pet = SCHEMA_BUILDERS["DOM-HOSPITAL"]("宠物医院挂号预约管理系统")
        self.assertEqual(pet["labels"]["authEyebrow"], "宠物挂号")
        self.assertEqual(pet["roles"]["user"]["label"], "宠主")

    def test_fund_labsafe_builders(self) -> None:
        fund = SCHEMA_BUILDERS["DOM-FUND"]("测试课题")
        self.assertEqual(fund["roles"]["admin"]["label"], "资助主管（总管）")
        self.assertEqual(fund["entities"]["archive"]["key"], "fund_program")

        lab = SCHEMA_BUILDERS["DOM-LABSAFE"]("测试课题")
        self.assertEqual(lab["roles"]["subadmin"]["label"], "安全员")
        self.assertEqual(lab["entities"]["ticket"]["key"], "access_apply")


if __name__ == "__main__":
    unittest.main()
