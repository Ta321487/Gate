"""领域目录 — 时间银行 / 志愿时长账户（C-14）。"""

from __future__ import annotations

from app.bake.gate_contracts import gate_archive_ticket

DOMAINS: dict = {
    "DOM-TIMEBANK": {
        "label": "时间银行",
        "keywords": [
            "时间银行",
            "志愿时长账户",
            "时长账户",
            "存入时长",
            "时长核销",
            "时间币",
            "互助时长",
            "时长存取",
            "志愿时数账户",
            "社区时间银行",
        ],
        "match_hint": (
            "适用：志愿时长账户余额、台账加减、核销申请审核。"
            "勿与劳动教育项目时长认定（劳动时长认定）、社团活动报名占名额混淆。"
        ),
        "entities": ["Archive", "Category", "Ticket", "Timebank", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["服务事项存入时长 → 账户余额 → 核销申请 → 审核扣减"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "服务事项", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "时长账户与流水", "status": "flow"},
            {"name": "核销申请审核", "status": "flow"},
            {"name": "核销记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "真支付兑现/跨校联盟", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["真支付兑现", "跨校联盟", "人脸核销"],
        "themes": [
            {"id": "timebank-teal", "label": "时间银行青绿"},
            {"id": "timebank-sand", "label": "时间银行暖沙"},
            {"id": "timebank-slate", "label": "时间银行灰青"},
            {"id": "timebank-night", "label": "时间银行深色"},
        ],
        "gate": gate_archive_ticket(
            archive_feature="服务事项",
            flow_feature="核销申请审核",
            records_feature="核销记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "tb_redeem",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "tb_service",
        },
    },
}
