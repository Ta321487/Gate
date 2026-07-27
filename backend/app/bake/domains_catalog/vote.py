"""领域目录 — 投票评选（C-04）。"""

from __future__ import annotations

from app.bake.gate_contracts import gate_archive_only

DOMAINS: dict = {
    "DOM-VOTE": {
        "label": "投票评选",
        "keywords": [
            "投票",
            "评选",
            "十佳",
            "选票",
            "投票评选",
            "在线投票",
            "候选人投票",
            "评选投票",
            "投票系统",
            "网络投票",
        ],
        "match_hint": (
            "适用：候选档案、每人一票或限票、结果公示的评选投票（无报名主路径）。"
            "开题同时写报名占名额 + 投票计票 → 活动报名并挂 vote（C-11），勿用本域顶替报名。"
            "勿与简易问卷填写回收、网上评教多维打分混淆。"
        ),
        "entities": ["Archive", "Category", "Vote", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["浏览评选 → 选候选人投票 → 结果公示"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "评选活动", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "投票与计票", "status": "flow"},
            {"name": "公告管理", "status": "module"},
            {"name": "刷票防护/实名公证", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["刷票防护", "区块链存证", "短信验证码投票"],
        "themes": [
            {"id": "vote-coral", "label": "评选珊瑚"},
            {"id": "vote-sky", "label": "选票天蓝"},
            {"id": "vote-lime", "label": "十佳青绿"},
            {"id": "vote-night", "label": "晚会夜色"},
        ],
        "gate": gate_archive_only(
            archive_feature="评选活动",
            users_feature="用户管理",
            category_feature="分类管理",
        ),
        "portal_banners": True,
        "runtime": {
            "enable_ticket": False,
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "vote_campaign",
        },
    },
}
