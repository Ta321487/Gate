"""全域错皮回归：禁止已踩过的「共享壳串台」再漏网。

覆盖：客房冒物流、论坛默认私信/推荐、应急仍打卡、无 recommend 标签残留、
前端 DOM-* 业务分支、消息页写死「订单/预约」导语、全 catalog × 常见开题矩阵。
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
    "DOM-LOST": [
        ("校园失物", "师生认领"),
        ("社区失物", "居民认领"),
        ("宠物领养", "领养申请"),
        ("捐赠物资认领", "物资认领"),
    ],
    "DOM-ACTIVITY": [
        ("活动报名", "报名者报名"),
        ("证书报考培训班", "报考人报名"),
        ("景区演出票务", "领票报名"),
        ("献血开放日", "场次报名"),
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
    "DOM-CARRENT": [("汽车租赁", "租车人选车取还")],
    "DOM-MEDIA": [("影视点播", "用户点播"), ("校园媒资", "师生点播")],
    "DOM-MUSIC": [("在线音乐", "用户听歌"), ("校园音乐", "师生点播")],
    "DOM-FORUM": [("校园论坛", "师生发帖"), ("社区论坛", "居民发帖")],
    "DOM-BLOG": [("个人博客", "读者浏览"), ("校园博客", "师生写作")],
    "DOM-GENERIC": [("信息管理", "增删改查")],
    # P/C 新域（错皮矩阵须覆盖 catalog 每一具名域）
    "DOM-SEAL": [("学校行政印章使用申请", "用章审批")],
    "DOM-FLEET": [("公务用车申请", "用车审批")],
    "DOM-CERT": [("在读证明开具申请", "开具证明")],
    "DOM-PROMO": [("横幅海报宣传审批", "宣传审批")],
    "DOM-FITOUT": [("装修进场施工备案", "装修备案")],
    "DOM-ACAD": [("学籍异动转专业申请", "异动审批")],
    "DOM-TRIP": [("出差加班审批", "出差审批")],
    "DOM-EXPENSE": [("经费报销申请", "报销审批")],
    "DOM-CREDIT": [("第二课堂学分认定", "学分认定")],
    "DOM-LABOR": [("劳动教育志愿时长认定", "时长认定")],
    "DOM-EVAL": [("学生网上评教", "评教打分")],
    "DOM-MORAL": [("综合测评德育分申报", "综测申报")],
    "DOM-AWARD": [("创新学分竞赛获奖登记", "成果登记")],
    "DOM-BED": [("宿舍床位分配选房", "选房申请")],
    "DOM-CHECKIN": [("宿舍查寝归寝签到", "归寝签到")],
    "DOM-MUTUAL-TUTOR": [("研究生导师双向选择", "导师双选")],
    "DOM-MUTUAL-TOPIC": [("毕设选题双向选择", "选题双选")],
    "DOM-MUTUAL-TEAM": [("竞赛组队学习搭子", "组队匹配")],
    "DOM-VISITOR": [("访客登记临时门禁", "访客申请")],
    "DOM-CARPASS": [("车辆通行证备案", "车辆通行")],
    "DOM-LISTING": [("房源挂牌带看跟进", "带看跟进")],
    "DOM-PROCURE": [("采购物资申购", "申购审批")],
    "DOM-CLUB": [("社团注册年审", "社团材料")],
    "DOM-PROJ": [("大创项目申报中期检查", "项目申报")],
    "DOM-ETHIC": [("伦理审查开题材料", "材料审核")],
    "DOM-PARTY": [("党员发展阶段材料", "入党台账")],
    "DOM-CONTRACT": [("合同登记审批", "合同审批")],
    "DOM-INSTRUMENT": [("大型仪器机时预约", "约机时")],
    "DOM-EXAM": [("在线题库考试判分", "在线考试")],
    "DOM-SURVEY": [("学生满意度问卷调查", "问卷填写")],
    "DOM-VOTE": [("校园十佳投票评选", "投票计票")],
    "DOM-DOCLIB": [("制度文件文库下载台账", "资料下载")],
    "DOM-CARPOOL": [("校园拼车同行意向", "拼车对接")],
    "DOM-TOUR": [("旅行社线路报名", "游客报名")],
    "DOM-TIMEBANK": [("时间银行志愿时长账户", "时长核销")],
    "DOM-CINEMA": [("影院选座购票", "选座下单")],
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

    def test_cinema_not_logistics_ship_copy(self) -> None:
        """R-TRADE-05：影院履约勿串商城发货/物流叙事。"""
        s = build_domain_schema("影院选座购票", "DOM-CINEMA")
        order = (s.get("entities") or {}).get("order") or {}
        self.assertEqual(order.get("fulfillMode"), "cinema")
        self.assertEqual((order.get("verbs") or {}).get("ship"), "出票")
        self.assertNotRegex(str(order.get("verbs") or {}), r"发货|物流")
        hint = str((s.get("labels") or {}).get("orderFulfillHint") or "")
        self.assertIn("无物流发货", hint)

    def test_reserve_role_leads_meeting_hotel_carrent(self) -> None:
        """R-RESERVE-01/02：预约组拆 Admin/Staff lead；HOTEL/CARRENT 禁发货串台。"""
        meeting = build_domain_schema(
            "会议室分时预约管理系统", "DOM-MEETING", proposal_text=""
        )
        mlab = meeting.get("labels") or {}
        self.assertIn("全场", str(mlab.get("reservationsAdminLead") or ""))
        self.assertRegex(str(mlab.get("reservationsStaffLead") or ""), r"审批|核销")

        hotel = build_domain_schema("酒店客房预订系统", "DOM-HOTEL")
        hlab = hotel.get("labels") or {}
        self.assertIn("全店", str(hlab.get("reservationsAdminLead") or ""))
        self.assertRegex(str(hlab.get("reservationsStaffLead") or ""), r"入住|离店")
        self.assertNotRegex(str(hlab.get("ordersAdminLead") or ""), r"发货|物流")
        self.assertIn("无物流发货", str(hlab.get("orderFulfillHint") or ""))
        boarding = build_domain_schema(
            "宠物寄养管理系统", "DOM-HOTEL", proposal_text="寄养位按日预订"
        )
        self.assertIn(
            "无物流发货",
            str((boarding.get("labels") or {}).get("orderFulfillHint") or ""),
        )

        carrent = build_domain_schema("汽车租赁管理系统", "DOM-CARRENT")
        clab = carrent.get("labels") or {}
        self.assertIn("全店", str(clab.get("reservationsAdminLead") or ""))
        self.assertRegex(str(clab.get("reservationsStaffLead") or ""), r"取车|还车")
        self.assertNotRegex(str(clab.get("ordersAdminLead") or ""), r"发货|物流")
        issues = check_schema_skin_leaks(hotel, domain="DOM-HOTEL")
        self.assertEqual(issues, [])
        issues = check_schema_skin_leaks(carrent, domain="DOM-CARRENT")
        self.assertEqual(issues, [])

    def test_reservations_admin_role_leads_by_super(self) -> None:
        """R-RESERVE-02：预约页按超管/前台挂 Admin vs Staff lead。"""
        root = Path(__file__).resolve().parents[2] / "skeletons" / "baseline"
        text = (
            root / "frontend/src/views/admin/ReservationsAdmin.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("reservationsAdminLead", text)
        self.assertIn("reservationsStaffLead", text)
        self.assertIn("page-lead", text)
        self.assertIn("pageLead", text)
        self.assertIn("superAdmin", text)
        self.assertRegex(text, r"if\s*\(\s*isSuper\.value\s*\)\s*return\s+adminLead")

    def test_borrow_role_leads_library_equip_parcel(self) -> None:
        """R-BORROW-01/02：图书/设备/驿站拆单据 lead；设备不得挂取书预约。"""
        library = build_domain_schema("图书借阅管理系统", "DOM-LIBRARY")
        llab = library.get("labels") or {}
        self.assertIn("全馆", str(llab.get("ticketsAdminLead") or ""))
        self.assertRegex(str(llab.get("ticketsStaffLead") or ""), r"借还|催还|柜台")

        equip = build_domain_schema("实验室设备借用系统", "DOM-EQUIP")
        elab = equip.get("labels") or {}
        self.assertIn("全室", str(elab.get("ticketsAdminLead") or ""))
        self.assertNotRegex(
            str(elab.get("ticketsAdminLead") or "") + str(elab.get("ticketsStaffLead") or ""),
            r"待取书|索书号|借阅额度",
        )
        et = (equip.get("entities") or {}).get("ticket") or {}
        self.assertFalse(et.get("allowBookHold"))
        self.assertNotIn("hold_ready", et.get("states") or {})

        parcel = build_domain_schema("校园快递驿站系统", "DOM-PARCEL")
        plab = parcel.get("labels") or {}
        self.assertIn("全站", str(plab.get("ticketsAdminLead") or ""))
        self.assertRegex(str(plab.get("ticketsStaffLead") or ""), r"核销|取件")

    def test_tickets_admin_role_leads_by_super(self) -> None:
        """R-BORROW-02：待审/记录页按超管挂 Admin vs Staff lead。"""
        root = Path(__file__).resolve().parents[2] / "skeletons" / "baseline"
        for rel in (
            "frontend/src/views/admin/TicketsAdmin.setup.js",
            "frontend/src/views/admin/TicketRecordsAdmin.setup.js",
        ):
            text = (root / rel).read_text(encoding="utf-8")
            self.assertIn("ticketsAdminLead", text, msg=rel)
            self.assertIn("ticketsStaffLead", text, msg=rel)
            self.assertIn("pageLead", text, msg=rel)
            self.assertIn("superAdmin", text, msg=rel)

    def test_ticket_repair_role_leads_dorm_property_it(self) -> None:
        """R-TICKET-01/02：报修组拆 lead；文案不含商城发货口吻。"""
        for domain, title, admin_needle, staff_needle in (
            ("DOM-DORM", "学生宿舍报修管理系统", "全楼", r"受理|派单"),
            ("DOM-PROPERTY", "小区物业报修系统", "全盘", r"受理|调度|派单"),
            ("DOM-IT", "校园运维报修系统", "全站", r"受理|接单"),
        ):
            with self.subTest(domain=domain):
                schema = build_domain_schema(title, domain)
                lab = schema.get("labels") or {}
                admin = str(lab.get("ticketsAdminLead") or "")
                staff = str(lab.get("ticketsStaffLead") or "")
                self.assertIn(admin_needle, admin)
                self.assertRegex(staff, staff_needle)
                blob = admin + staff + str(lab.get("authLead") or "")
                self.assertNotRegex(blob, r"发货|物流|购物车|商城")

    def test_follow_role_leads_intern_crm_event(self) -> None:
        """R-FOLLOW-01/02：跟进组拆 lead；不含商城/借阅串台。"""
        for domain, title, admin_needle, staff_needle in (
            ("DOM-INTERN", "顶岗实习岗位建档与每周周报导师审阅", "全员", r"周报|催交"),
            ("DOM-CRM", "客户关系跟进管理系统", "全盘", r"跟进|催办"),
            ("DOM-EVENT", "社区公共卫生事件应急上报系统", "全盘", r"随访|催办"),
        ):
            with self.subTest(domain=domain):
                schema = build_domain_schema(title, domain)
                lab = schema.get("labels") or {}
                admin = str(lab.get("ticketsAdminLead") or "")
                staff = str(lab.get("ticketsStaffLead") or "")
                self.assertIn(admin_needle, admin)
                self.assertRegex(staff, staff_needle)
                blob = admin + staff
                self.assertNotRegex(blob, r"发货|物流|购物车|待取书|借阅额度")

    def test_approve_role_leads_seal_expense(self) -> None:
        """R-APPROVE-01/02：审批组拆 lead；不含商城串台。"""
        for domain, title, admin_needle, staff_needle in (
            ("DOM-SEAL", "公文用章审批管理系统", "全盘", r"用章|核验|办结"),
            ("DOM-EXPENSE", "差旅报销多级审批系统", "全盘", r"初审|审批|完结"),
        ):
            with self.subTest(domain=domain):
                schema = build_domain_schema(title, domain)
                lab = schema.get("labels") or {}
                admin = str(lab.get("ticketsAdminLead") or "")
                staff = str(lab.get("ticketsStaffLead") or "")
                self.assertIn(admin_needle, admin)
                self.assertRegex(staff, staff_needle)
                blob = admin + staff
                self.assertNotRegex(blob, r"发货|物流|购物车|待取书|借阅额度")

    def test_apply_role_leads_activity_course(self) -> None:
        """R-APPLY-01/02：报名组拆 lead；不含商城串台。"""
        for domain, title, admin_needle, staff_needle in (
            ("DOM-ACTIVITY", "校园活动报名管理系统", "全盘", r"报名|签到|取消"),
            ("DOM-COURSE", "学生选课申请管理系统", "全盘", r"选课|退选|催办"),
        ):
            with self.subTest(domain=domain):
                schema = build_domain_schema(title, domain)
                lab = schema.get("labels") or {}
                admin = str(lab.get("ticketsAdminLead") or "")
                staff = str(lab.get("ticketsStaffLead") or "")
                self.assertIn(admin_needle, admin)
                self.assertRegex(staff, staff_needle)
                blob = admin + staff
                self.assertNotRegex(blob, r"发货|物流|购物车|待取书|借阅额度")

    def test_content_role_leads_forum_media(self) -> None:
        """R-CONTENT-01/02：内容组拆 lead；不含商城串台。"""
        for domain, title, admin_needle, staff_needle in (
            ("DOM-FORUM", "校园论坛发帖回帖管理系统", "全盘", r"审核|违规|催办"),
            ("DOM-MEDIA", "校园媒资点播管理系统", "全盘", r"上下架|媒资|催办"),
        ):
            with self.subTest(domain=domain):
                schema = build_domain_schema(title, domain)
                lab = schema.get("labels") or {}
                admin = str(lab.get("ticketsAdminLead") or "")
                staff = str(lab.get("ticketsStaffLead") or "")
                self.assertIn(admin_needle, admin)
                self.assertRegex(staff, staff_needle)
                blob = admin + staff
                self.assertNotRegex(blob, r"发货|物流|购物车|待取书|借阅额度|报名名额")

    def test_interact_role_leads_dating_survey(self) -> None:
        """R-INTERACT-01/02：互动组拆 lead；不含商城串台。"""
        for domain, title, admin_needle, staff_needle in (
            ("DOM-DATING", "校园交友匹配管理系统", "全盘", r"牵线|反馈|催办"),
            ("DOM-SURVEY", "问卷调查管理系统", "全盘", r"回收|催答|统计"),
        ):
            with self.subTest(domain=domain):
                schema = build_domain_schema(title, domain)
                lab = schema.get("labels") or {}
                admin = str(lab.get("ticketsAdminLead") or "")
                staff = str(lab.get("ticketsStaffLead") or "")
                self.assertIn(admin_needle, admin)
                self.assertRegex(staff, staff_needle)
                blob = admin + staff
                self.assertNotRegex(blob, r"发货|物流|购物车|待取书|借阅额度|报名名额")

    def test_fallback_role_leads_generic_paths(self) -> None:
        """R-FALLBACK-01/02：GENERIC 按路径拆 lead；交易壳勿写管理员发货。"""
        from app.bake.domain_schema import build_domain_schema

        flow = build_domain_schema(
            "业务申请审核系统",
            "DOM-GENERIC",
            archetype="ARCH-FLOW",
            archetypes=["ARCH-FLOW"],
        )
        lab = flow.get("labels") or {}
        self.assertIn("全盘", str(lab.get("ticketsAdminLead") or ""))
        self.assertRegex(str(lab.get("ticketsStaffLead") or ""), r"审核|催办|办结")

        trade = build_domain_schema(
            "校园二手交易系统",
            "DOM-GENERIC",
            archetype="ARCH-TRADE",
            archetypes=["ARCH-TRADE"],
        )
        tlab = trade.get("labels") or {}
        self.assertIn("全盘", str(tlab.get("ordersAdminLead") or ""))
        self.assertRegex(str(tlab.get("ordersStaffLead") or ""), r"履约|发货|自提")
        seed_body = str((trade.get("seeds") or {}).get("noticeBody") or "")
        self.assertNotIn("管理员确认发货", seed_body)
        self.assertNotRegex(
            str(tlab.get("ordersAdminLead") or ""), r"确认发货|处理发货"
        )

        reserve = build_domain_schema(
            "会议室预约系统",
            "DOM-GENERIC",
            archetype="ARCH-RESERVE",
            archetypes=["ARCH-RESERVE"],
        )
        rlab = reserve.get("labels") or {}
        self.assertIn("全盘", str(rlab.get("reservationsAdminLead") or ""))
        self.assertRegex(
            str(rlab.get("reservationsStaffLead") or ""), r"预约|催到|办结"
        )

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

    def test_order_domains_shop_food_hotel_cinema(self) -> None:
        with_orders = [
            d for d, caps in DOMAIN_CAPABILITIES.items() if "order_lines" in caps
        ]
        self.assertEqual(
            set(with_orders),
            {"DOM-SHOP", "DOM-FOOD", "DOM-HOTEL", "DOM-CINEMA", "DOM-CARRENT"},
        )
        hotel = build_domain_schema("酒店", "DOM-HOTEL")
        self.assertEqual(
            ((hotel.get("entities") or {}).get("order") or {}).get("fulfillMode"),
            "stay",
        )
        carrent = build_domain_schema("汽车租赁", "DOM-CARRENT")
        self.assertEqual(
            ((carrent.get("entities") or {}).get("order") or {}).get("fulfillMode"),
            "rental",
        )
        cinema = build_domain_schema("影院选座", "DOM-CINEMA")
        self.assertIn("seat_select", cinema.get("capabilities") or [])
        self.assertIn("order_lines", cinema.get("capabilities") or [])

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

    def test_marketplace_blocks_reserve_message_lead(self) -> None:
        """多店商城 messagesPageLead 不得串预约/待受理申请。"""
        from app.bake.schema.builders_slot import _shop_schema

        schema = _shop_schema("多商家电商", "商家入驻与店铺管理")
        self.assertTrue(schema.get("shopMarketplace"))
        issues = check_schema_skin_leaks(schema, domain="DOM-SHOP", title="多商家电商")
        self.assertEqual(issues, [], issues)
        bad = dict(schema)
        labels = dict(bad.get("labels") or {})
        labels["messagesPageLead"] = "待受理申请、新订单/预约等管理通知。"
        labels.pop("guestbookGuestCta", None)
        bad["labels"] = labels
        issues2 = check_schema_skin_leaks(bad, domain="DOM-SHOP", title="多商家电商")
        self.assertTrue(any("messagesPageLead" in i for i in issues2), issues2)
        self.assertTrue(any("guestbookGuestCta" in i for i in issues2), issues2)


if __name__ == "__main__":
    unittest.main()
