"""领域目录 — HOSPITAL/PARKING/MEETING/SALON/HOTEL。"""

from __future__ import annotations

from app.bake.gate_contracts import (
    gate_slot_shell,
)

DOMAINS: dict = {
    "DOM-HOSPITAL": {
        "label": "医院",
        # 勿单列「医院」「宠物医院」：院感/病患随访正文易误伤；挂号语义 +「宠物挂号」挂靠
        "keywords": [
            "挂号", "就诊", "门诊", "就医", "诊疗", "分诊",
            "宠物挂号",
            "疫苗预约", "接种预约", "HPV", "疫苗接种预约",
        ],
        "match_hint": (
            "适用：挂号预约、门诊分诊、疫苗/HPV 接种预约；题名含宠物+挂号时走宠物医院挂号皮。"
            "院感防控、病患随访、隔离观察、慢病随访选事件上报，不要选本域。"
        ),
        "entities": ["Doctor", "Department", "Appointment"],
        "roles": ["patient", "admin", "subadmin"],
        "flows": ["选科室 → 挂号 → 就诊"],
        "features": [
            {"name": "患者登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "科室医生", "status": "domain"},
            {"name": "挂号预约", "status": "flow"},
            {"name": "患者管理", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "电子病历", "status": "out_of_mvp"},
            {"name": "处方开药", "status": "out_of_mvp"},
            {"name": "检验检查", "status": "out_of_mvp"},
            {"name": "排队叫号大屏", "status": "out_of_mvp"},
            {"name": "医保对接/结算", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["电子病历", "处方开药", "检验检查", "排队叫号大屏", "医保对接/结算"],
        "themes": [
            {"id": "hosp-blue", "label": "医护蓝"},
            {"id": "hosp-mint", "label": "洁净绿"},
            {"id": "hosp-coral", "label": "分诊醒目"},
            {"id": "hosp-sky", "label": "候诊淡青"},
            {"id": "hosp-night", "label": "值班深色"},
        ],
        "gate": gate_slot_shell(
            archive_feature="科室医生",
            reserve_feature="挂号预约",
            users_feature="患者管理",
        ),
        "runtime": {
            "enable_ticket": False,
            "register_role": "patient",
            "archive_category_table": "category",
            "archive_item_table": "doctor",
            "slot_table": "resource_slot",
            "reservation_table": "reservation",
            "use_quota": False,
        },
    },
    "DOM-PARKING": {
        "label": "车位",
        "keywords": ["车位", "停车", "预约车位", "泊车", "停车场", "停车管理"],
        "match_hint": "适用：停车场车位时段预约。勿与场地预约（会议室/球馆）或客房预订混淆。",
        "entities": ["ParkingLot", "Space", "Reservation"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["选车位 → 预约 → 入场"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "车位检索", "status": "domain"},
            {"name": "车位预约", "status": "flow"},
            {"name": "用户管理", "status": "module"},
            {"name": "公告管理", "status": "module"},
        ],
        "out_of_mvp": [],
        "themes": [
            {"id": "park-asphalt", "label": "车位灰蓝"},
            {"id": "park-signal", "label": "通行绿"},
            {"id": "park-amber", "label": "警示黄"},
            {"id": "park-cyan", "label": "导航青"},
            {"id": "park-night", "label": "地库夜色"},
        ],
        "gate": gate_slot_shell(
            archive_feature="车位检索",
            reserve_feature="车位预约",
        ),
        "runtime": {
            "enable_ticket": False,
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "space",
            "slot_table": "resource_slot",
            "reservation_table": "reservation",
            "use_quota": False,
        },
    },
    "DOM-MEETING": {
        "label": "场地预约",
        # 会议室 + 校园常见场地；皮肤文案按题名在 schema 里再细化
        "keywords": [
            "会议室", "会议室预约", "会议预约",
            "琴房", "琴房预约", "排练厅", "舞蹈室",
            "体育场", "体育馆", "球馆", "羽毛球场", "篮球场", "足球场",
            "自习室", "研习室", "研讨室",
            "座位预约", "占座", "选座", "图书馆座位", "自习座位",
            "预约占座", "图书馆占座", "工位预约",
            "场地预约", "订场", "实验室预约", "实训室预约", "游泳馆",
        ],
        "match_hint": "适用：会议室、球馆、琴房、自习室、座位/占座、工位等场地时段预约。勿与车位预约或服务预约（美发/健身）混淆。",
        "entities": ["Room", "Reservation"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["选场地 → 预约 → 取消/完成"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "场地检索", "status": "domain"},
            {"name": "时段预约", "status": "flow"},
            {"name": "用户管理", "status": "module"},
            {"name": "公告管理", "status": "module"},
        ],
        "out_of_mvp": [],
        "themes": [
            {"id": "meet-blue", "label": "会议蓝"},
            {"id": "meet-gray", "label": "洽谈灰"},
            {"id": "meet-green", "label": "空闲绿"},
            {"id": "meet-night", "label": "夜间预约"},
        ],
        "gate": gate_slot_shell(
            archive_feature="场地检索",
            reserve_feature="时段预约",
        ),
        "runtime": {
            "enable_ticket": False,
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "room",
            "slot_table": "resource_slot",
            "reservation_table": "reservation",
            "use_quota": False,
        },
    },
    "DOM-SALON": {
        "label": "服务预约",
        "keywords": [
            "美发", "美容", "美容院", "理发预约", "服务预约",
            "健身", "健身房", "私教", "私教预约", "健身预约", "瑜伽预约",
        ],
        "match_hint": (
            "适用：美发美容、健身私教等服务项目时段预约。"
            "勿与场地预约（会议室/球馆/座位）或医院挂号混淆。"
        ),
        "entities": ["Service", "Slot", "Booking"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["选服务 → 预约时段 → 到店完成"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "服务浏览", "status": "domain"},
            {"name": "服务与预约", "status": "flow"},
            {"name": "用户管理", "status": "module"},
            {"name": "公告管理", "status": "module"},
        ],
        "out_of_mvp": [],
        "themes": [
            {"id": "salon-rose", "label": "护理玫瑰"},
            {"id": "salon-cream", "label": "沙龙暖米"},
            {"id": "salon-ink", "label": "造型墨"},
            {"id": "salon-night", "label": "夜场预约"},
        ],
        "gate": gate_slot_shell(
            archive_feature="服务浏览",
            reserve_feature="服务与预约",
        ),
        "runtime": {
            "enable_ticket": False,
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "service",
            "slot_table": "resource_slot",
            "reservation_table": "reservation",
            "use_quota": False,
        },
    },
    "DOM-HOTEL": {
        "label": "客房",
        "keywords": ["宾馆", "客房", "酒店", "民宿", "酒店预订", "住宿预订"],
        "match_hint": "适用：酒店/民宿客房预订入住。勿与场地预约或商城交易混淆。",
        "entities": ["Room", "Booking", "Order"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["选房 → 预订 → 入住/离店"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "房型浏览", "status": "domain"},
            {"name": "预订订单", "status": "flow"},
            {"name": "用户管理", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "真支付对接", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["真支付对接"],
        "themes": [
            {"id": "hotel-gold", "label": "酒店金"},
            {"id": "hotel-navy", "label": "客房藏蓝"},
            {"id": "hotel-sand", "label": "大堂暖沙"},
            {"id": "hotel-night", "label": "夜宿深色"},
        ],
        "gate": gate_slot_shell(
            archive_feature="房型浏览",
            reserve_feature="预订订单",
            with_orders=True,
        ),
        "runtime": {
            "enable_ticket": False,
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "room_type",
            "slot_table": "resource_slot",
            "reservation_table": "reservation",
            "order_cart_table": "cart_line",
            "order_table": "biz_order",
            "order_line_table": "order_line",
            "use_quota": False,
        },
    }
}
