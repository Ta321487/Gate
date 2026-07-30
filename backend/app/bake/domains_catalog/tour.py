"""领域目录 — 旅行社线路报名（P-31 · 组 C）。"""

from __future__ import annotations

from app.bake.gate_contracts import gate_archive_ticket

DOMAINS: dict = {
    "DOM-TOUR": {
        "label": "旅行社线路",
        "keywords": [
            "旅行社",
            "旅游线路",
            "跟团游",
            "旅游报名",
            "线路报名",
            "出团",
            "旅游团",
            "组团游",
            "旅游产品报名",
            "线路产品",
            "跟团报名",
            "旅行社管理系统",
            "旅游管理系统",
        ],
        "match_hint": (
            "适用：旅行社线路/团期产品档案、游客报名占名额、审核确认出团（无地图/真支付）。"
            "勿与酒店民宿客房预订、校园社团活动报名、拼车结伴行程、公务出差审批或商城套餐下单混淆。"
        ),
        "entities": ["Archive", "Category", "Ticket", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["浏览线路 → 提交报名 → 审核占名额 → 出团确认"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "线路档案", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "线路报名审核", "status": "flow"},
            {"name": "报名记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "地图导航/导游轨迹", "status": "out_of_mvp"},
            {"name": "OTA渠道同步", "status": "out_of_mvp"},
            {"name": "真支付分账", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["地图导航", "导游GPS轨迹", "OTA渠道同步", "真支付分账"],
        "themes": [
            {"id": "tour-teal", "label": "旅行青绿"},
            {"id": "tour-sand", "label": "旅行暖沙"},
            {"id": "tour-slate", "label": "旅行灰青"},
            {"id": "tour-night", "label": "旅行深色"},
        ],
        "gate": gate_archive_ticket(
            archive_feature="线路档案",
            flow_feature="线路报名审核",
            records_feature="报名记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "tour_signup",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "tour_line",
        },
    },
}
