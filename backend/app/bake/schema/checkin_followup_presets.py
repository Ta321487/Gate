"""查寝签到 FOLLOWUP_PRESETS（P-22 · C-10）。"""

from __future__ import annotations

from typing import Any, Callable


def build_checkin_followup_presets(
    _std_archive_fields: Callable[..., list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    return {
        "DOM-CHECKIN": {
            "doc": "查寝签到：寝室档案 + 归寝登记审核 + 窗口内口令签到（结束未签到记缺勤）。",
            "user_label": "学生",
            "admin_label": "宿管主管（总管）",
            "subadmin_label": "查寝员",
            "archive_key": "dorm_room",
            "archive_label": "寝室",
            "archive_plural": "寝室",
            "archive_fields": [
                {"key": "title", "label": "寝室号", "type": "string"},
                {"key": "author", "label": "楼栋", "type": "string"},
                {"key": "isbn", "label": "说明", "type": "string"},
                {"key": "category", "label": "楼区/批次", "type": "select"},
                {"key": "stock", "label": "应签人数", "type": "number"},
                {"key": "checkinCode", "label": "签到码", "type": "string"},
                {"key": "startAt", "label": "查寝开始", "type": "datetime", "timeStepMinutes": 30},
                {"key": "endAt", "label": "查寝结束", "type": "datetime", "timeStepMinutes": 30},
            ],
            "stock_display": "count",
            "ticket_key": "checkin_apply",
            "ticket_label": "归寝签到",
            "ticket_plural": "归寝签到",
            "verbs": {
                "apply": "归寝登记",
                "approve": "通过",
                "reject": "驳回",
                "return": "撤销登记",
                "remind": "催签",
            },
            "states": {
                "pending": "待审",
                "approved": "签到中",
                "rejected": "已驳回",
                "returned": "已签到",
                "overdue": "缺勤",
            },
            "archive_menu_admin": "寝室档案",
            "archive_menu_user": "寝室目录",
            "auth_eyebrow": "查寝签到",
            "auth_lead": (
                "验证码登录；选择寝室提交归寝登记，宿管审核通过后凭签到码完成归寝签到；"
                "窗口结束后未签到记缺勤。"
            ),
            "auth_points": ["验证码登录", "寝室目录", "归寝登记与口令签到"],
            "register_hint": "注册后可归寝登记",
            "notice_title": "查寝须知",
            "notice_body": (
                "请先提交归寝登记并等待宿管审核；通过后在查寝窗口内凭签到码完成归寝签到。"
                "人脸/GPS 不在本期。窗口结束后仍未签到记缺勤。"
            ),
            "notice_page_title": "宿管公告",
            "notice_page_lead": "查寝安排与须知，点击条目阅读全文。",
            "messages_page_lead": "审核结果、查寝提醒与系统通知。",
            "my_tickets_label": "我的归寝",
            "pending_label": "归寝审核",
            "records_label": "归寝记录",
            "remark_label": "签到说明",
            "auto_approve": False,
            "approve_ends_flow": True,
            "allow_checkin": True,
            "no_show_after_end": True,
            "no_show_penalty_yuan": 0,
            "checkin_label": "归寝签到",
            "require_remark": False,
            "contact_channel_label": "归寝类型",
            "contact_channel_options": ["正常归寝", "晚归", "请假外出", "其他"],
            "contact_channel_placeholder": "正常/晚归等",
            "next_follow_label": "备注日",
            "banners": [
                {"title": "寝室目录", "lead": "按楼栋浏览查寝寝室与窗口。"},
                {"title": "归寝登记", "lead": "提交登记后等待宿管审核。"},
                {"title": "口令签到", "lead": "审核通过后在窗口内输入签到码完成归寝。"},
                {"title": "缺勤台账", "lead": "窗口结束后未签到记缺勤。"},
                {"title": "我的归寝", "lead": "查看本人签到与缺勤记录。"},
            ],
        },
    }
