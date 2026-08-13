"""拼车结伴 FOLLOWUP_PRESETS（C-13）。"""

from __future__ import annotations

from typing import Any, Callable


def build_carpool_followup_presets(
    _std_archive_fields: Callable[..., list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    return {
        "DOM-CARPOOL": {
            "doc": "拼车结伴：用户发行程 + 同行意向 + 车主确认（管理可调剂）。",
            "user_label": "拼车用户",
            "admin_label": "拼车主管（总管）",
            "subadmin_label": "对接员",
            "archive_key": "trip_route",
            "archive_label": "行程",
            "archive_plural": "行程",
            "archive_fields": [
                {"key": "title", "label": "行程标题", "type": "string"},
                {"key": "author", "label": "发布人", "type": "string"},
                {"key": "startAt", "label": "出发时间", "type": "datetime"},
                {"key": "isbn", "label": "地点备注", "type": "string"},
                {"key": "category", "label": "分类", "type": "select"},
                {"key": "stock", "label": "余座", "type": "number"},
                {"key": "ownerUsername", "label": "确认账号", "type": "string"},
            ],
            "stock_display": "number",
            "ticket_key": "carpool_intent",
            "ticket_label": "同行意向",
            "ticket_plural": "同行意向",
            "verbs": {
                "apply": "提交意向",
                "approve": "调剂确认",
                "reject": "调剂驳回",
                "return": "完结",
                "remind": "催确认",
            },
            "states": {
                "pending": "待对方确认",
                "approved": "已对接",
                "rejected": "已婉拒",
                "returned": "已完结",
            },
            "archive_menu_admin": "行程档案",
            "archive_menu_user": "行程目录",
            "auth_eyebrow": "拼车结伴",
            "auth_lead": "验证码登录；发布行程（出发时间）或提交同行意向，由车主确认或婉拒；过出发自动下架（无地图）。",
            "auth_points": ["验证码登录", "行程发布", "意向对接与车主确认"],
            "register_hint": "注册后可发布行程并提交同行意向",
            "notice_title": "拼车须知",
            "notice_body": "请填写出发时间与地点备注；确认后占用余座；过出发时间自动下架不可对接。本期无地图导航与真支付分账。",
            "notice_page_title": "拼车公告",
            "notice_page_lead": "出行须知与临时通知，点击条目阅读全文。",
            "my_tickets_label": "我的意向",
            "pending_label": "调剂确认",
            "records_label": "意向记录",
            "remark_label": "同行说明",
            "peer_inbox_label": "待我确认",
            "peer_inbox_lead": "他人向你发起的同行意向，确认后即对接成功；也可婉拒。管理端可调剂。",
            "peer_inbox_empty": "暂无待确认意向",
            "messages_page_lead": "意向确认、调剂结果与系统通知。",
            "peer_reject_dialog_title": "婉拒意向",
            "peer_confirm_dialog_title": "确认对接",
            "peer_confirm_dialog_message": "确认接受该同行意向？",
            "auto_approve": False,
            "approve_ends_flow": True,
            "peer_accept": True,
            "user_publish": True,
            "contact_channel_label": "对接方式",
            "contact_channel_options": ["站内留言", "电话联系", "线下碰面", "其他"],
            "contact_channel_placeholder": "选择对接方式",
            "next_follow_label": "期望出行日",
            "banners": [
                {"title": "行程目录", "lead": "浏览可对接行程。"},
                {"title": "发布行程", "lead": "填写出发时间与地点，即时可见；过点自动下架。"},
                {"title": "提交意向", "lead": "填写说明提交同行意向，等待车主确认。"},
                {"title": "待我确认", "lead": "他人向你发起的意向在此确认或婉拒。"},
                {"title": "我的意向", "lead": "跟踪对接进度。"},
            ],
        },
    }
