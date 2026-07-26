"""全域错皮回归：禁止已踩过的「共享壳串台」再漏网。

覆盖：客房冒物流、论坛默认私信/推荐、应急仍打卡、无 recommend 标签残留、
前端 DOM-* 业务分支、全 catalog × 常见开题矩阵。
"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.domain_schema import build_domain_schema
from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
from app.bake.engine_sql import domain_sql
from app.bake.schema.templates import SCHEMA_BUILDERS
from app.bake.skin_invariants import (
    assert_skin_invariants,
    check_frontend_skin_leaks,
    check_schema_skin_leaks,
)

_REPO = Path(__file__).resolve().parents[2]
_FE_SRC = _REPO / "skeletons" / "baseline" / "frontend" / "src"

# 每域至少一题；多场景域覆盖串台高发档
_OPENINGS: dict[str, list[tuple[str, str]]] = {
    "DOM-LIBRARY": [("高校图书借阅", "读者借还")],
    "DOM-EQUIP": [("实验室器材借用", "借用人申请")],
    "DOM-ASSET": [("物资申领", "申领人申请")],
    "DOM-CRM": [
        ("中小企业客户跟进", "销售跟进客户"),
        ("学院孵化项目跟进", "导师跟进学生项目"),
    ],
    "DOM-EVENT": [
        ("校园晨午检", "班主任维护学生档案"),
        ("社区健康监测", "网格员上报居民"),
        ("社区公共卫生事件应急上报", "网格员上报公共卫生事件"),
        ("养老机构巡访", "家属查看照护"),
        ("企业复工监测", "员工每日健康打卡"),
    ],
    "DOM-ATTEND": [("学生请假", "学生请假"), ("员工考勤", "员工请假")],
    "DOM-FUND": [("学生资助", "困难生申请"), ("员工福利", "员工申请福利")],
    "DOM-LABSAFE": [("实验室安全", "学生巡检")],
    "DOM-RECRUIT": [("校园招聘", "求职者投递")],
    "DOM-DATING": [("婚恋交友", "会员牵线")],
    "DOM-GRADE": [("成绩管理", "学生查成绩")],
    "DOM-INTERN": [("实习管理", "实习生周报")],
    "DOM-PARCEL": [("校园驿站", "取件人取件")],
    "DOM-DORM": [("宿舍报修", "学生报修")],
    "DOM-PROPERTY": [("校园物业", "师生报修"), ("小区物业", "业主报修")],
    "DOM-IT": [("校园运维", "师生报障"), ("企业运维", "员工报障")],
    "DOM-ACTIVITY": [("活动报名", "报名者报名")],
    "DOM-LOST": [
        ("校园失物", "师生认领"),
        ("社区失物", "居民认领"),
        ("宠物领养", "领养申请"),
    ],
    "DOM-COURSE": [("选课系统", "学生选课")],
    "DOM-SHOP": [("二手商城", "买家下单"), ("校园二手", "学生交易")],
    "DOM-FOOD": [("食堂点餐", "用餐者点餐"), ("外卖点餐", "顾客点餐")],
    "DOM-HOSPITAL": [
        ("医院挂号", "患者挂号"),
        ("宠物医院", "宠主挂号"),
        ("疫苗预约", "接种人预约"),
    ],
    "DOM-PARKING": [("车位预约", "车主预约"), ("校园车位", "师生预约")],
    "DOM-MEETING": [("会议室预约", "预约人订会议室")],
    "DOM-SALON": [("美发预约", "顾客预约"), ("健身房预约", "会员预约")],
    "DOM-HOTEL": [("民宿预订", "住客预订")],
    "DOM-MEDIA": [("影视点播", "用户点播"), ("校园媒资", "师生点播")],
    "DOM-MUSIC": [("在线音乐", "用户听歌"), ("校园音乐", "师生点播")],
    "DOM-FORUM": [("校园论坛", "师生发帖"), ("社区论坛", "居民发帖")],
    "DOM-BLOG": [("个人博客", "读者浏览"), ("校园博客", "师生写作")],
    "DOM-GENERIC": [("信息管理", "增删改查")],
}


class DomainSkinLeakRegressionTests(unittest.TestCase):
    def test_all_builders_present(self) -> None:
        self.assertGreaterEqual(len(SCHEMA_BUILDERS), 30)

    def test_openings_cover_every_named_domain(self) -> None:
        missing = [d for d in DOMAINS if d not in _OPENINGS]
        self.assertEqual(missing, [], f"错皮矩阵缺域: {missing}")

    def test_hotel_stay_not_logistics(self) -> None:
        s = build_domain_schema("客房预订系统", "DOM-HOTEL")
        order = (s.get("entities") or {}).get("order") or {}
        self.assertEqual(order.get("fulfillMode"), "stay")
        self.assertEqual((order.get("verbs") or {}).get("ship"), "办理入住")
        self.assertNotIn("物流", str(order))

    def test_forum_no_default_dm_recommend(self) -> None:
        caps = DOMAIN_CAPABILITIES["DOM-FORUM"]
        self.assertNotIn("dm", caps)
        self.assertNotIn("recommend", caps)
        s = build_domain_schema("高校校园论坛", "DOM-FORUM", proposal_text="发帖回帖审核")
        self.assertNotIn("dm", s.get("capabilities") or [])
        self.assertNotIn("recommend", s.get("capabilities") or [])
        self.assertNotIn("recommendSectionTitle", (s.get("labels") or {}))
        self.assertEqual(
            ((s.get("entities") or {}).get("ticket") or {}).get("verbs", {}).get("apply"),
            "回复",
        )

    def test_event_incident_not_monitor_skin(self) -> None:
        s = build_domain_schema(
            "社区公共卫生事件应急上报系统",
            "DOM-EVENT",
            proposal_text="社区网格员上报公共卫生事件。",
        )
        self.assertEqual((s.get("entities") or {}).get("archive", {}).get("label"), "事件")
        self.assertEqual((s.get("labels") or {}).get("archiveLogSubmitLabel"), "登记巡查")
        sql = domain_sql(
            "DOM-EVENT",
            "audit",
            title="社区公共卫生事件应急上报系统",
            proposal_text="社区网格员上报。",
        )
        self.assertIn("聚集性发热线索", sql)
        self.assertNotIn("体温异常待回访", sql)

    def test_no_recommend_label_without_cap(self) -> None:
        for domain, builder in sorted(SCHEMA_BUILDERS.items()):
            with self.subTest(domain=domain):
                s = builder("测试课题")
                caps = s.get("capabilities") or []
                labels = s.get("labels") or {}
                if "recommend" not in caps:
                    self.assertNotIn(
                        "recommendSectionTitle",
                        labels,
                        f"{domain} 无 recommend 却有 recommendSectionTitle",
                    )

    def test_order_domains_only_shop_food_hotel(self) -> None:
        with_orders = [
            d for d, caps in DOMAIN_CAPABILITIES.items() if "order_lines" in caps
        ]
        self.assertEqual(set(with_orders), {"DOM-SHOP", "DOM-FOOD", "DOM-HOTEL"})
        hotel = build_domain_schema("酒店", "DOM-HOTEL")
        self.assertEqual(
            ((hotel.get("entities") or {}).get("order") or {}).get("fulfillMode"),
            "stay",
        )

    def test_matrix_no_known_skin_leaks(self) -> None:
        """全 catalog × 常见开题：已知错皮模式零命中。"""
        for domain, cases in sorted(_OPENINGS.items()):
            for title, body in cases:
                with self.subTest(domain=domain, title=title):
                    schema = build_domain_schema(title, domain, proposal_text=body)
                    issues = check_schema_skin_leaks(
                        schema,
                        domain=domain,
                        title=title,
                        proposal_text=body,
                    )
                    self.assertEqual(issues, [], issues)

    def test_baseline_frontend_no_dom_branch(self) -> None:
        """骨架前端禁止 DOM-* 业务分支（Login 材料清洗除外）。"""
        self.assertTrue(_FE_SRC.is_dir(), _FE_SRC)
        issues = check_frontend_skin_leaks(_FE_SRC)
        self.assertEqual(issues, [], issues)

    def test_assert_skin_invariants_blocks_hotel_logistics(self) -> None:
        schema = build_domain_schema("酒店", "DOM-HOTEL")
        schema = dict(schema)
        order = dict((schema.get("entities") or {}).get("order") or {})
        order["fulfillMode"] = "ship"
        order["verbs"] = {**(order.get("verbs") or {}), "ship": "发货物流"}
        ents = dict(schema.get("entities") or {})
        ents["order"] = order
        schema["entities"] = ents
        with self.assertRaises(ValueError):
            assert_skin_invariants(schema, domain="DOM-HOTEL", title="酒店")


if __name__ == "__main__":
    unittest.main()
