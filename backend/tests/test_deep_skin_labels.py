"""深皮可见文案：product_kind 必须换档案/工单 label，禁止只命中域仍穿帮。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import build_domain_schema
from app.bake.engine_sql import domain_sql
from app.bake.scene_scan import (
    crm_product_kind,
    equip_product_kind,
    it_product_kind,
    library_product_kind,
    product_kind_for,
    property_product_kind,
    scene_for,
)


def _field_map(schema: dict) -> dict[str, str]:
    arch = (schema.get("entities") or {}).get("archive") or {}
    return {
        f.get("key"): f.get("label")
        for f in (arch.get("fields") or [])
        if isinstance(f, dict) and f.get("key")
    }


def _menu_label(schema: dict, key: str) -> str | None:
    for m in ((schema.get("menus") or {}).get("admin") or []):
        if isinstance(m, dict) and m.get("key") == key:
            return m.get("label")
    return None


class DeepSkinLabelTests(unittest.TestCase):
    def test_crm_kinds(self) -> None:
        cases = [
            (
                "法律援助案件跟进管理系统",
                "法律援助律所案件跟进审核",
                "legal",
                "案件",
                "案件名称",
                "案件跟进",
            ),
            (
                "高校学工家访谈心谈话记录系统",
                "班主任家访谈心谈话记录跟进",
                "homevisit",
                "谈话对象",
                "学生姓名",
                "家访谈心",
            ),
            (
                "校企合作单位库跟进管理系统",
                "校企合作单位库建档跟进审核",
                "coop",
                "合作单位",
                "单位名称",
                "校企合作",
            ),
            (
                "中小企业客户关系管理系统",
                "销售跟进客户",
                "sales",
                "客户",
                "客户名称",
                "客户跟进",
            ),
        ]
        for title, body, want_kind, arch, title_lab, brow in cases:
            with self.subTest(kind=want_kind):
                self.assertEqual(crm_product_kind(title, body), want_kind)
                self.assertEqual(product_kind_for("DOM-CRM", title, body), want_kind)
                s = build_domain_schema(title, "DOM-CRM", proposal_text=body)
                self.assertEqual((s["entities"]["archive"] or {}).get("label"), arch)
                self.assertEqual(_field_map(s).get("title"), title_lab)
                self.assertEqual((s.get("labels") or {}).get("authEyebrow"), brow)
                self.assertNotEqual(
                    (s.get("labels") or {}).get("authEyebrow"),
                    "校园创业",
                    msg=f"{want_kind} 不得误用创业皮",
                )

    def test_homevisit_not_startup_scene_labels(self) -> None:
        scene = scene_for(
            "DOM-CRM",
            "高校学工家访谈心谈话记录系统",
            "班主任家访谈心谈话记录跟进",
        )
        self.assertEqual(scene, "campus")
        s = build_domain_schema(
            "高校学工家访谈心谈话记录系统",
            "DOM-CRM",
            proposal_text="班主任家访谈心谈话记录跟进",
        )
        self.assertEqual((s.get("labels") or {}).get("authEyebrow"), "家访谈心")
        self.assertEqual(_field_map(s).get("author"), "班级/联系人")

    def test_library_kinds(self) -> None:
        arch = build_domain_schema(
            "高校档案馆卷宗借阅管理系统",
            "DOM-LIBRARY",
            proposal_text="档案馆卷宗借阅与归还审核",
        )
        self.assertEqual(library_product_kind("高校档案馆卷宗借阅管理系统", ""), "archive")
        self.assertEqual((arch["entities"]["archive"] or {}).get("label"), "卷宗")
        self.assertEqual(_field_map(arch).get("isbn"), "档号")
        self.assertNotEqual(_field_map(arch).get("title"), "书名")
        self.assertEqual(_menu_label(arch, "archive"), "卷宗管理")

        drift = build_domain_schema(
            "校园图书漂流借阅管理系统",
            "DOM-LIBRARY",
            proposal_text="校园图书漂流借阅流转审核",
        )
        self.assertEqual(library_product_kind("校园图书漂流借阅管理系统", ""), "drift")
        self.assertEqual(_field_map(drift).get("isbn"), "漂流编号")
        self.assertEqual((drift.get("labels") or {}).get("authEyebrow"), "图书漂流")

        book = build_domain_schema(
            "高校图书借阅管理系统",
            "DOM-LIBRARY",
            proposal_text="读者借还",
        )
        self.assertEqual(_field_map(book).get("isbn"), "ISBN")
        self.assertEqual((book["entities"]["archive"] or {}).get("label"), "图书")

    def test_equip_kinds(self) -> None:
        light = build_domain_schema(
            "校园共享雨伞与充电宝租借管理系统",
            "DOM-EQUIP",
            proposal_text="校园雨伞充电宝门禁卡租借归还",
        )
        self.assertEqual(
            equip_product_kind("校园共享雨伞与充电宝租借管理系统", ""), "light"
        )
        self.assertEqual(
            product_kind_for(
                "DOM-EQUIP", "校园共享雨伞与充电宝租借管理系统", ""
            ),
            "light",
        )
        self.assertEqual((light.get("labels") or {}).get("authEyebrow"), "校园轻资产")
        self.assertEqual((light["entities"]["archive"] or {}).get("label"), "物品")
        self.assertEqual(_field_map(light).get("title"), "物品名称")
        self.assertEqual(_menu_label(light, "archive"), "物品管理")
        self.assertNotEqual((light.get("labels") or {}).get("authEyebrow"), "实验室设备")
        self.assertNotIn("实验室", _menu_label(light, "archive") or "")

        costume = build_domain_schema(
            "校园演出服装道具租借管理系统",
            "DOM-EQUIP",
            proposal_text="演出服装道具器材租借归还审核",
        )
        self.assertEqual(
            equip_product_kind("校园演出服装道具租借管理系统", ""), "costume"
        )
        self.assertEqual((costume.get("labels") or {}).get("authEyebrow"), "演出道具")
        self.assertEqual(_field_map(costume).get("title"), "物品名称")
        self.assertEqual(_menu_label(costume, "archive"), "道具管理")
        self.assertNotEqual(
            (costume.get("labels") or {}).get("authEyebrow"), "实验室设备"
        )

        # 开题写「剧社…租借」而不点名「道具」——场景兜底
        scene_only = equip_product_kind("校园剧社物资租借管理系统", "排练物资借还审核")
        self.assertEqual(scene_only, "costume")

        # 具名器材档 + 中性 gear（勿一律实验室壳）
        extra = [
            ("高校体育器材借用管理系统", "球类运动器材借还", "sports", "体育器材", "器材名称"),
            ("校园摄影摄像器材租借系统", "单反摄像机借用归还", "media", "影像设备", "设备名称"),
            ("高校乐器租借管理系统", "吉他小提琴借还审核", "music", "乐器租借", "乐器名称"),
            ("教学教具借用管理系统", "模型挂图教具借还", "teach", "教学教具", "教具名称"),
            ("户外拓展装备借用系统", "帐篷登山杖借用归还", "outdoor", "户外拓展", "装备名称"),
            ("高校公用器材借用管理系统", "投影仪对讲机借用", "gear", "公用器材", "器材名称"),
            ("校园消防器材借用管理系统", "灭火器消防栓相关器材借还", "gear", "消防器材", "器材名称"),
            ("高校军训器械借用系统", "军训器械借还审核", "gear", "军训器械", "器材名称"),
        ]
        for title, body, want_kind, brow, title_lab in extra:
            with self.subTest(kind=want_kind):
                self.assertEqual(equip_product_kind(title, body), want_kind)
                s = build_domain_schema(title, "DOM-EQUIP", proposal_text=body)
                self.assertEqual((s.get("labels") or {}).get("authEyebrow"), brow)
                self.assertEqual(_field_map(s).get("title"), title_lab)
                self.assertNotEqual(
                    (s.get("labels") or {}).get("authEyebrow"), "实验室设备"
                )

        lab = build_domain_schema(
            "实验室器材借用管理系统",
            "DOM-EQUIP",
            proposal_text="实验室设备借用归还审核",
        )
        self.assertEqual(equip_product_kind("实验室器材借用管理系统", ""), "lab")
        self.assertEqual((lab.get("labels") or {}).get("authEyebrow"), "实验室设备")
        self.assertEqual(_field_map(lab).get("title"), "设备名称")
        self.assertEqual(_menu_label(lab, "archive"), "设备管理")

        # 借用壳标志不被皮换掉；LIBRARY 亦保持 pickLoanPeriod
        from app.bake.domain_schema import attach_accept
        from app.bake.domains import DOMAIN_CAPABILITIES

        for title, body, domain in (
            (
                "校园共享雨伞与充电宝租借管理系统",
                "校园雨伞充电宝门禁卡租借归还",
                "DOM-EQUIP",
            ),
            ("高校图书借阅管理系统", "读者借还", "DOM-LIBRARY"),
        ):
            with self.subTest(domain=domain):
                spec = attach_accept(
                    {
                        "domain": domain,
                        "title": title,
                        "capabilities": list(DOMAIN_CAPABILITIES[domain]),
                        "features": [],
                    },
                    body,
                )
                ticket = ((spec.get("schema") or {}).get("entities") or {}).get(
                    "ticket"
                ) or {}
                self.assertTrue(ticket.get("pickLoanPeriod"))
                self.assertFalse(ticket.get("applicantCompleteOnly"))
                self.assertFalse(ticket.get("slaDeadline"))

    def test_property_kinds(self) -> None:
        muni = build_domain_schema(
            "市政路灯井盖报修管理系统",
            "DOM-PROPERTY",
            proposal_text="路灯井盖市政设施报修工单",
        )
        self.assertEqual(property_product_kind("市政路灯井盖报修管理系统", ""), "municipal")
        self.assertEqual((muni.get("labels") or {}).get("authEyebrow"), "市政报修")
        self.assertEqual((muni["roles"]["user"] or {}).get("label"), "市民")
        self.assertEqual(_menu_label(muni, "lookup_site"), "片区路段")
        self.assertNotEqual(_menu_label(muni, "lookup_site"), "楼栋房间")

        comp = build_domain_schema(
            "社区物业投诉建议工单管理系统",
            "DOM-PROPERTY",
            proposal_text="业主投诉建议物业工单办结",
        )
        self.assertEqual(property_product_kind("社区物业投诉建议工单管理系统", ""), "complaint")
        tick = (comp.get("entities") or {}).get("ticket") or {}
        self.assertEqual(tick.get("label"), "投诉单")
        self.assertEqual((tick.get("verbs") or {}).get("apply"), "提交投诉")
        self.assertEqual(_menu_label(comp, "lookup_site"), "楼栋单元")

    def test_it_kinds(self) -> None:
        after = build_domain_schema(
            "客服售后工单管理系统",
            "DOM-IT",
            proposal_text="客服售后工单受理完结",
        )
        self.assertEqual(it_product_kind("客服售后工单管理系统", ""), "aftersales")
        tick = (after.get("entities") or {}).get("ticket") or {}
        self.assertEqual(tick.get("label"), "售后单")
        self.assertEqual((tick.get("verbs") or {}).get("apply"), "提交售后")
        self.assertEqual((after.get("labels") or {}).get("authEyebrow"), "客服售后")
        self.assertEqual(_menu_label(after, "lookup_site"), "服务网点")
        self.assertNotEqual((after.get("labels") or {}).get("authEyebrow"), "校园网运维")

        maint = build_domain_schema(
            "设备维保工单管理系统",
            "DOM-IT",
            proposal_text="设备维保工单报修受理完结",
        )
        self.assertEqual(it_product_kind("设备维保工单管理系统", ""), "maintenance")
        self.assertEqual(((maint.get("entities") or {}).get("ticket") or {}).get("label"), "维保单")
        self.assertEqual((maint.get("labels") or {}).get("authEyebrow"), "设备维保")

    def test_seeds_switch_with_kind(self) -> None:
        legal_sql = domain_sql(
            "DOM-CRM",
            "t",
            title="法律援助案件跟进管理系统",
            proposal_text="法律援助律所案件跟进审核",
        )
        self.assertIn("律所主管", legal_sql)
        self.assertIn("张某劳动争议援助", legal_sql)
        self.assertNotIn("星河科技有限公司", legal_sql)

        arch_sql = domain_sql(
            "DOM-LIBRARY",
            "t",
            title="高校档案馆卷宗借阅管理系统",
            proposal_text="档案馆卷宗借阅与归还审核",
        )
        self.assertIn("学籍卷宗", arch_sql)
        self.assertIn("档案馆长", arch_sql)
        self.assertNotIn("Spring Boot 实战", arch_sql)

        light_sql = domain_sql(
            "DOM-EQUIP",
            "t",
            title="校园共享雨伞与充电宝租借管理系统",
            proposal_text="校园雨伞充电宝门禁卡租借归还",
        )
        self.assertIn("后勤主管", light_sql)
        self.assertIn("共享雨伞", light_sql)
        self.assertIn("临时门禁卡", light_sql)
        self.assertNotIn("数字万用表", light_sql)
        self.assertNotIn("实验室主管", light_sql)

        costume_sql = domain_sql(
            "DOM-EQUIP",
            "t",
            title="校园演出服装道具租借管理系统",
            proposal_text="演出服装道具器材租借归还审核",
        )
        self.assertIn("艺术团主管", costume_sql)
        self.assertIn("古装戏服", costume_sql)
        self.assertNotIn("数字万用表", costume_sql)
        self.assertNotIn("实验室主管", costume_sql)

        sports_sql = domain_sql(
            "DOM-EQUIP",
            "t",
            title="高校体育器材借用管理系统",
            proposal_text="球类运动器材借还",
        )
        self.assertIn("体育部主管", sports_sql)
        self.assertIn("羽毛球拍", sports_sql)
        self.assertNotIn("数字万用表", sports_sql)

        muni_sql = domain_sql(
            "DOM-PROPERTY",
            "t",
            title="市政路灯井盖报修管理系统",
            proposal_text="路灯井盖市政设施报修工单",
        )
        self.assertIn("市政主管", muni_sql)
        self.assertIn("东区一街", muni_sql)

        after_sql = domain_sql(
            "DOM-IT",
            "t",
            title="客服售后工单管理系统",
            proposal_text="客服售后工单受理完结",
        )
        self.assertIn("客服主管", after_sql)
        self.assertIn("售后须知", after_sql)
        self.assertIn("个人客户", after_sql)
        self.assertNotIn("studentNo", after_sql)

    def test_ticket_kind_profiles_not_campus_leak(self) -> None:
        from app.bake.profile_fields import profile_fields_for

        def labels(domain: str, title: str, body: str) -> list[str]:
            return [
                str(f.get("label"))
                for f in profile_fields_for(domain, title=title, proposal_text=body)
                if f.get("key") not in ("nickname", "phone", "avatar", "realName", "email", "gender")
            ]

        muni = labels(
            "DOM-PROPERTY",
            "市政路灯井盖报修管理系统",
            "路灯井盖市政设施报修工单",
        )
        self.assertIn("片区", muni)
        self.assertIn("设施点", muni)
        self.assertNotIn("住户类型", muni)
        self.assertNotIn("房号", muni)

        after = labels(
            "DOM-IT",
            "客服售后工单管理系统",
            "客服售后工单受理完结",
        )
        self.assertIn("客户类型", after)
        self.assertNotIn("学号", after)

        maint = labels(
            "DOM-IT",
            "设备维保工单管理系统",
            "设备维保工单报修受理完结",
        )
        self.assertIn("工号", maint)
        self.assertNotIn("学号", maint)

    def test_standalone_ticket_keeps_pending_accepted_label(self) -> None:
        dorm = build_domain_schema("学生宿舍报修管理系统", "DOM-DORM")
        states = ((dorm.get("entities") or {}).get("ticket") or {}).get("states") or {}
        self.assertEqual(states.get("pending"), "待受理")
        self.assertEqual(states.get("pending_final"), "待终审")
        self.assertEqual(states.get("approved"), "处理中")


if __name__ == "__main__":
    unittest.main()
