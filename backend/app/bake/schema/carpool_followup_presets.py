"""拼车结伴 FOLLOWUP_PRESETS（C-13）。"""

from __future__ import annotations

from typing import Any, Callable


def build_carpool_followup_presets(
    _std_archive_fields: Callable[..., list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    return {
        "DOM-CARPOOL": {
            "doc": "拼车结伴：行程档案 + 同行意向单。",
            "user_label": "同行者",
            "admin_label": "拼车主管（总管）",
            "subadmin_label": "对接员",
            "archive_key": "trip_route",
            "archive_label": "行程",
            "archive_plural": "行程",
            "archive_fields": _std_archive_fields(
                "行程标题",
                "发布人",
                "时间地点备注",
                "状态",
                ["开放", "满员", "取消"],
                "分类",
                "余座",
            ),
            "stock_display": "number",
            "ticket_key": "carpool_intent",
            "ticket_label": "同行意向",
            "ticket_plural": "同行意向",
            "verbs": {
                "apply": "提交意向",
                "approve": "同意对接",
                "reject": "婉拒",
                "return": "完结",
                "remind": "催办",
            },
            "states": {
                "pending": "待对接",
                "approved": "已对接",
                "rejected": "已婉拒",
                "returned": "已完结",
                "overdue": "已逾期",
            },
            "archive_menu_admin": "行程档案",
            "archive_menu_user": "行程目录",
            "auth_eyebrow": "拼车结伴",
            "auth_lead": "验证码登录；浏览行程并提交同行意向，管理员审核对接（无地图）。",
            "auth_points": ["验证码登录", "行程发布", "意向对接"],
            "register_hint": "注册后可提交同行意向",
            "notice_title": "拼车须知",
            "notice_body": "请如实填写同行说明；本期无地图导航与真支付分账。",
            "notice_page_title": "拼车公告",
            "notice_page_lead": "出行须知与临时通知，点击条目阅读全文。",
            "my_tickets_label": "我的意向",
            "pending_label": "待对接意向",
            "records_label": "意向记录",
            "remark_label": "同行说明",
            "auto_approve": False,
            "approve_ends_flow": True,
            "contact_channel_label": "对接方式",
            "contact_channel_options": ["站内留言", "电话联系", "线下碰面", "其他"],
            "contact_channel_placeholder": "选择对接方式",
            "next_follow_label": "期望出行日",
            "banners": [
                {"title": "行程目录", "lead": "浏览可对接行程。"},
                {"title": "提交意向", "lead": "填写说明提交同行意向。"},
                {"title": "拼车公告", "lead": "须知见公告栏。"},
                {"title": "我的意向", "lead": "跟踪对接进度。"},
                {"title": "分类检索", "lead": "按路线类型筛选。"},
            ],
        },
    }
