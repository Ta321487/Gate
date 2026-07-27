"""领域目录 — 床位分配（P-20/P-21 · C-08）。"""

from __future__ import annotations

from app.bake.gate_contracts import gate_archive_ticket

DOMAINS: dict = {
    "DOM-BED": {
        "label": "床位分配",
        "keywords": [
            "宿舍床位", "床位分配", "床位", "选房", "调宿", "退宿",
            "宿舍分配", "床位申请", "宿舍选房", "调宿申请", "退宿申请",
            "新生分床", "床位选择", "分床", "调宿退宿", "在线选房",
        ],
        "match_hint": (
            "适用：宿舍床位建档、选房/调宿/退宿申请与审核占用（库存床位）。"
            "勿与宿舍水电报修（宿舍报修）、查寝归寝签到（查寝签到）或请假考勤混淆。"
        ),
        "entities": ["Archive", "Category", "Ticket", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["浏览床位 → 选房/调宿申请 → 审分配占用"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "床位档案", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "床位申请审核", "status": "flow"},
            {"name": "床位申请记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
        ],
        "out_of_mvp": ["智能排宿算法", "门锁硬件"],
        "themes": [
            {"id": "bed-teal", "label": "床位青绿"},
            {"id": "bed-sand", "label": "床位暖沙"},
            {"id": "bed-slate", "label": "床位灰青"},
            {"id": "bed-night", "label": "床位深色"},
        ],
        "gate": gate_archive_ticket(
            archive_feature="床位档案",
            flow_feature="床位申请审核",
            records_feature="床位申请记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "bed_apply",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "bed",
        },
    },
}
