"""领域目录 — 互选双选（P-09～P-11 · C-05）。"""

from __future__ import annotations

from app.bake.gate_contracts import gate_archive_ticket

DOMAINS: dict = {
"DOM-MUTUAL-TUTOR": {
    "label": "导师双选",
    "keywords": ["导师双选", "双向选择", "导师志愿", "研究生导师选择", "导师互选", "选导", "导师确认"],
    "match_hint": (
        "适用：研究生导师双向选择：浏览导师 → 提交志愿 → 导师确认/婉拒，管理可调剂。勿与婚恋交友牵线（婚恋交友）或招聘投递混淆。"
    ),
    "entities": ["Archive", "Category", "Ticket", "Notice"],
    "roles": ["user", "admin", "subadmin"],
    "flows": ["浏览导师 → 提交志愿 → 对方确认/婉拒（管理可调剂）"],
    "features": [
        {"name": "登录", "status": "baseline"},
        {"name": "个人资料与头像", "status": "baseline"},
        {"name": "管理端工作台", "status": "module"},
        {"name": "导师档案", "status": "domain"},
        {"name": "分类管理", "status": "module"},
        {"name": "用户管理", "status": "module"},
        {"name": "志愿互选确认", "status": "flow"},
        {"name": "管理调剂", "status": "module"},
        {"name": "志愿记录", "status": "module"},
        {"name": "公告管理", "status": "module"},
    ],
    "out_of_mvp": ["智能推荐算法", "多轮志愿排序引擎"],
    "themes": [
        {"id": "tutor-teal", "label": "导师双选青绿"},
        {"id": "tutor-sand", "label": "导师双选暖沙"},
        {"id": "tutor-slate", "label": "导师双选灰青"},
        {"id": "tutor-night", "label": "导师双选深色"},
    ],
    "gate": gate_archive_ticket(
        archive_feature="导师档案",
        flow_feature="志愿互选确认",
        records_feature="志愿记录",
        users_feature="用户管理",
        category_feature="分类管理",
        with_deadline=False,
    ),
    "portal_banners": True,
    "runtime": {
        "ticket_mode": "archive",
        "ticket_table": "tutor_wish",
        "register_role": "user",
        "archive_category_table": "category",
        "archive_item_table": "tutor",
    },
},

"DOM-MUTUAL-TOPIC": {
    "label": "选题双选",
    "keywords": ["选题双选", "毕业论文选题", "毕业设计选题", "选题志愿", "课题双选", "毕设选题互选", "选题确认"],
    "match_hint": (
        "适用：毕业论文/设计选题双向选择：浏览选题 → 提交志愿 → 指导教师确认，管理可调剂。勿与公选课选课占名额或招聘投递混淆。"
    ),
    "entities": ["Archive", "Category", "Ticket", "Notice"],
    "roles": ["user", "admin", "subadmin"],
    "flows": ["浏览选题 → 提交志愿 → 对方确认/婉拒（管理可调剂）"],
    "features": [
        {"name": "登录", "status": "baseline"},
        {"name": "个人资料与头像", "status": "baseline"},
        {"name": "管理端工作台", "status": "module"},
        {"name": "选题档案", "status": "domain"},
        {"name": "分类管理", "status": "module"},
        {"name": "用户管理", "status": "module"},
        {"name": "志愿互选确认", "status": "flow"},
        {"name": "管理调剂", "status": "module"},
        {"name": "志愿记录", "status": "module"},
        {"name": "公告管理", "status": "module"},
    ],
    "out_of_mvp": ["智能推荐算法", "多轮志愿排序引擎"],
    "themes": [
        {"id": "topic-teal", "label": "选题双选青绿"},
        {"id": "topic-sand", "label": "选题双选暖沙"},
        {"id": "topic-slate", "label": "选题双选灰青"},
        {"id": "topic-night", "label": "选题双选深色"},
    ],
    "gate": gate_archive_ticket(
        archive_feature="选题档案",
        flow_feature="志愿互选确认",
        records_feature="志愿记录",
        users_feature="用户管理",
        category_feature="分类管理",
        with_deadline=False,
    ),
    "portal_banners": True,
    "runtime": {
        "ticket_mode": "archive",
        "ticket_table": "topic_wish",
        "register_role": "user",
        "archive_category_table": "category",
        "archive_item_table": "thesis_topic",
    },
},

"DOM-MUTUAL-TEAM": {
    "label": "组队匹配",
    "keywords": ["竞赛组队", "学习搭子", "组队匹配", "组队意向", "搭子匹配", "队友互选", "学习小组匹配"],
    "match_hint": (
        "适用：竞赛组队/学习搭子意向匹配：建资料 → 投意向 → 对方确认组队，管理可调剂。"
        "勿与婚恋交友、活动报名或拼车/结伴出行（行程同行意向）混淆。"
    ),
    "entities": ["Archive", "Category", "Ticket", "Notice"],
    "roles": ["user", "admin", "subadmin"],
    "flows": ["浏览组队资料 → 提交志愿 → 对方确认/婉拒（管理可调剂）"],
    "features": [
        {"name": "登录", "status": "baseline"},
        {"name": "个人资料与头像", "status": "baseline"},
        {"name": "管理端工作台", "status": "module"},
        {"name": "组队资料档案", "status": "domain"},
        {"name": "分类管理", "status": "module"},
        {"name": "用户管理", "status": "module"},
        {"name": "志愿互选确认", "status": "flow"},
        {"name": "管理调剂", "status": "module"},
        {"name": "志愿记录", "status": "module"},
        {"name": "公告管理", "status": "module"},
    ],
    "out_of_mvp": ["智能推荐算法", "多轮志愿排序引擎"],
    "themes": [
        {"id": "team-teal", "label": "组队匹配青绿"},
        {"id": "team-sand", "label": "组队匹配暖沙"},
        {"id": "team-slate", "label": "组队匹配灰青"},
        {"id": "team-night", "label": "组队匹配深色"},
    ],
    "gate": gate_archive_ticket(
        archive_feature="组队资料档案",
        flow_feature="志愿互选确认",
        records_feature="志愿记录",
        users_feature="用户管理",
        category_feature="分类管理",
        with_deadline=False,
    ),
    "portal_banners": True,
    "runtime": {
        "ticket_mode": "archive",
        "ticket_table": "team_wish",
        "register_role": "user",
        "archive_category_table": "category",
        "archive_item_table": "team_profile",
    },
},
}
