"""仪器机时 FOLLOWUP_PRESETS（P-19 · C-07）。"""

from __future__ import annotations

from typing import Any, Callable


def build_instrument_followup_presets(
    _std_archive_fields: Callable[..., list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    return {
        "DOM-INSTRUMENT": {
            "doc": "仪器机时：仪器档案 + 借用单 + 机时时段预约（主路径约机时）。",
            "user_label": "使用人",
            "admin_label": "平台主管（总管）",
            "subadmin_label": "仪器管理员",
            "archive_key": "instrument",
            "archive_label": "仪器",
            "archive_plural": "仪器",
            "archive_fields": _std_archive_fields(
                "仪器名称",
                "所属实验室",
                "型号/说明",
                "状态",
                ["开放", "维护", "停用"],
                "分类",
                "可预约",
            ),
            "stock_display": "toggle",
            "ticket_key": "instrument_loan",
            "ticket_label": "借用申请",
            "ticket_plural": "借用申请",
            "verbs": {
                "apply": "提交借用",
                "approve": "通过",
                "reject": "驳回",
                "return": "归还完结",
                "remind": "催还",
            },
            "states": {
                "pending": "待审",
                "approved": "借用中",
                "rejected": "已驳回",
                "returned": "已归还",
                "overdue": "已逾期",
            },
            "archive_menu_admin": "仪器档案",
            "archive_menu_user": "仪器目录",
            "auth_eyebrow": "仪器机时",
            "auth_lead": "验证码登录；浏览仪器约机时，必要时提交借用申请。",
            "auth_points": ["验证码登录", "机时预约", "借用申请与审批"],
            "register_hint": "注册后可预约机时",
            "notice_title": "仪器机时须知",
            "notice_body": "请先预约机时再上机；外带仪器须另提借用申请。本期无物联网联机计费。",
            "notice_page_title": "平台公告",
            "notice_page_lead": "上机须知与临时通知，点击条目阅读全文。",
            "my_tickets_label": "我的借用",
            "pending_label": "待审借用",
            "records_label": "借用记录",
            "remark_label": "借用说明",
            "with_deadline": True,
            "auto_approve": False,
            "approve_ends_flow": False,
            "contact_channel_label": "用途",
            "contact_channel_options": ["教学", "科研", "测试服务", "其他"],
            "contact_channel_placeholder": "选择用途",
            "next_follow_label": "计划归还日",
            "postprocess": "instrument_slot",
            "banners": [
                {"title": "仪器目录", "lead": "浏览可预约仪器。"},
                {"title": "约机时", "lead": "选择时段占机。"},
                {"title": "借用申请", "lead": "外带或长时占用可另提单据。"},
                {"title": "平台公告", "lead": "须知见公告栏。"},
                {"title": "我的预约/借用", "lead": "跟踪进度。"},
            ],
        },
    }
