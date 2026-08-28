"""§2 / §16 易混对：正句命中期望域，反句不互抢（domain-skin-gap-analysis）。"""

from __future__ import annotations

import unittest

from app.bake.catalog import match_text
from app.bake.domain_schema import build_domain_schema
from app.bake.engine_sql import domain_sql


# (id, 正句, 期望域)
_POSITIVE: list[tuple[str, str, str]] = [
    ("M-01", "顶岗实习岗位建档与每周周报导师审阅", "DOM-INTERN"),
    ("M-02", "校园招聘岗位发布与简历投递初筛", "DOM-RECRUIT"),
    ("M-03a", "社团志愿活动在线报名审核", "DOM-ACTIVITY"),
    ("M-03b", "公选课在线选课与学分名额", "DOM-COURSE"),
    ("M-04", "学生请假销假管理系统", "DOM-ATTEND"),
    ("M-05", "校园传染病晨午检打卡与异常上报", "DOM-EVENT"),
    ("M-06a", "宠物医院门诊挂号预约", "DOM-HOSPITAL"),
    ("M-06b", "流浪动物领养申请审核", "DOM-LOST"),
    ("M-07", "校园快递驿站取件核销", "DOM-PARCEL"),
    ("M-08", "宾馆客房预订管理系统", "DOM-HOTEL"),
    ("M-09a", "实验室安全培训与准入申请", "DOM-LABSAFE"),
    ("M-09b", "实验耗材与试剂申领出库", "DOM-ASSET"),
    ("M-10", "社区物业投诉建议工单受理", "DOM-PROPERTY"),
    ("M-11", "高校助学贷款困难认定申请", "DOM-FUND"),
    ("M-12", "校园相亲牵线交友审核", "DOM-DATING"),
    ("M-13a", "会议室分时预约管理系统", "DOM-MEETING"),
    ("M-13b", "大型仪器借用与机时时段预约", "DOM-INSTRUMENT"),
    ("M-14a", "学生宿舍水电报修与卫生整改", "DOM-DORM"),
    ("M-14b", "学生宿舍床位分配与调宿申请", "DOM-BED"),
    ("M-15a", "成绩更正与成绩复核申请", "DOM-GRADE"),
    ("M-15b", "学生网上评教与课程评分", "DOM-EVAL"),
    ("M-15c", "综合测评与德育分申报", "DOM-MORAL"),
    ("M-16", "旅行社线路报名与出团确认", "DOM-TOUR"),
    ("M-17a", "家政预约与上门维修时段预约", "DOM-SALON"),
    ("M-17b", "小区物业报修工单受理完结", "DOM-PROPERTY"),
    ("M-18a", "消防设备巡检打卡与异常上报", "DOM-EVENT"),
    ("M-18b", "校园网故障报修与IT运维工单", "DOM-IT"),
    ("M-19a", "景区演出票务领票与名额报名", "DOM-ACTIVITY"),
    ("M-19b", "影院在线选座购票管理系统", "DOM-CINEMA"),
    ("M-20a", "校园跑腿代买订单办理", "DOM-SHOP"),
    ("M-20b", "校园快递驿站取件核销", "DOM-PARCEL"),
    ("M-21a", "充电桩与共享车位时段预约", "DOM-PARKING"),
    ("M-21b", "校园临时车辆通行证申请备案", "DOM-CARPASS"),
    ("M-22a", "点播课课程视频库播放收藏", "DOM-MEDIA"),
    ("M-22b", "公选课在线选课与学分名额", "DOM-COURSE"),
    ("M-22c", "校园表白墙树洞发帖回帖", "DOM-FORUM"),
    ("M-22d", "校园资讯院刊文章发布浏览", "DOM-BLOG"),
]

