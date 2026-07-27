"""领域目录 — 在线考试 / 题库（C-01）。"""

from __future__ import annotations

from app.bake.gate_contracts import gate_archive_only

DOMAINS: dict = {
    "DOM-EXAM": {
        "label": "在线考试",
        "keywords": [
            "在线考试",
            "题库",
            "组卷",
            "刷题",
            "结业考试",
            "自动判分",
            "在线答题",
            "考试系统",
            "题库管理",
            "党建答题",
            "党史答题",
            "科目一",
            "驾校理论",
            "驾照题库",
            "入职安全考",
            "安全教育考试",
            "岗前安全答题",
            "培训结业考",
            "课程结业测验",
        ],
        "match_hint": (
            "适用：在线考试/题库组卷/刷题与自动判分（客观+主观自动判分）。"
            "勿与论坛跟帖、网上评教、实验室准入申请单（无题库主路径）混淆。"
        ),
        "entities": ["Archive", "Category", "Exam", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["录题 → 组卷发布 → 开考作答 → 自动判分 → 查成绩"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "考试科目", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "题库与组卷", "status": "flow"},
            {"name": "在线作答与判分", "status": "flow"},
            {"name": "公告管理", "status": "module"},
            {"name": "人脸监考/防切屏", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["人脸监考", "防切屏", "成绩导出 Excel", "电子证书"],
        "themes": [
            {"id": "exam-teal", "label": "考试青绿"},
            {"id": "exam-sand", "label": "考试暖沙"},
            {"id": "exam-slate", "label": "考试灰青"},
            {"id": "exam-night", "label": "考试深色"},
        ],
        "gate": gate_archive_only(
            archive_feature="考试科目",
            users_feature="用户管理",
            category_feature="分类管理",
        ),
        "portal_banners": True,
        "runtime": {
            "enable_ticket": False,
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "exam_subject",
        },
    },
}
