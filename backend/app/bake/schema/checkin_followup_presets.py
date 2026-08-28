"""查寝签到 FOLLOWUP_PRESETS（P-22 · C-10）。

主路径对齐常见毕设：资料绑定本人楼栋/寝室 →「我的归寝」对本寝场次登记
→ 审核 → 窗口内口令签到（结束未签记缺勤）。禁止「目录里随便选一间寝室」。
"""

from __future__ import annotations

from typing import Any, Callable


def build_checkin_followup_presets(
    _std_archive_fields: Callable[..., list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    return {
        "DOM-CHECKIN": {
            "doc": (
                "查寝签到：寝室档案 + 本人寝室归寝登记审核 + 窗口内口令签到"
                "（结束未签到记缺勤；matchProfileRoom 约束本寝）。"
            ),
            "user_label": "学生",
            "admin_label": "宿管主管（总管）",
            "subadmin_label": "查寝员",
            "archive_key": "dorm_room",
            "archive_label": "寝室",
            "archive_plural": "寝室",
            "archive_fields": [
                {"key": "title", "label": "寝室号", "type": "string"},
                {"key": "author", "label": "楼栋", "type": "string"},
                {"key": "isbn", "label": "房型说明", "type": "string"},
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
            "archive_menu_user": "查寝安排",
            "auth_eyebrow": "查寝签到",
            "auth_lead": (
                "验证码登录；资料确认本人楼栋与寝室后，在「我的归寝」对本寝室提交归寝登记，"
                "宿管审核通过后凭签到码完成归寝签到；窗口结束后未签到记缺勤。"
            ),
            "auth_points": ["验证码登录", "本人寝室归寝登记", "口令签到与缺勤"],
            "register_hint": "注册时填写本人楼栋与房间",
            "notice_title": "查寝须知",
            "notice_body": (
                "请先在个人资料填写本人楼栋与房间，再提交归寝登记并等待宿管审核；"
                "通过后在查寝窗口内凭签到码完成归寝签到。只能对本寝室场次登记。"
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
            # 与考勤请假同款：主路径在「我的*」填单；档案页作查寝安排说明
            "apply_from_list": True,
            "user_tickets_first": True,
            # 楼栋↔author、房间⊆title，禁止选他寝（见 TicketStore.assertMatchProfileRoomIfRequired）
            "match_profile_room": True,
            "my_tickets_page_lead": (
                "在此对本寝室提交归寝或晚归登记，并跟踪审核与口令签到；查寝安排页仅作查阅。"
            ),
            "my_tickets_empty": "还没有归寝记录，点击右上角归寝登记。",
            "contact_channel_label": "归寝类型",
            "contact_channel_options": ["正常归寝", "晚归", "请假外出", "其他"],
            "contact_channel_placeholder": "正常/晚归等",
            "next_follow_label": "备注日",
            "banners": [
                {"title": "本人寝室", "lead": "注册/资料中填写本人楼栋与房间，登记仅限本寝。"},
                {"title": "归寝登记", "lead": "在「我的归寝」对本寝场次提交登记，等待宿管审核。"},
                {"title": "口令签到", "lead": "审核通过后在窗口内输入签到码完成归寝。"},
                {"title": "缺勤台账", "lead": "窗口结束后未签到记缺勤。"},
                {"title": "查寝安排", "lead": "查阅各寝室查寝窗口与须知（不作选房）。"},
            ],
        },
    }
