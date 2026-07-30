"""领域目录 — 查寝/归寝签到（P-22 · C-10）。"""

from __future__ import annotations

from app.bake.gate_contracts import gate_archive_ticket

DOMAINS: dict = {
    "DOM-CHECKIN": {
        "label": "查寝签到",
        "keywords": [
            "查寝", "归寝", "归寝签到", "宿舍签到", "晚归登记",
            "查寝签到", "归寝缺勤", "宿舍查寝", "寝室签到",
            "缺勤记录", "归寝打卡",
        ],
        "match_hint": (
            "适用：宿舍查寝/归寝口令签到、缺勤登记（单据向，非人脸/GPS）。"
            "勿与宿舍水电报修（宿舍报修）、床位选房调宿（床位分配）、请假假勤（考勤请假）"
            "或活动报名签到混淆。"
        ),
        "entities": ["Archive", "Category", "Ticket", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["浏览寝室 → 口令签到（结束未签到记缺勤）"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "寝室档案", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "口令签到", "status": "flow"},
            {"name": "结束未签到记缺勤", "status": "module"},
            {"name": "归寝记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "人脸签到", "status": "out_of_mvp"},
            {"name": "GPS轨迹打卡", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["人脸签到", "GPS轨迹打卡"],
        "themes": [
            {"id": "checkin-teal", "label": "查寝青绿"},
            {"id": "checkin-sand", "label": "查寝暖沙"},
            {"id": "checkin-slate", "label": "查寝灰青"},
            {"id": "checkin-night", "label": "查寝深色"},
        ],
        "gate": gate_archive_ticket(
            archive_feature="寝室档案",
            flow_feature="口令签到",
            records_feature="归寝记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "checkin_apply",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "dorm_room",
        },
    },
}
