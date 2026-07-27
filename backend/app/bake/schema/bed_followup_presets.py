"""床位分配 FOLLOWUP_PRESETS（P-20/P-21 · C-08）。"""

from __future__ import annotations

from typing import Any, Callable


def build_bed_followup_presets(
    _std_archive_fields: Callable[..., list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    return {
        "DOM-BED": {
            "doc": "床位分配：床位档案 + 选房/调宿申请（配额占用）。",
            "user_label": "学生",
            "admin_label": "宿管主管（总管）",
            "subadmin_label": "宿管员",
            "archive_key": "bed",
            "archive_label": "床位",
            "archive_plural": "床位",
            "archive_fields": _std_archive_fields(
                "床位号",
                "楼栋",
                "说明",
                "状态",
                ["空闲", "已分配", "维修中", "开放"],
                "房型/事项",
                "可占用",
            ),
            "stock_display": "available",
            "ticket_key": "bed_apply",
            "ticket_label": "床位申请",
            "ticket_plural": "床位申请",
            "verbs": {
                "apply": "提交申请",
                "approve": "分配通过",
                "reject": "驳回",
                "return": "退宿办结",
                "remind": "催办",
            },
            "states": {
                "pending": "待审",
                "approved": "已分配",
                "rejected": "已驳回",
                "returned": "已退宿",
                "overdue": "已失效",
            },
            "archive_menu_admin": "床位档案",
            "archive_menu_user": "床位目录",
            "auth_eyebrow": "床位分配",
            "auth_lead": "验证码登录；浏览空闲床位提交选房或调宿申请，宿管审核后占用。",
            "auth_points": ["验证码登录", "床位目录", "选房/调宿申请"],
            "register_hint": "注册后可选房或申请调宿",
            "notice_title": "床位申请须知",
            "notice_body": "选房通过后占用床位；调宿/退宿请写明原床位。本期无门锁对接。",
            "notice_page_title": "宿管公告",
            "notice_page_lead": "分床与调宿通知，点击条目阅读全文。",
            "my_tickets_label": "我的床位申请",
            "pending_label": "床位审批",
            "records_label": "床位申请记录",
            "remark_label": "申请说明",
            "auto_approve": False,
            "approve_ends_flow": True,
            "contact_channel_label": "申请类型",
            "contact_channel_options": ["新生选房", "调宿", "退宿", "其他"],
            "contact_channel_placeholder": "选房/调宿/退宿",
            "next_follow_label": "期望入住日",
            "banners": [
                {"title": "床位目录", "lead": "按楼栋与房型浏览空闲床位。"},
                {"title": "选房申请", "lead": "选择床位提交申请，审核通过后占用。"},
                {"title": "调宿退宿", "lead": "选择调宿/退宿事项并填写说明。"},
                {"title": "宿管公告", "lead": "分床节点与须知见公告栏。"},
                {"title": "我的申请", "lead": "跟踪审批与分配结果。"},
            ],
        },
    }
