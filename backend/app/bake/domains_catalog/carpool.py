"""领域目录 — 拼车/结伴（C-13）。"""

from __future__ import annotations

from app.bake.gate_contracts import gate_archive_ticket

DOMAINS: dict = {
    "DOM-CARPOOL": {
        "label": "拼车结伴",
        "keywords": [
            "拼车",
            "顺风车",
            "结伴出行",
            "同行意向",
            "拼车信息",
            "约拼",
            "城际拼车",
            "校园拼车",
            "拼车对接",
            "结伴信息",
            "同行拼车",
        ],
        "match_hint": (
            "适用：行程档案发布、同行意向单审核对接（无地图/导航）。"
            "勿与婚恋交友牵线、学习搭子组队互选、社团活动报名占名额混淆。"
        ),
        "entities": ["Archive", "Category", "Ticket", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["浏览行程 → 提交同行意向 → 审核对接"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "行程档案", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "同行意向审核", "status": "flow"},
            {"name": "意向记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "地图导航/GPS轨迹", "status": "out_of_mvp"},
            {"name": "真支付分账", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["地图导航", "GPS轨迹", "真支付分账"],
        "themes": [
            {"id": "carpool-teal", "label": "拼车青绿"},
            {"id": "carpool-sand", "label": "拼车暖沙"},
            {"id": "carpool-slate", "label": "拼车灰青"},
            {"id": "carpool-night", "label": "拼车深色"},
        ],
        "gate": gate_archive_ticket(
            archive_feature="行程档案",
            flow_feature="同行意向审核",
            records_feature="意向记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "carpool_intent",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "trip_route",
        },
    },
}