# (id, 正句, 禁止落入的域)
_NEGATIVE: list[tuple[str, str, str]] = [
    ("M-01", "顶岗实习岗位建档与每周周报导师审阅", "DOM-RECRUIT"),
    ("M-02", "校园招聘岗位发布与简历投递初筛", "DOM-INTERN"),
    ("M-03a", "社团志愿活动在线报名审核", "DOM-COURSE"),
    ("M-03b", "公选课在线选课与学分名额", "DOM-ACTIVITY"),
    ("M-04", "学生请假销假管理系统", "DOM-EVENT"),
    ("M-05", "校园传染病晨午检打卡与异常上报", "DOM-ATTEND"),
    ("M-06a", "宠物医院门诊挂号预约", "DOM-LOST"),
    ("M-06b", "流浪动物领养申请审核", "DOM-HOSPITAL"),
    ("M-07", "校园快递驿站取件核销", "DOM-SHOP"),
    ("M-08", "宾馆客房预订管理系统", "DOM-GENERIC"),
    ("M-08b", "宾馆客房预订管理系统", "DOM-MEETING"),
    ("M-09a", "实验室安全培训与准入申请", "DOM-ASSET"),
    ("M-09b", "实验耗材与试剂申领出库", "DOM-LABSAFE"),
    ("M-10", "社区物业投诉建议工单受理", "DOM-DORM"),
    ("M-11", "高校助学贷款困难认定申请", "DOM-EXPENSE"),
    ("M-11b", "高校助学贷款困难认定申请", "DOM-SEAL"),
    ("M-11c", "高校助学贷款困难认定申请", "DOM-CERT"),
    ("M-12", "校园相亲牵线交友审核", "DOM-MUTUAL-TUTOR"),
    ("M-13a", "会议室分时预约管理系统", "DOM-INSTRUMENT"),
    ("M-13b", "大型仪器借用与机时时段预约", "DOM-MEETING"),
    ("M-13c", "大型仪器借用与机时时段预约", "DOM-EQUIP"),
    ("M-14a", "学生宿舍水电报修与卫生整改", "DOM-BED"),
    ("M-14b", "学生宿舍床位分配与调宿申请", "DOM-DORM"),
    ("M-15a", "成绩更正与成绩复核申请", "DOM-EVAL"),
    ("M-15b", "学生网上评教与课程评分", "DOM-GRADE"),
    ("M-15c", "综合测评与德育分申报", "DOM-GRADE"),
    ("M-16a", "旅行社线路报名与出团确认", "DOM-ACTIVITY"),
    ("M-16b", "旅行社线路报名与出团确认", "DOM-HOTEL"),
    ("M-16c", "旅行社线路报名与出团确认", "DOM-CARPOOL"),
    ("M-16d", "旅行社线路报名与出团确认", "DOM-TRIP"),
    ("M-17a", "家政预约与上门维修时段预约", "DOM-PROPERTY"),
    ("M-17b", "小区物业报修工单受理完结", "DOM-SALON"),
    ("M-18a", "消防设备巡检打卡与异常上报", "DOM-IT"),
    ("M-18b", "校园网故障报修与IT运维工单", "DOM-EVENT"),
    ("M-19a", "景区演出票务领票与名额报名", "DOM-CINEMA"),
    ("M-19b", "影院在线选座购票管理系统", "DOM-ACTIVITY"),
    ("M-20a", "校园跑腿代买订单办理", "DOM-PARCEL"),
    ("M-20b", "校园快递驿站取件核销", "DOM-SHOP"),
    ("M-21a", "充电桩与共享车位时段预约", "DOM-CARPASS"),
    ("M-21b", "校园临时车辆通行证申请备案", "DOM-PARKING"),
    ("M-22a", "点播课课程视频库播放收藏", "DOM-COURSE"),
    ("M-22b", "公选课在线选课与学分名额", "DOM-MEDIA"),
    ("M-22c", "校园表白墙树洞发帖回帖", "DOM-BLOG"),
    ("M-22d", "校园资讯院刊文章发布浏览", "DOM-FORUM"),
]


class ConfusionPairMatchTests(unittest.TestCase):
    def test_positive_hits(self) -> None:
        for mid, title, want in _POSITIVE:
            with self.subTest(id=mid, title=title):
                got = match_text(f"基于 Spring Boot 的{title}的设计与实现")
                self.assertEqual(got.domain, want, f"hits={got.hits[:8]}")

    def test_negative_not_cross(self) -> None:
        for mid, title, forbid in _NEGATIVE:
            with self.subTest(id=mid, forbid=forbid):
                got = match_text(f"基于 Spring Boot 的{title}的设计与实现")
                self.assertNotEqual(got.domain, forbid, f"hits={got.hits[:8]}")

    def test_m12_dating_vs_tutor_mutual(self) -> None:
        """M-12：相亲牵线 → DATING；导师双选 → DOM-MUTUAL-TUTOR。"""
        dating = match_text("基于 Spring Boot 的校园相亲牵线交友审核系统的设计与实现")
        self.assertEqual(dating.domain, "DOM-DATING", f"hits={dating.hits[:8]}")
        tutor = match_text("基于 Spring Boot 的研究生导师双向选择志愿与确认系统的设计与实现")
        self.assertEqual(tutor.domain, "DOM-MUTUAL-TUTOR", f"hits={tutor.hits[:8]}")
        self.assertNotEqual(tutor.domain, "DOM-DATING")


class InternMenuSeedSemanticsTests(unittest.TestCase):
    """M-01 / §18：说明页≠「我的多岗」；种子「实习中」仅关联岗；入口在我的周报。"""

    def test_intern_user_menu_is_catalog(self) -> None:
        schema = build_domain_schema("顶岗实习周报", "DOM-INTERN", proposal_text="学生提交周报")
        user_menus = schema.get("menus", {}).get("user") or []
        self.assertEqual(user_menus[0].get("key"), "my_tickets")
        self.assertIn("周报", str(user_menus[0].get("label") or ""))
        archive = next((m for m in user_menus if m.get("key") == "archive"), None)
        self.assertIsNotNone(archive)
        label = str(archive.get("label") or "")
        self.assertNotIn("我的", label)
        self.assertIn("岗位", label)
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("applyFromList"))

    def test_intern_seed_single_active_stage(self) -> None:
        sql = domain_sql("DOM-INTERN", "t", title="顶岗实习周报", proposal_text="学生提交周报")
        self.assertIn("DEFAULT '待上岗'", sql)
        insert_active = [ln for ln in sql.splitlines() if ", '实习中')" in ln or ", '实习中'," in ln]
        self.assertEqual(len(insert_active), 1, insert_active)
        self.assertIn("week_report", sql)
        self.assertIn("'user'", sql)

    def test_parcel_menu_not_mine_prefix(self) -> None:
        schema = build_domain_schema("校园驿站", "DOM-PARCEL", proposal_text="取件核销")
        user_menus = schema.get("menus", {}).get("user") or []
        self.assertEqual(user_menus[0].get("key"), "my_tickets")
        archive = next((m for m in user_menus if m.get("key") == "archive"), None)
        self.assertIsNotNone(archive)
        self.assertNotIn("我的", str(archive.get("label") or ""))
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("applyFromList"))


if __name__ == "__main__":
    unittest.main()
