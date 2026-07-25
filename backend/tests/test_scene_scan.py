"""开题场景单一真源：壳与资料页必须同判定。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import build_domain_schema
from app.bake.scene_scan import scene_for
from app.bake.schema.templates import SCHEMA_BUILDERS


class SceneScanContractTests(unittest.TestCase):
    def test_crm_sales_beats_campus_background(self) -> None:
        scene = scene_for(
            "DOM-CRM",
            "中小企业客户跟进管理系统",
            "学院创业孵化；销售人员维护客户并提交跟进。",
        )
        self.assertEqual(scene, "enterprise")
        schema = build_domain_schema(
            "中小企业客户跟进管理系统",
            "DOM-CRM",
            proposal_text="学院创业孵化；销售人员维护客户并提交跟进。",
        )
        ident = next(f for f in schema["profileFields"] if f["key"] == "identityType")
        self.assertEqual(ident["options"], ["销售", "运营", "其他"])
        self.assertNotIn("studentNo", {f["key"] for f in schema["profileFields"]})

    def test_event_elderly_institution_not_community_grid(self) -> None:
        """养老机构/照护员开题不得套社区网格壳，档案与种子跟机构档。"""
        title = "养老机构健康监测照护管理系统"
        body = "养老机构需要照护员对老人健康打卡与异常上报。"
        self.assertEqual(scene_for("DOM-EVENT", title, body), "institution")
        schema = build_domain_schema(title, "DOM-EVENT", proposal_text=body)
        self.assertEqual(schema["roles"]["subadmin"]["label"], "照护员")
        self.assertNotEqual(schema["roles"]["subadmin"]["label"], "网格员")
        self.assertEqual(schema["labels"].get("authEyebrow"), "机构照护")
        self.assertNotEqual(schema["labels"].get("authEyebrow"), "社区公卫")
        archive = schema["entities"]["archive"]
        self.assertEqual(archive.get("label"), "老人")
        author = next(f for f in archive["fields"] if f["key"] == "author")
        # attach_staff_posts 后与子管同名（照护员）
        self.assertEqual(author["label"], "照护员")
        ident = next(f for f in schema["profileFields"] if f["key"] == "identityType")
        self.assertEqual(ident["options"], ["照护员", "家属", "访客"])
        self.assertNotIn("studentNo", {f["key"] for f in schema["profileFields"]})

        from app.bake.engine_sql import domain_sql

        sql = domain_sql("DOM-EVENT", "thesis_test", title=title, proposal_text=body)
        self.assertIn("王德贵", sql)
        self.assertIn("照护员张敏", sql)
        self.assertNotIn("南门聚集性发热", sql)
        self.assertNotIn("食堂晨检", sql)
        self.assertNotIn("网格员甲", sql)

        # 社区网格仍走 community
        self.assertEqual(
            scene_for("DOM-EVENT", "社区健康监测", "社区网格员维护居民档案。"),
            "community",
        )

    def test_event_enterprise_fugong_not_community(self) -> None:
        title = "企业员工健康监测复工管理系统"
        body = "企业需要组织员工健康打卡与复工评估。"
        self.assertEqual(scene_for("DOM-EVENT", title, body), "enterprise")
        schema = build_domain_schema(title, "DOM-EVENT", proposal_text=body)
        self.assertEqual(schema["labels"].get("authEyebrow"), "企业复工")
        self.assertEqual(schema["entities"]["archive"].get("label"), "员工")
        self.assertNotIn("studentNo", {f["key"] for f in schema["profileFields"]})
        from app.bake.engine_sql import domain_sql

        sql = domain_sql("DOM-EVENT", "thesis_test", title=title, proposal_text=body)
        self.assertIn("生产一部", sql)
        self.assertNotIn("南门聚集性发热", sql)
        self.assertNotIn("阳光小区", sql)

    def test_event_default_clinic_not_campus_seed(self) -> None:
        title = "基层慢性病随访健康管理系统"
        body = "基层医疗卫生机构对高血压糖尿病患者建档随访。"
        self.assertEqual(scene_for("DOM-EVENT", title, body), "default")
        schema = build_domain_schema(title, "DOM-EVENT", proposal_text=body)
        self.assertEqual(schema["labels"].get("authEyebrow"), "健康随访")
        self.assertNotIn("studentNo", {f["key"] for f in schema["profileFields"]})
        ident = next(f for f in schema["profileFields"] if f["key"] == "identityType")
        self.assertIn("随访对象", ident["options"])
        from app.bake.engine_sql import domain_sql

        sql = domain_sql("DOM-EVENT", "thesis_test", title=title, proposal_text=body)
        self.assertIn("高血压", sql)
        self.assertNotIn("南门聚集性发热", sql)
        self.assertNotIn("食堂晨检", sql)

    def test_event_campus_and_community_archive_columns(self) -> None:
        campus = build_domain_schema(
            "校园晨午检", "DOM-EVENT", proposal_text="因病缺课上报。"
        )
        self.assertEqual(campus["entities"]["archive"].get("label"), "学生")
        community = build_domain_schema(
            "社区健康监测",
            "DOM-EVENT",
            proposal_text="社区网格员维护居民档案。",
        )
        self.assertEqual(community["entities"]["archive"].get("label"), "对象")
        author = next(
            f for f in community["entities"]["archive"]["fields"] if f["key"] == "author"
        )
        self.assertEqual(author["label"], "网格员")

    def test_attend_enterprise_archive_columns(self) -> None:
        schema = build_domain_schema(
            "企业员工考勤请假管理系统", "DOM-ATTEND", proposal_text=""
        )
        arch = schema["entities"]["archive"]
        self.assertEqual(arch.get("label"), "员工")
        isbn = next(f for f in arch["fields"] if f["key"] == "isbn")
        self.assertEqual(isbn["label"], "工号备注")
        self.assertNotIn("学号", isbn["label"])

    def test_shell_and_profile_same_scene_asset_attend_event(self) -> None:
        cases = [
            (
                "DOM-ASSET",
                "物资领用系统",
                "企业仓储部门耗材申领出库。",
                "enterprise",
                "物资领用",
            ),
            (
                "DOM-ASSET",
                "高校固定资产申领",
                "学院行政部门物资申领。",
                "campus",
                "高校物资",
            ),
            (
                "DOM-ATTEND",
                "学生请假销假管理系统",
                "",
                "campus",
                "学生请假",
            ),
            (
                "DOM-ATTEND",
                "企业员工考勤请假管理系统",
                "",
                "enterprise",
                "人事公告",
            ),
            (
                "DOM-EVENT",
                "社区健康监测",
                "社区网格员维护居民档案。",
                "community",
                "社区公卫",
            ),
            (
                "DOM-EVENT",
                "校园晨午检",
                "因病缺课上报。",
                "campus",
                "校园晨午检",
            ),
        ]
        for domain, title, body, want_scene, eyebrow_or_notice in cases:
            with self.subTest(domain=domain, title=title):
                self.assertEqual(scene_for(domain, title, body), want_scene)
                schema = build_domain_schema(title, domain, proposal_text=body)
                labels = schema.get("labels") or {}
                blob = " ".join(
                    [
                        labels.get("authEyebrow") or "",
                        labels.get("noticePageTitle") or "",
                        (schema.get("roles") or {}).get("admin", {}).get("label") or "",
                    ]
                )
                self.assertIn(eyebrow_or_notice, blob)

    def test_parcel_community_no_campus_profile(self) -> None:
        title, body = "快递代收系统", "小区菜鸟驿站取件核销。"
        self.assertEqual(scene_for("DOM-PARCEL", title, body), "community")
        schema = build_domain_schema(title, "DOM-PARCEL", proposal_text=body)
        self.assertEqual(schema["labels"]["authEyebrow"], "快递代收")
        self.assertNotIn("campusNo", {f["key"] for f in schema["profileFields"]})

    def test_builders_accept_proposal_kw(self) -> None:
        """SCENE_COPY 域 builder 必须吃 proposal_text，避免只扫题名。"""
        from app.bake.schema.shells import _SCENE_COPY_DOMAINS

        for dom in sorted(_SCENE_COPY_DOMAINS):
            with self.subTest(dom=dom):
                fn = SCHEMA_BUILDERS[dom]
                schema = fn("测试课题", proposal_text="占位开题正文")
                self.assertTrue(schema.get("labels") or schema.get("roles"))

    def test_scene_branch_domains_wired_in_scene_for(self) -> None:
        """SCENE_COPY 域不得一律 default；壳/资料页须能按开题分档。"""
        from app.bake.schema.shells import _SCENE_COPY_DOMAINS

        cases = [
            ("DOM-FOOD", "校园食堂点餐系统", "食堂档口堂食外卖", "campus"),
            ("DOM-SHOP", "校园二手交易平台", "校内闲置物品流转", "campus"),
            ("DOM-HOSPITAL", "宠物医院挂号预约系统", "宠主为爱宠挂号", "adopt"),
            ("DOM-SALON", "美发门店预约系统", "发型师分时预约", "commercial"),
            ("DOM-CRM", "中小企业客户跟进", "销售维护客户", "enterprise"),
            ("DOM-IT", "企业内网故障报修", "员工提交终端故障", "enterprise"),
            ("DOM-LOST", "宠物领养管理系统", "待领养档案与申请", "adopt"),
            ("DOM-PARCEL", "小区快递代收", "菜鸟驿站取件", "community"),
            ("DOM-RECRUIT", "企业社会招聘系统", "HR 社招投递", "enterprise"),
            ("DOM-ATTEND", "学生请假销假", "", "campus"),
            ("DOM-MEETING", "企业会议室预约", "部门会议室占坑", "enterprise"),
            ("DOM-PARKING", "商场车位预约", "商场地下车场", "commercial"),
            ("DOM-ASSET", "企业仓储耗材申领", "仓储出库", "enterprise"),
            ("DOM-EVENT", "养老机构健康监测", "照护员打卡上报", "institution"),
        ]
        covered = {c[0] for c in cases}
        self.assertEqual(_SCENE_COPY_DOMAINS, covered)
        for domain, title, body, want in cases:
            with self.subTest(domain=domain):
                self.assertEqual(scene_for(domain, title, body), want)

    def test_hospital_pet_profile_and_seed(self) -> None:
        title, body = "宠物医院挂号预约系统", "宠主为爱宠选择医生挂号。"
        self.assertEqual(scene_for("DOM-HOSPITAL", title, body), "adopt")
        schema = build_domain_schema(title, "DOM-HOSPITAL", proposal_text=body)
        self.assertEqual(schema["labels"].get("authEyebrow"), "宠物挂号")
        keys = {f["key"] for f in schema["profileFields"]}
        self.assertIn("petName", keys)
        self.assertNotIn("patientNo", keys)
        from app.bake.engine_sql import domain_sql

        sql = domain_sql("DOM-HOSPITAL", "thesis_test", title=title, proposal_text=body)
        self.assertIn("宠主甲", sql)
        self.assertIn("豆豆", sql)
        self.assertNotIn("钱患者", sql)

    def test_attend_campus_seed_not_employee(self) -> None:
        title, body = "学生请假销假管理系统", ""
        from app.bake.engine_sql import domain_sql

        sql = domain_sql("DOM-ATTEND", "thesis_test", title=title, proposal_text=body)
        self.assertIn("学生甲", sql)
        self.assertIn("学工主管", sql)
        self.assertNotIn("员工甲", sql)

    def test_it_enterprise_seed_not_campus_student(self) -> None:
        title, body = "企业内网故障报修系统", "员工提交办公区终端故障。"
        schema = build_domain_schema(title, "DOM-IT", proposal_text=body)
        self.assertEqual(schema["labels"].get("authEyebrow"), "企业运维")
        from app.bake.engine_sql import domain_sql

        sql = domain_sql("DOM-IT", "thesis_test", title=title, proposal_text=body)
        self.assertIn("研发中心", sql)
        self.assertNotIn("陈同学", sql)
        self.assertNotIn("宿舍区", sql)

    def test_lost_adopt_and_community_shell(self) -> None:
        adopt = build_domain_schema(
            "宠物领养管理系统", "DOM-LOST", proposal_text="待领养档案与申请审核。"
        )
        self.assertEqual(adopt["labels"].get("authEyebrow"), "宠物领养")
        community = build_domain_schema(
            "小区失物招领", "DOM-LOST", proposal_text="社区物业失物启事认领。"
        )
        self.assertEqual(community["labels"].get("authEyebrow"), "社区招领")
        from app.bake.engine_sql import domain_sql

        sql = domain_sql(
            "DOM-LOST",
            "thesis_test",
            title="宠物领养管理系统",
            proposal_text="待领养档案与申请审核。",
        )
        self.assertIn("小橘", sql)
        self.assertNotIn("校园卡", sql)

    def test_single_template_domains_build(self) -> None:
        """无场景分支域：默认题名能出壳，不抛错。"""
        single = [
            "DOM-LIBRARY",
            "DOM-EQUIP",
            "DOM-FUND",
            "DOM-LABSAFE",
            "DOM-GRADE",
            "DOM-INTERN",
            "DOM-COURSE",
            "DOM-DORM",
            "DOM-PROPERTY",
            "DOM-HOTEL",
            "DOM-ACTIVITY",
            "DOM-MEDIA",
            "DOM-MUSIC",
            "DOM-FORUM",
            "DOM-BLOG",
        ]
        for dom in single:
            with self.subTest(dom=dom):
                schema = build_domain_schema("测试课题", dom, proposal_text="")
                self.assertTrue(schema.get("labels") or schema.get("roles"))
                self.assertIn(dom, SCHEMA_BUILDERS)


if __name__ == "__main__":
    unittest.main()
