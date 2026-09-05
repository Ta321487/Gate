"""旅行社线路报名 FOLLOWUP_PRESETS（P-31 · DOM-TOUR）。"""

from __future__ import annotations

from typing import Any, Callable


def build_tour_followup_presets(
    _std_archive_fields: Callable[..., list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    return {
        "DOM-TOUR": {
            "doc": "旅行社线路：线路档案 + 报名占名额。",
            "user_label": "游客",
            "admin_label": "计调主管（总管）",
            "subadmin_label": "计调员",
            "archive_key": "tour_line",
            "archive_label": "线路",
            "archive_plural": "线路",
            "archive_fields": _std_archive_fields(
                "线路名称",
                "计调/发布人",
                "行程亮点与说明",
                "线路状态",
                ["开放报名", "满员", "已出团", "下架"],
                "线路类型",
                "余位",
            )
            + [
                {
                    "key": "applyDeadlineAt",
                    "label": "报名截止",
                    "type": "datetime",
                    "timeStepMinutes": 30,
                },
            ],
            "stock_display": "number",
            "ticket_key": "tour_signup",
            "ticket_label": "线路报名",
            "ticket_plural": "线路报名",
            "verbs": {
                "apply": "提交报名",
                "approve": "确认报名",
                "reject": "驳回",
                "return": "取消报名",
                "remind": "催办",
            },
            "states": {
                "pending": "待审核",
                "approved": "已确认",
                "rejected": "已驳回",
                "returned": "已取消",
            },
            "archive_menu_admin": "线路档案",
            "archive_menu_user": "线路目录",
            "auth_eyebrow": "旅行社线路",
            "auth_lead": "验证码登录；浏览线路并提交报名，计调审核确认后占余位；过截止、满员、已出团或下架不可再报。",
            "auth_points": ["验证码登录", "线路浏览", "报名审核"],
            "register_hint": "注册后可提交线路报名",
            "notice_title": "报名须知",
            "notice_body": "请如实填写出行人数与联系方式；余位有限，过报名截止将无法提交；取消报名将回补余位；线路「已出团/下架」由计调在档案标注。",
            "notice_page_title": "旅行社公告",
            "notice_page_lead": "出团须知与临时通知，点击条目阅读全文。",
            "my_tickets_label": "我的报名",
            "pending_label": "待审核报名",
            "records_label": "报名记录",
            "remark_label": "报名说明",
            "auto_approve": False,
            "approve_ends_flow": True,
            "contact_channel_label": "联系方式偏好",
            "contact_channel_options": ["手机电话", "微信", "站内留言", "其他"],
            "contact_channel_placeholder": "选择联系方式",
            "next_follow_label": "期望出行日",
            "banners": [
                {"title": "线路目录", "lead": "浏览可报名线路与余位。"},
                {"title": "提交报名", "lead": "填写人数与说明提交报名。"},
                {"title": "旅行社公告", "lead": "出团须知见公告栏。"},
                {"title": "我的报名", "lead": "跟踪审核；通过后可取消报名回补余位。"},
                {"title": "分类检索", "lead": "按线路类型筛选。"},
            ],
        },
    }
