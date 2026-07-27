"""领域目录 — 简易问卷 / 调研（C-03）。"""

from __future__ import annotations

from app.bake.gate_contracts import gate_archive_only

DOMAINS: dict = {
    "DOM-SURVEY": {
        "label": "问卷调研",
        "keywords": [
            "问卷",
            "调研",
            "调查表",
            "简易量表",
            "满意度调查",
            "问卷调查",
            "在线问卷",
            "问卷回收",
            "问卷统计",
        ],
        "match_hint": (
            "适用：简易问卷配置、填写、回收与选项计数统计。"
            "勿与网上评教多维打分、在线考试题库判分、论坛跟帖混淆。"
        ),
        "entities": ["Archive", "Category", "Survey", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["配置问卷 → 发布 → 填写提交 → 回收统计"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "问卷项目", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "问卷填写与回收", "status": "flow"},
            {"name": "公告管理", "status": "module"},
            {"name": "跳题逻辑/SPSS导出", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["跳题逻辑", "SPSS导出", "真匿名密码学"],
        "themes": [
            {"id": "survey-teal", "label": "问卷青绿"},
            {"id": "survey-sand", "label": "问卷暖沙"},
            {"id": "survey-slate", "label": "问卷灰青"},
            {"id": "survey-night", "label": "问卷深色"},
        ],
        "gate": gate_archive_only(
            archive_feature="问卷项目",
            users_feature="用户管理",
            category_feature="分类管理",
        ),
        "portal_banners": True,
        "runtime": {
            "enable_ticket": False,
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "survey_form",
        },
    },
}
