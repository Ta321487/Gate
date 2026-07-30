"""门户用户任命：服务对象域 / 场景档须关；组织成员档可开。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import build_domain_schema
from app.bake.staff_posts import allow_appoint_from_users


def _allow(domain: str, title: str = "", body: str = "") -> bool:
    return allow_appoint_from_users(domain, proposal_text=body, title=title)


def _schema_allow(domain: str, title: str = "", body: str = "") -> bool:
    roles = build_domain_schema(title or "测试", domain, proposal_text=body).get("roles") or {}
    return roles.get("allowAppointFromUsers") is True


class AppointFromUsersTests(unittest.TestCase):
    def test_trade_reserve_always_closed(self) -> None:
        for d in (
            "DOM-HOSPITAL",
            "DOM-PARKING",
            "DOM-MEETING",
            "DOM-SALON",
            "DOM-HOTEL",
            "DOM-SHOP",
            "DOM-FOOD",
        ):
            self.assertFalse(_allow(d), d)
            self.assertFalse(_schema_allow(d), d)

    def test_recipient_domains_always_closed(self) -> None:
        for d, title, body in (
            ("DOM-DATING", "婚恋交友", "会员互相喜欢。"),
            ("DOM-RECRUIT", "校园招聘", "求职者投递简历。"),
            ("DOM-INTERN", "实习管理", "实习生提交周报。"),
            ("DOM-PARCEL", "校园驿站", "取件人扫码取件。"),
            ("DOM-ACTIVITY", "社团活动报名", "报名者在线报名。"),
            ("DOM-EQUIP", "器材借用", "借用人预约器材。"),
            ("DOM-ASSET", "物资申领", "申领人申请办公用品。"),
        ):
            self.assertFalse(_allow(d, title, body), d)
            self.assertFalse(_schema_allow(d, title, body), d)

    def test_scene_blocks_property_media_event_lost(self) -> None:
        self.assertFalse(_allow("DOM-PROPERTY", "小区物业报修", "业主在线报修。"))
        self.assertTrue(_allow("DOM-PROPERTY", "校园物业报修", "师生报修工单。"))
        self.assertFalse(_allow("DOM-MEDIA", "影视点播", "用户点播收藏。"))
        self.assertTrue(_allow("DOM-MEDIA", "校园媒资点播", "师生点播学习资源。"))
        self.assertFalse(_allow("DOM-EVENT", "公共卫生随访", "随访对象上报健康。"))
        self.assertFalse(_allow("DOM-EVENT", "养老机构巡访", "家属查看照护。"))
        self.assertTrue(_allow("DOM-EVENT", "校园晨午检", "班主任维护学生档案。"))
        self.assertTrue(_allow("DOM-EVENT", "社区健康监测", "网格员上报居民。"))
        self.assertFalse(_allow("DOM-LOST", "社区失物招领", "居民认领失物。"))
        self.assertFalse(_allow("DOM-LOST", "宠物领养", "领养人提交申请。"))
        self.assertTrue(_allow("DOM-LOST", "校园失物招领", "师生认领失物。"))
        self.assertFalse(_allow("DOM-FORUM", "小区业主论坛", "居民发帖回帖。"))
        self.assertTrue(_allow("DOM-FORUM", "校园论坛", "师生发帖回帖。"))

    def test_org_member_domains_still_open(self) -> None:
        for d, title, body in (
            ("DOM-LIBRARY", "图书借阅", "读者借还图书。"),
            ("DOM-DORM", "宿舍报修", "学生提交报修。"),
            ("DOM-ATTEND", "员工考勤", "员工请假打卡。"),
            ("DOM-FORUM", "校园论坛", "师生发帖回帖。"),
            ("DOM-FUND", "学生资助", "困难生申请助学金。"),
        ):
            self.assertTrue(_allow(d, title, body), d)
            self.assertTrue(_schema_allow(d, title, body), d)

    def test_dual_role_domains_no_clerk_appoint_closed(self) -> None:
        """CRM/EVAL 双角色无办理岗：无可任命岗位 → allowAppoint 关。"""
        for d, title, body in (
            ("DOM-CRM", "客户关系管理", "销售跟进客户线索。"),
            ("DOM-EVAL", "学生网上评教", "学生对课程多维打分。"),
        ):
            self.assertFalse(_allow(d, title, body), d)
            self.assertFalse(_schema_allow(d, title, body), d)
            roles = build_domain_schema(title, d, proposal_text=body).get("roles") or {}
            self.assertEqual(roles.get("staff_posts") or [], [])
            self.assertNotIn("subadmin", roles)

    def test_crm_three_roles_when_opening_names_clerk(self) -> None:
        body = "销售建档；客户经理审核跟进后办结。"
        self.assertTrue(_allow("DOM-CRM", "客户关系管理", body))
        roles = build_domain_schema(
            "客户关系管理", "DOM-CRM", proposal_text=body
        ).get("roles") or {}
        self.assertEqual(roles.get("subadmin", {}).get("staffPostId"), "account_mgr")
        self.assertTrue(roles.get("allowAppointFromUsers"))

    def test_every_catalog_domain_flag_is_bool_and_matches_rule(self) -> None:
        """防漏登记：全 catalog 默认开题下 schema 开关必须是 bool，且与规则函数一致。"""
        from app.bake.domains import DOMAINS

        for d in sorted(DOMAINS):
            title = f"{d}测试系统"
            expect = _allow(d, title, "")
            roles = build_domain_schema(title, d, proposal_text="").get("roles") or {}
            flag = roles.get("allowAppointFromUsers")
            self.assertIsInstance(flag, bool, d)
            self.assertEqual(flag, expect, d)


if __name__ == "__main__":
    unittest.main()
