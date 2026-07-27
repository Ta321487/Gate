"""领域目录 — LIBRARY/EQUIP/ASSET/CRM/EVENT/ATTEND/FUND/LABSAFE/RECRUIT/GRADE/INTERN/PARCEL。"""

from __future__ import annotations

from app.bake.gate_contracts import (
    gate_archive_ticket,
)

DOMAINS: dict = {
    "DOM-LIBRARY": {
        "label": "图书",
        "keywords": [
            "图书", "借阅", "图书馆", "读者", "图书借阅", "借还管理", "馆藏",
            "档案借阅", "卷宗借阅", "档案馆", "档案室", "图书漂流", "漂流图书",
        ],
        "match_hint": (
            "适用：图书借阅、读者借还审核；档案馆/卷宗借阅、图书漂流（仍走借还审核）亦挂本域。"
            "勿与设备借用（器材/实验室）或选课混淆。"
            "勿与制度/课件文库下载台账（文库资料）混淆——借还审核≠附件下载台账。"
        ),
        "entities": ["Book", "Category", "Borrow", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["申请借阅 → 审核 → 归还", "逾期提醒 → 归还 / 罚款登记"],
        "features": [
            {"name": "读者注册 / 登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "图书检索与详情", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "读者管理", "status": "module"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "借阅申请 → 审核", "status": "flow"},
            {"name": "自选应还日 / 申请数量", "status": "flow"},
            {"name": "借阅记录", "status": "module"},
            {"name": "归还 / 逾期", "status": "flow"},
            {"name": "逾期提醒与罚款", "status": "flow"},
            {"name": "公告管理", "status": "module"},
            {"name": "猜你喜欢", "status": "module"},
            {"name": "人脸识别进馆", "status": "out_of_mvp"},
            {"name": "协同过滤推荐", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["人脸识别", "协同过滤推荐"],
        "themes": [
            {"id": "lib-ink", "label": "墨蓝书香"},
            {"id": "lib-grove", "label": "青松阅览"},
            {"id": "lib-amber", "label": "暖光自习"},
            {"id": "lib-plum", "label": "梅影典藏"},
            {"id": "lib-slate", "label": "石青检索"},
            {"id": "lib-night", "label": "夜读静谧"},
        ],
        "gate": gate_archive_ticket(
            archive_feature="图书检索与详情",
            flow_feature="借阅申请 → 审核",
            records_feature="借阅记录",
            users_feature="读者管理",
            category_feature="分类管理",
            overdue_feature="逾期提醒与罚款",
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "borrow",
            "register_role": "reader",
            "archive_category_table": "category",
            "archive_item_table": "book",
        },
    },
    "DOM-EQUIP": {
        "label": "设备借用",
        "keywords": [
            "设备借用", "器材", "实验室设备", "物资借用", "实验室管理",
            "仪器借用", "实验器材", "设备租借",
            "雨伞租借", "充电宝租借", "门禁卡租借", "钥匙租借",
            "服装租借", "道具租借", "演出器材", "共享雨伞", "共享充电宝",
        ],
        "match_hint": (
            "适用：实验室/器材借用归还审核；校园轻资产（雨伞/充电宝/门禁卡）与演出服装道具租借亦挂本域。"
            "勿与物资领用（耗材/试剂出库）、图书借阅或「仪器借用+机时预约」一体题混淆"
            "（机时一体选 DOM-INSTRUMENT，勿只落本域而丢掉预约）。"
        ),
        "entities": ["Equip", "Category", "Loan", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["申请借用 → 审核 → 归还"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "设备检索", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "借用申请 → 审核", "status": "flow"},
            {"name": "自选应还日 / 申请数量", "status": "flow"},
            {"name": "借用记录", "status": "module"},
            {"name": "归还 / 逾期", "status": "flow"},
            {"name": "公告管理", "status": "module"},
            {"name": "猜你喜欢", "status": "module"},
            {"name": "硬件交付（开题提及）", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["硬件交付"],
        "themes": [
            {"id": "equip-steel", "label": "器械钢蓝"},
            {"id": "equip-amber", "label": "警示琥珀"},
            {"id": "equip-mint", "label": "实验青绿"},
            {"id": "equip-night", "label": "夜间库房"},
        ],
        "gate": gate_archive_ticket(
            archive_feature="设备检索",
            flow_feature="借用申请 → 审核",
            records_feature="借用记录",
            users_feature="用户管理",
            category_feature="分类管理",
            overdue_feature="归还 / 逾期",
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "loan",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "equip",
        },
    },
    "DOM-ASSET": {
        "label": "物资领用",
        "keywords": [
            "固定资产",
            "耗材申领",
            "物资申领",
            "仓储物资",
            "物资领用",
            "仓库领用",
            "资产领用",
            "资产台账",
            "办公用品申领",
            "耗材管理",
            "入库出库",
            "出入库",
            "应急物资",
            "物资仓储",
            "仓储调度",
            "物资调度",
            "冷链仓储",
            "冷库",
            "货品台账",
            "实验耗材",
            "试剂申领",
            "耗材出库",
            "危化品领用",
            "办公用品",
            "劳保领用",
            "劳保用品",
        ],
        "match_hint": (
            "适用：物资/耗材/试剂/办公用品/劳保领用、仓储出入库、应急物资调度台账、冷链仓储温湿度台账。"
            "正文顺带提公卫/疫情时，若题名是仓储物资仍选本域，勿改事件上报。"
            "勿与实验室安全准入（培训许可进室）混淆；准入选实验室安全准入。"
            "勿与采购申购单审批（未入库前的申购）混淆。"
        ),
        "entities": ["Asset", "Category", "Requisition", "StockIo", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": [
            "提交申领 → 审核出库 → 可选退库",
            "管理端入库/出库登记 → 调整库存 → 流水台账",
        ],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "入出库与库存流水", "status": "flow"},
            {"name": "物资目录", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "申领审核", "status": "flow"},
            {"name": "申领数量", "status": "flow"},
            {"name": "申领记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "RFID/条码全链路盘点", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["RFID/条码全链路盘点"],
        "themes": [
            {"id": "asset-olive", "label": "仓储橄榄"},
            {"id": "asset-clay", "label": "库房暖陶"},
            {"id": "asset-slate", "label": "台账灰青"},
            {"id": "asset-night", "label": "盘点深色"},
        ],
        "gate": gate_archive_ticket(
            archive_feature="物资目录",
            flow_feature="申领审核",
            records_feature="申领记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "requisition",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "asset",
        },
    },
    "DOM-CRM": {
        "label": "客户跟进",
        "keywords": [
            "CRM",
            "客户关系",
            "客户管理",
            "客户跟进",
            "销售线索",
            "线索管理",
            "客户档案",
            "家访",
            "谈心谈话",
            "法律援助",
            "案件跟进",
            "律所案件",
            "校企合作",
            "合作单位",
            "单位库",
        ],
        "match_hint": (
            "适用：客户档案、销售线索跟进审核；学工家访/谈心谈话、法律援助案件、校企合作单位库跟进亦挂本域。"
            "勿与事件上报（公卫排查）、房源中介带看或合同登记单级审批混淆。"
        ),
        "entities": ["Customer", "Category", "FollowUp", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["客户建档 → 提交跟进 → 审核完结"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "客户档案", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "客户跟进", "status": "flow"},
            {"name": "跟进记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "外呼中心/公海池", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["外呼中心/公海池"],
        "themes": [
            {"id": "crm-ocean", "label": "客户海蓝"},
            {"id": "crm-slate", "label": "商务灰青"},
            {"id": "crm-sand", "label": "线索暖沙"},
            {"id": "crm-night", "label": "夜访深色"},
        ],
        "gate": gate_archive_ticket(
            archive_feature="客户档案",
            flow_feature="客户跟进",
            records_feature="跟进记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "follow_up",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "customer",
        },
    },
    "DOM-EVENT": {
        "label": "事件上报",
        # 词表只做硬分流；长尾说法交给 match_recommend（见 match_hint）
        # 词表预算 ≤20；长尾说法靠 match_hint + 题名（见 test_event_keyword_budget）
        "keywords": [
            "事件上报",
            "公共卫生",
            "公共卫生事件",
            "院感",
            "感染防控",
            "晨检",
            "晨午检",
            "排查",
            "传染病",
            "随访",
            "流调",
            "网格化",
            "健康监测",
            "因病缺课",
            "健康筛查",
            "食品安全",
            "复工监测",
            "走访打卡",
            "巡检打卡",
            "慢病随访",
        ],
        "match_hint": (
            "适用：公卫应急、院感、晨午检、慢性病随访、养老/员工健康监测、网格排查、"
            "食安风险排查、流调协查、网格走访打卡、消防/设备巡检打卡等「建档+打卡/随访+上报」题。"
            "健康打卡/随访 ≠ 请销假（考勤请假）；请销假勿选本域。"
            "献血/开放日若主写「报名占名额」选活动报名，勿因出现献血一词误落本域。"
            "不适用：门诊挂号（医院）、食堂点餐（点餐）、纯应急物资仓储（物资领用）、"
            "宿舍卫生整改工单（宿舍报修）。"
            "开题主写物资出入库勿选本域。"
            "简易问卷配置/填写/回收选问卷调研（DOM-SURVEY），勿用本域冒充完整量表引擎。"
        ),
        "entities": ["EventCase", "Category", "EventReport", "ArchiveLog", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["对象建档 → 打卡/随访记录 → 异常上报处置"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "事件档案", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "健康打卡/监测记录", "status": "domain"},
            {"name": "事件上报", "status": "flow"},
            {"name": "上报记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "疾控直报对接", "status": "out_of_mvp"},
            {"name": "物资仓储出入库", "status": "out_of_mvp"},
            {"name": "复杂量表/跳题逻辑", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["疾控直报对接", "物资仓储出入库", "复杂量表/跳题逻辑"],
        # 简易问卷见 DOM-SURVEY（C-03）
        "themes": [
            {"id": "event-teal", "label": "应急青绿"},
            {"id": "event-amber", "label": "警示琥珀"},
            {"id": "event-slate", "label": "台账灰青"},
            {"id": "event-night", "label": "值班深色"},
        ],
        "gate": gate_archive_ticket(
            archive_feature="事件档案",
            flow_feature="事件上报",
            records_feature="上报记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "event_report",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "event_case",
        },
    },
    "DOM-ATTEND": {
        "label": "考勤请假",
        "keywords": [
            "请假", "销假", "考勤请假", "请假管理", "请假审批", "请假系统",
            "请假申请", "请销假", "事假", "病假", "假勤", "出勤管理",
            "学生请假", "员工请假",
        ],
        "match_hint": (
            "适用：员工/学生请假申请与审批、销假、假勤台账（单据向）。"
            "不承诺人脸/指纹闸机或 GPS 轨迹打卡；硬件考勤/定位打卡不在本期。"
            "勿与宿舍查寝归寝签到（查寝签到）、出差/加班（DOM-TRIP）、用车申请或公卫健康打卡/晨午检混淆。"
        ),
        "entities": ["StaffPerson", "Category", "LeaveReq", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["人员建档 → 提交请假 → 审批销假"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "人员档案", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "请假审批", "status": "flow"},
            {"name": "请假记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "人脸考勤", "status": "out_of_mvp"},
            {"name": "GPS轨迹打卡", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["人脸考勤", "GPS轨迹打卡"],
        "themes": [
            {"id": "attend-sky", "label": "假勤天蓝"},
            {"id": "attend-leaf", "label": "销假叶绿"},
            {"id": "attend-slate", "label": "台账灰青"},
            {"id": "attend-night", "label": "值班深色"},
        ],
        "gate": gate_archive_ticket(
            archive_feature="人员档案",
            flow_feature="请假审批",
            records_feature="请假记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "leave_req",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "staff_person",
        },
    },
    "DOM-FUND": {
        "label": "资助奖学金",
        "keywords": [
            "资助", "奖学金", "助学金", "困难补助", "奖助学金",
            "学生资助", "资助申请", "助学贷款", "勤工助学补助",
            "员工福利", "企业补助", "职工补助", "福利申请",
            "困难认定",
        ],
        "match_hint": (
            "适用：奖助学金/困难补助/助学贷款认定等资助项目发布与学生申请审核；"
            "或企业员工福利/补助申请审核。"
            "勿与经费报销、用章申请、开具证明等 OA 申请壳混淆（那些另有预设/深皮）。"
            "勿与创新学分/竞赛获奖登记（DOM-AWARD）或综测申报混淆。"
            "勿与大创/科研项目申报中期检查、采购申购或合同审批混淆。"
            "勿与招聘投递、选课或活动报名混淆；勤工助学「岗位投递」选招聘投递。"
        ),
        "entities": ["FundProgram", "Category", "FundApply", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["项目发布 → 提交申请 → 资助审核"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "资助项目", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "资助审批", "status": "flow"},
            {"name": "申请记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "银行直发对接", "status": "out_of_mvp"},
            {"name": "学工部大数据画像", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["银行直发对接", "学工部大数据画像"],
        "themes": [
            {"id": "fund-sky", "label": "资助天蓝"},
            {"id": "fund-leaf", "label": "助学叶绿"},
            {"id": "fund-slate", "label": "台账灰青"},
            {"id": "fund-night", "label": "夜审深色"},
        ],
        "gate": gate_archive_ticket(
            archive_feature="资助项目",
            flow_feature="资助审批",
            records_feature="申请记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "fund_apply",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "fund_program",
        },
    },
    "DOM-LABSAFE": {
        "label": "实验室安全准入",
        "keywords": [
            "实验室安全", "安全准入", "准入申请", "入室许可",
            "实验室准入", "安全培训证明", "实验室许可",
            "厂区", "安环", "企业实验室", "EHS准入",
        ],
        "match_hint": (
            "适用：实验室/实训室安全培训与准入申请审核；"
            "或厂区/安环实验室准入。"
            "勿与实验耗材/试剂申领出库（物资领用）、实验室器材借用（设备）"
            "或实验室工位时段预约（场地预约）混淆。"
        ),
        "entities": ["LabRoom", "Category", "AccessApply", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["实验室建档 → 准入申请 → 安全审核"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "实验室档案", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "准入审批", "status": "flow"},
            {"name": "准入记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "门禁硬件开锁", "status": "out_of_mvp"},
            {"name": "危化品全链路台账", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["门禁硬件开锁", "危化品全链路台账"],
        "themes": [
            {"id": "labsafe-sky", "label": "准入天蓝"},
            {"id": "labsafe-leaf", "label": "安全叶绿"},
            {"id": "labsafe-slate", "label": "台账灰青"},
            {"id": "labsafe-night", "label": "值班深色"},
        ],
        "gate": gate_archive_ticket(
            archive_feature="实验室档案",
            flow_feature="准入审批",
            records_feature="准入记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "access_apply",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "lab_room",
        },
    },
    "DOM-RECRUIT": {
        "label": "招聘投递",
        "keywords": [
            "招聘", "投递", "校招", "应聘", "简历投递", "校园招聘",
            "岗位发布", "招聘系统", "人才招聘", "网申", "职位申请",
            "招聘岗位", "双选会", "求职投递",
            "勤工助学", "助教岗", "社会招聘", "内部竞聘", "社招",
        ],
        "match_hint": (
            "适用：岗位发布、简历投递、初筛/录用审核（找工作/投简历）；"
            "勤工助学岗/助教岗申请、社会招聘/内部竞聘亦挂本域。"
            "勿与实习周报（已建档岗交周报/鉴定，实习管理）混淆；"
            "题名主写周报审阅勿选本域。勿与客户跟进（CRM）混淆。"
        ),
        "entities": ["JobPost", "Category", "JobApply", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["岗位发布 → 简历投递 → 初筛录用"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "岗位档案", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "投递审核", "status": "flow"},
            {"name": "投递记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "视频面试", "status": "out_of_mvp"},
            {"name": "ATS爬虫导入", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["视频面试", "ATS爬虫导入"],
        "themes": [
            {"id": "recruit-coral", "label": "校招珊瑚"},
            {"id": "recruit-ocean", "label": "岗位海蓝"},
            {"id": "recruit-sand", "label": "简历暖沙"},
            {"id": "recruit-night", "label": "夜招深色"},
        ],
        "gate": gate_archive_ticket(
            archive_feature="岗位档案",
            flow_feature="投递审核",
            records_feature="投递记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "job_apply",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "job_post",
        },
    },
    "DOM-DATING": {
        "label": "婚恋交友",
        "keywords": [
            "婚恋", "相亲", "交友", "红娘", "牵线", "征婚", "择偶",
            "婚恋交友", "相亲平台", "交友系统", "会员资料", "恋爱交友",
            "婚姻介绍", "相亲资料", "牵线申请",
        ],
        "match_hint": (
            "适用：会员/交友资料建档、浏览与牵线意向审核（红娘撮合）。"
            "有婚恋资料+牵线主线时优先本域；开题点到的收藏/留言/推荐走能力交叉挂载，勿因出现活动/论坛/商城一词就换域。"
            "题名主业务是活动报名、论坛发帖或婚宴酒店/婚纱商城时再分别选活动/论坛/酒店/商城。"
            "勿与导师双选/毕设选题/组队匹配（DOM-MUTUAL-*）或招聘投递、客户跟进（CRM）混淆。"
            "勿与拼车/结伴出行意向对接（拼车结伴）混淆——婚恋牵线≠行程同行。"
        ),
        "entities": ["DatingProfile", "Category", "MatchApply", "Dm", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["资料建档 → 牵线意向 → 红娘审核撮合"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "交友资料", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "牵线审核", "status": "flow"},
            {"name": "牵线记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "一对一私信", "status": "module"},
            {"name": "视频相亲", "status": "out_of_mvp"},
            {"name": "红娘费支付", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["视频相亲", "红娘费支付"],
        "themes": [
            {"id": "dating-rose", "label": "相亲玫粉"},
            {"id": "dating-coral", "label": "联谊珊瑚"},
            {"id": "dating-ink", "label": "资料墨蓝"},
            {"id": "dating-night", "label": "夜谈深色"},
        ],
        "gate": gate_archive_ticket(
            archive_feature="交友资料",
            flow_feature="牵线审核",
            records_feature="牵线记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "match_apply",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "dating_profile",
        },
    },
    "DOM-GRADE": {
        "label": "教务成绩",
        "keywords": [
            "成绩", "补考", "成绩管理", "成绩查询", "成绩更正", "教务成绩",
            "成绩登记", "成绩系统", "成绩录入", "补考申请", "成绩审核",
            "绩点查询", "成绩申请",
            "内训", "培训成绩", "员工考核", "培训结业", "岗位认证",
        ],
        "match_hint": (
            "适用：课程成绩台账、补考/成绩更正申请与教务审核；"
            "或企业内训/培训成绩与考核申请。"
            "勿与学籍异动/转专业/缓考申请（DOM-ACAD）、开具成绩单证明（DOM-CERT）混淆。"
            "勿与网上评教（DOM-EVAL）、综测德育分申报（DOM-MORAL）、创新学分成果登记（DOM-AWARD）混淆。"
            "勿与伦理/开题答辩材料审核（非成绩更正）或选课占名额混淆。"
        ),
        "entities": ["CourseItem", "Category", "GradeApply", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["课程建档 → 补考/更正申请 → 教务确认"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "课程档案", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "成绩申请审核", "status": "flow"},
            {"name": "成绩申请记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "学信网对接", "status": "out_of_mvp"},
            {"name": "复杂绩点引擎", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["学信网对接", "复杂绩点引擎"],
        "themes": [
            {"id": "grade-ink", "label": "教务墨蓝"},
            {"id": "grade-leaf", "label": "成绩青绿"},
            {"id": "grade-amber", "label": "补考琥珀"},
            {"id": "grade-night", "label": "夜查深色"},
        ],
        "gate": gate_archive_ticket(
            archive_feature="课程档案",
            flow_feature="成绩申请审核",
            records_feature="成绩申请记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "grade_apply",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "course_item",
        },
    },
    "DOM-INTERN": {
        "label": "实习周报",
        "keywords": [
            "实习", "周报", "实习周报", "实习管理", "实习鉴定", "实习岗位",
            "学生实习", "顶岗实习", "实习系统", "实习导师", "实习单位",
            "实习报告", "校外实习", "实习考勤",
            "企业带教", "带教导师", "入职实习",
        ],
        "match_hint": (
            "适用：已建档实习岗的周报提交与导师/辅导员审阅（含顶岗实习、企业带教）；"
            "本系统为选示范岗交周报，≠同时入职多家单位。"
            "勿与校园招聘/简历投递初筛（招聘投递）或活动报名混淆；"
            "题名主写投简历找岗勿选本域。"
        ),
        "entities": ["InternPost", "Category", "WeekReport", "ESign", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": [
            "实习岗建档 → 提交周报 → 导师审阅",
            "鉴定签署：上传签章图 → 勾选同意 → 留痕",
        ],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "实习岗位", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "周报审阅", "status": "flow"},
            {"name": "周报记录", "status": "module"},
            {"name": "本地签章", "status": "flow"},
            {"name": "公告管理", "status": "module"},
            {"name": "电子签章 CA/第三方签平台", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["电子签章 CA/第三方签平台"],
        "themes": [
            {"id": "intern-teal", "label": "实习青绿"},
            {"id": "intern-sand", "label": "周报暖沙"},
            {"id": "intern-slate", "label": "鉴定灰青"},
            {"id": "intern-night", "label": "夜写深色"},
        ],
        "gate": gate_archive_ticket(
            archive_feature="实习岗位",
            flow_feature="周报审阅",
            records_feature="周报记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "week_report",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "intern_post",
        },
    },
    "DOM-PARCEL": {
        "label": "快递驿站",
        "keywords": [
            "快递", "驿站", "取件", "包裹", "快递驿站", "校园快递",
            "取件码", "快递代收", "驿站管理", "包裹取件", "代收点",
            "快递入库", "快递领取", "催取",
        ],
        "match_hint": (
            "适用：包裹入库、取件码核销、驿站取件申请。"
            "勿与校园跑腿代买/商城下单（商城或点餐）或失物招领混淆；"
            "智能柜硬件对接不在本期。"
        ),
        "entities": ["Parcel", "Category", "ParcelClaim", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["包裹入库 → 取件申请 → 核销出库"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "包裹台账", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "取件核销", "status": "flow"},
            {"name": "取件记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "智能柜硬件对接", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["智能柜硬件对接"],
        "themes": [
            {"id": "parcel-orange", "label": "包裹橙"},
            {"id": "parcel-sky", "label": "驿站天蓝"},
            {"id": "parcel-slate", "label": "柜号灰青"},
            {"id": "parcel-night", "label": "夜取深色"},
        ],
        "gate": gate_archive_ticket(
            archive_feature="包裹台账",
            flow_feature="取件核销",
            records_feature="取件记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "parcel_claim",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "parcel",
        },
    }
}
