"""领域目录 — 访客登记（P-17 · C-09）。"""

from __future__ import annotations

from app.bake.gate_contracts import gate_archive_ticket

DOMAINS: dict = {
    "DOM-VISITOR": {
        "label": "访客登记",
        "keywords": [
            "访客登记", "访客预约", "临时门禁", "来访登记",
            "访客申请", "访客通行", "到访预约", "访客管理",
        ],
        "match_hint": (
            "适用：访客到访预约与审核，通过后签发通行码（非真门禁硬件）。"
            "勿与实验室安全准入考试、会议室预约或车辆通行证混淆。"
        ),
        "entities": ["Archive", "Category", "Ticket", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["选区域 → 访客申请 → 审 → 签发通行码"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "到访区域", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "访客申请审核", "status": "flow"},
            {"name": "通行码", "status": "module"},
            {"name": "访客记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "真门禁硬件对接", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["真门禁硬件对接", "人脸闸机"],
        "themes": [
            {"id": "visitor-teal", "label": "访客青绿"},
            {"id": "visitor-sand", "label": "访客暖沙"},
            {"id": "visitor-slate", "label": "访客灰青"},
            {"id": "visitor-night", "label": "访客深色"},
        ],
        "gate": gate_archive_ticket(
            archive_feature="到访区域",
            flow_feature="访客申请审核",
            records_feature="访客记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "visitor_apply",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "visit_zone",
        },
    },
}
