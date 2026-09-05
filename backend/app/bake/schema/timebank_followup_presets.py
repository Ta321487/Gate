"""时间银行 FOLLOWUP_PRESETS（C-14）。"""

from __future__ import annotations

from typing import Any, Callable


def build_timebank_followup_presets(
    _std_archive_fields: Callable[..., list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    from app.bake.schema.form_first_entry import apply_form_first_entry

    out = {
        "DOM-TIMEBANK": {
            "doc": "时间银行：服务事项 + 时长账户 + 核销申请。",
            "user_label": "志愿者",
            "admin_label": "时间银行主管（总管）",
            "subadmin_label": "核销员",
            "archive_key": "tb_service",
            "archive_label": "服务事项",
            "archive_plural": "服务事项",
            "archive_fields": _std_archive_fields(
                "事项名称",
                "组织方",
                "说明",
                "状态",
                ["开放", "暂停", "关闭"],
                "分类",
                "可参与",
            ),
            "stock_display": "toggle",
            "ticket_key": "tb_redeem",
            "ticket_label": "核销申请",
            "ticket_plural": "核销申请",
            "verbs": {
                "apply": "申请核销",
                "approve": "同意扣减",
                "reject": "驳回",
                "return": "完结",
                "remind": "催办",
            },
            "states": {
                "pending": "待审",
                "approved": "已核销",
                "rejected": "已驳回",
                "returned": "已完结",
            },
            "archive_menu_admin": "服务事项",
            "archive_menu_user": "服务说明",
            "auth_eyebrow": "时间银行",
            "auth_lead": (
                "验证码登录；在「我的核销」选择服务事项申请扣减，审核后从账户扣时长。"
            ),
            "auth_points": ["验证码登录", "时长账户", "核销申请"],
            "register_hint": "注册后可存入时长并申请核销",
            "notice_title": "时间银行须知",
            "notice_body": "存入即时入账；核销须审批且余额充足。",
            "notice_page_title": "时间银行公告",
            "notice_page_lead": "规则与临时通知，点击条目阅读全文。",
            "my_tickets_label": "我的核销",
            "pending_label": "待审核销",
            "records_label": "核销记录",
            "remark_label": "核销说明",
            "allow_qty": True,
            "auto_approve": False,
            "approve_ends_flow": True,
            "contact_channel_label": "核销用途",
            "contact_channel_options": ["兑换服务", "抵用志愿", "结对互助", "其他"],
            "contact_channel_placeholder": "选择用途",
            "next_follow_label": "期望办结日",
            "banners": [
                {"title": "申请核销", "lead": "在「我的核销」选事项填小时数，审核后扣减。"},
                {"title": "服务说明", "lead": "查阅可存入/核销的服务事项。"},
                {"title": "存入时长", "lead": "登记服务后即时入账。"},
                {"title": "我的时长", "lead": "查看余额与流水。"},
                {"title": "公告须知", "lead": "规则见公告栏。"},
            ],
        },
    }
    apply_form_first_entry(out["DOM-TIMEBANK"])
    return out
