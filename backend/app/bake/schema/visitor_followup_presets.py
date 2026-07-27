"""访客登记 FOLLOWUP_PRESETS（P-17 · C-09）。"""

from __future__ import annotations

from typing import Any, Callable


def build_visitor_followup_presets(
    _std_archive_fields: Callable[..., list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    return {
        "DOM-VISITOR": {
            "doc": "访客登记：到访区域 + 访客申请 + 审过签发通行码。",
            "user_label": "来访人",
            "admin_label": "门卫主管（总管）",
            "subadmin_label": "接待员",
            "archive_key": "visit_zone",
            "archive_label": "到访区域",
            "archive_plural": "到访区域",
            "archive_fields": _std_archive_fields(
                "区域名称",
                "楼栋/位置",
                "接待说明",
                "状态",
                ["开放", "暂停", "关闭"],
                "区域类型",
                "可预约",
            ),
            "stock_display": "count",
            "ticket_key": "visitor_apply",
            "ticket_label": "访客申请",
            "ticket_plural": "访客申请",
            "verbs": {
                "apply": "预约到访",
                "approve": "通过并发卡",
                "reject": "驳回",
                "return": "取消预约",
                "remind": "催办",
            },
            "states": {
                "pending": "待审",
                "approved": "已发卡",
                "rejected": "已驳回",
                "returned": "已取消",
                "overdue": "已失效",
            },
            "archive_menu_admin": "到访区域",
            "archive_menu_user": "区域目录",
            "auth_eyebrow": "访客登记",
            "auth_lead": "验证码登录；选择到访区域提交预约，审核通过后获得通行码。",
            "auth_points": ["验证码登录", "区域目录", "预约到访与通行码"],
            "register_hint": "注册后可预约到访",
            "notice_title": "访客须知",
            "notice_body": "请如实填写来访事由；通过后出示通行码。真门禁硬件不在本期。",
            "notice_page_title": "访客公告",
            "notice_page_lead": "到访安排与须知，点击条目阅读全文。",
            "my_tickets_label": "我的预约",
            "pending_label": "访客审批",
            "records_label": "访客记录",
            "remark_label": "来访事由",
            "auto_approve": False,
            "approve_ends_flow": True,
            "issue_pass_code": True,
            "pass_code_label": "通行码",
            "contact_channel_label": "来访类型",
            "contact_channel_options": ["公务拜访", "家长来访", "快递取件陪同", "其他"],
            "contact_channel_placeholder": "公务/家长等",
            "next_follow_label": "预计到访日",
            "banners": [
                {"title": "区域目录", "lead": "浏览可预约到访区域。"},
                {"title": "预约到访", "lead": "填写事由提交申请。"},
                {"title": "通行码", "lead": "审核通过后签发通行码。"},
                {"title": "访客公告", "lead": "须知见公告栏。"},
                {"title": "我的预约", "lead": "跟踪审批与通行码。"},
            ],
        },
    }
