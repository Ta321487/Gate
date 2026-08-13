"""Schema 壳构造器：档案单 / 订单 / 预约 / 独立工单 / 收藏 / GENERIC。

各域 builder 见 domain_builders；登记表见 templates.SCHEMA_BUILDERS。
"""

from __future__ import annotations

import re
from typing import Any

from app.bake.domains import DOMAIN_CAPABILITIES

def product_name_from_title(title: str) -> str:
    """开题长标题 → 登录/导航用的短产品名。"""
    t = (title or "").strip()
    if not t:
        return "业务系统"
    m = re.search(r"的(.+?)(?:的设计与实现|系统设计|的实现|的设计)\s*$", t)
    if m:
        name = m.group(1).strip()
        if 4 <= len(name) <= 32:
            return name
    m = re.search(r"基于.+?的(.+)$", t)
    if m:
        name = re.sub(r"(的设计与实现|系统设计|的实现|的设计)\s*$", "", m.group(1)).strip()
        if 4 <= len(name) <= 32:
            return name
    if len(t) > 28:
        return t[:28].rstrip("的与及")
    return t


def _copy_scan_text(title: str, proposal_text: str = "") -> str:
    """壳文案场景分支用：题名 + 开题正文（真源见 scene_scan）。"""
    from app.bake.scene_scan import copy_scan_text

    return copy_scan_text(title, proposal_text)


# 题名/开题双扫的壳构建器（其余 builder 仍只收 title）
_SCENE_COPY_DOMAINS = frozenset({
    "DOM-ATTEND",
    "DOM-FOOD",
    "DOM-SHOP",
    "DOM-MEETING",
    "DOM-RECRUIT",
    "DOM-DATING",
    "DOM-EVENT",
    "DOM-ASSET",
    "DOM-PARKING",
    "DOM-PARCEL",
    "DOM-SALON",
    "DOM-HOSPITAL",
    "DOM-LOST",
    "DOM-ACTIVITY",
    "DOM-CRM",
    "DOM-EQUIP",
    "DOM-IT",
    "DOM-FUND",
    "DOM-GRADE",
    "DOM-INTERN",
    "DOM-LABSAFE",
    "DOM-PROPERTY",
    "DOM-MEDIA",
    "DOM-MUSIC",
    "DOM-BLOG",
    "DOM-FORUM",
    "DOM-EXAM",
})

from app.bake.scene_scan import (  # noqa: E402
    CAMPUS_HINTS as _CAMPUS_HINTS,
    COMMUNITY_HINTS as _COMMUNITY_HINTS,
    scan_has as _scan_has,
)


def category_menu_label(
    archive_fields: list[dict[str, Any]] | None,
    *,
    override: str | None = None,
) -> str:
    """分类菜单文案：跟 archive.fields 里 category 的 label（科室→科室管理）。"""
    if (override or "").strip():
        noun = override.strip()
    else:
        cat = next(
            (
                f
                for f in (archive_fields or [])
                if isinstance(f, dict) and f.get("key") == "category"
            ),
            None,
        )
        noun = str((cat or {}).get("label") or "分类").strip() or "分类"
    if noun.endswith("管理"):
        return noun
    return f"{noun}管理"



def archive_ticket_schema(
    title: str,
    *,
    domain: str,
    user_role_id: str,
    user_label: str,
    admin_label: str,
    subadmin_label: str,
    archive_key: str,
    archive_label: str,
    archive_plural: str,
    archive_fields: list[dict[str, Any]],
    ticket_key: str,
    ticket_label: str,
    ticket_plural: str,
    verbs: dict[str, str],
    states: dict[str, str],
    archive_menu_admin: str,
    archive_menu_user: str,
    users_menu: str,
    auth_eyebrow: str,
    auth_lead: str,
    auth_points: list[str],
    register_hint: str,
    notice_title: str,
    notice_body: str,
    notice_page_title: str = "公告",
    notice_page_lead: str = "通知与须知，点击条目阅读全文。",
    messages_page_lead: str | None = None,
    my_tickets_label: str = "我的借用",
    pending_label: str = "借用审核",
    records_label: str = "借用记录",
    deadline_label: str = "逾期催还",
    with_deadline: bool = True,
    play_url_field: str = "",
    body_field: str = "",
    stock_display: str = "count",
    rich_remark: bool = False,
    two_level_approve: bool = False,
    require_attach: bool = False,
    allow_rating: bool = False,
    # C-06：多维评分 [{key,label},...]；空则单分。allow_anonymous_rating 演示匿名。
    rating_dims: list[dict[str, str]] | None = None,
    allow_anonymous_rating: bool = False,
    check_mutex: bool = False,
    category_limit: int = 0,
    soft_delete: bool = False,
    tag_filter: bool = False,
    # True：门户用户可发帖（主帖入库即时可见；站长可下架）
    user_publish: bool = False,
    week_calendar: bool = False,
    week_calendar_label: str = "我的日程",
    allow_checkin: bool = False,
    # C-05：档案主人确认志愿（互选）；管理端仍可调剂审批
    peer_accept: bool = False,
    peer_inbox_label: str | None = None,
    # 拼车等非互选域可覆盖「志愿」默认铅字
    peer_inbox_lead: str | None = None,
    peer_inbox_empty: str | None = None,
    peer_reject_dialog_title: str | None = None,
    peer_confirm_dialog_title: str | None = None,
    peer_confirm_dialog_message: str | None = None,
    # C-09：审核通过签发通行码（字符串，非真门禁）
    issue_pass_code: bool = False,
    pass_code_label: str | None = None,
    no_show_after_end: bool = False,
    no_show_penalty_yuan: float = 0,
    pick_loan_period: bool | None = None,
    allow_qty: bool | None = None,
    require_remark: bool = False,
    remark_label: str = "说明",
    pick_date_range: bool = False,
    due_label: str | None = None,
    fine_label: str | None = None,
    fine_paid_label: str | None = None,
    checkin_label: str | None = None,
    recommend_latest_hint: str | None = None,
    # CRM/EVENT：跟进/上报渠道文案（与 remark_label 同挂 ticket 实体）
    contact_channel_label: str | None = None,
    contact_channel_options: list[str] | None = None,
    contact_channel_placeholder: str | None = None,
    next_follow_label: str | None = None,
    # True：审核通过/驳回即为收口（报名/选课/认领/收藏等）；工作台「已完成」含 approved+rejected
    approve_ends_flow: bool = False,
    # True：提交即生效（媒资/博客收藏等个人动作），不进管理端待审队列
    auto_approve: bool = False,
    # True：申请说明/取件码须与档案 isbn（取件码）一致（驿站）
    require_claim_code: bool = False,
    # True：用户在「我的单据」填单选档案项提交（请假/OA 填单感）；仍保留档案浏览作说明
    apply_from_list: bool = False,
    # True：用户菜单「我的单据」排在档案目录前
    user_tickets_first: bool = False,
    my_tickets_page_lead: str | None = None,
    my_tickets_empty: str | None = None,
) -> dict[str, Any]:
    """借用/收藏/回复薄壳：档案主数据 + 单据流（组 A / G）。"""
    app = product_name_from_title(title)
    if pick_loan_period is None:
        pick_loan_period = with_deadline
    if allow_qty is None:
        allow_qty = with_deadline
    archive_entity: dict[str, Any] = {
        "key": archive_key,
        "label": archive_label,
        "labelPlural": archive_plural,
        "fields": archive_fields,
        "stockDisplay": stock_display,
        "softDelete": soft_delete,
        "tagFilter": tag_filter,
    }
    if user_publish:
        archive_entity["userPublish"] = True
    if play_url_field:
        archive_entity["playUrlField"] = play_url_field
    if body_field:
        archive_entity["bodyField"] = body_field
    if stock_display in ("available", "toggle"):
        from app.bake.ticket_copy_text import stock_unavailable_label

        stock_lab = "可认领"
        for f in archive_fields:
            if isinstance(f, dict) and f.get("key") == "stock":
                lab = str(f.get("label") or "").strip()
                if lab:
                    stock_lab = lab
                break
        archive_entity["stockUnavailableLabel"] = stock_unavailable_label(stock_lab)
    states_out = dict(states)
    if two_level_approve and "pending_final" not in states_out:
        # 插在 pending 后
        ordered: dict[str, str] = {}
        for k, v in states_out.items():
            ordered[k] = v
            if k == "pending":
                ordered["pending_final"] = "待终审"
        states_out = ordered
    remind = verbs.get("remind") or "提醒"
    if due_label is None and pick_loan_period:
        due_label = "应还日" if remind == "催还" else "到期日"
    if fine_label is None and with_deadline:
        fine_label = "罚款" if remind == "催还" else "逾期费用"
    if fine_paid_label is None and with_deadline:
        fine_paid_label = "罚款已缴" if remind == "催还" else "费用已结清"
    if checkin_label is None and allow_checkin:
        checkin_label = "签到"
    if no_show_after_end and allow_checkin:
        if no_show_penalty_yuan and float(no_show_penalty_yuan) > 0:
            if fine_label is None:
                fine_label = "爽约费用"
            if fine_paid_label is None:
                fine_paid_label = "爽约费用已缴"
        if "overdue" not in states_out:
            states_out["overdue"] = "爽约"
        elif states_out.get("overdue") in ("已失效", "逾期", "已逾期"):
            states_out["overdue"] = "爽约"
    ticket_entity: dict[str, Any] = {
        "key": ticket_key,
        "label": ticket_label,
        "labelPlural": ticket_plural,
        "verbs": verbs,
        "states": states_out,
        "twoLevelApprove": two_level_approve,
        "requireAttach": require_attach,
        "allowRating": allow_rating,
        "checkMutex": check_mutex,
        "categoryLimit": max(0, int(category_limit or 0)),
        "weekCalendar": week_calendar,
        "allowCheckin": allow_checkin,
        "peerAccept": bool(peer_accept),
        "issuePassCode": bool(issue_pass_code),
        "noShowAfterEnd": bool(no_show_after_end and allow_checkin),
        "noShowPenaltyYuan": float(no_show_penalty_yuan or 0) if (no_show_after_end and allow_checkin) else 0,
        "pickLoanPeriod": bool(pick_loan_period),
        "allowQty": bool(allow_qty),
        "requireRemark": bool(require_remark),
        "remarkLabel": remark_label or "说明",
        "pickDateRange": bool(pick_date_range),
        "approveEndsFlow": bool(approve_ends_flow),
        "autoApprove": bool(auto_approve),
        "requireClaimCode": bool(require_claim_code),
        "applyFromList": bool(apply_from_list),
    }
    dims = [d for d in (rating_dims or []) if isinstance(d, dict) and d.get("key") and d.get("label")]
    if dims and allow_rating:
        ticket_entity["ratingDims"] = [
            {"key": str(d["key"]).strip(), "label": str(d["label"]).strip()} for d in dims
        ]
        ticket_entity["allowAnonymousRating"] = bool(allow_anonymous_rating)
    if due_label:
        ticket_entity["dueLabel"] = due_label
    if fine_label:
        ticket_entity["fineLabel"] = fine_label
    if fine_paid_label:
        ticket_entity["finePaidLabel"] = fine_paid_label
    if checkin_label:
        ticket_entity["checkinLabel"] = checkin_label
    if issue_pass_code:
        ticket_entity["passCodeLabel"] = (pass_code_label or "").strip() or "通行码"
    if week_calendar:
        ticket_entity["weekCalendarLabel"] = week_calendar_label
    if rich_remark:
        ticket_entity["richRemark"] = True
    if contact_channel_label:
        ticket_entity["contactChannelLabel"] = contact_channel_label
    if contact_channel_options:
        ticket_entity["contactChannelOptions"] = list(contact_channel_options)
    if contact_channel_placeholder:
        ticket_entity["contactChannelPlaceholder"] = contact_channel_placeholder
    if next_follow_label:
        ticket_entity["nextFollowLabel"] = next_follow_label
    admin_menus = [
        {"key": "dashboard", "label": "工作台"},
        {"key": "archive", "label": archive_menu_admin, "superOnly": True},
        {"key": "category", "label": category_menu_label(archive_fields), "superOnly": True},
        {"key": "users", "label": users_menu, "superOnly": True},
    ]
    if not auto_approve:
        admin_menus.append({"key": "ticket_pending", "label": pending_label})
    admin_menus.append({"key": "ticket_records", "label": records_label})
    if with_deadline:
        admin_menus.append({"key": "deadline", "label": deadline_label})
    admin_menus.append({"key": "content", "label": "公告管理", "superOnly": True})
    if user_tickets_first:
        user_menus = [
            {"key": "my_tickets", "label": my_tickets_label},
            {"key": "archive", "label": archive_menu_user},
        ]
    else:
        user_menus = [
            {"key": "archive", "label": archive_menu_user},
            {"key": "my_tickets", "label": my_tickets_label},
        ]
    if peer_accept:
        user_menus.append(
            {"key": "peer_tickets", "label": (peer_inbox_label or "").strip() or "待我确认"}
        )
    if user_publish:
        user_menus.insert(1, {"key": "my_archive", "label": f"我的{archive_label}"})
    if week_calendar:
        user_menus.append({"key": "week_calendar", "label": week_calendar_label})
    user_menus.extend(
        [
            {"key": "content", "label": "公告"},
            {"key": "profile", "label": "个人资料"},
        ]
    )
    if messages_page_lead is None:
        if auto_approve:
            messages_page_lead = "系统通知。"
        elif peer_accept:
            messages_page_lead = "志愿确认、调剂结果与系统通知。"
        elif with_deadline:
            messages_page_lead = f"审核结果、{remind}提醒与系统通知。"
        elif allow_checkin:
            messages_page_lead = "审核结果、活动提醒与系统通知。"
        else:
            messages_page_lead = "审核结果与系统通知。"
    if recommend_latest_hint is None:
        recommend_latest_hint = "最新上架" if soft_delete and stock_display == "count" else "最新发布"
    caps = list(DOMAIN_CAPABILITIES[domain])
    labels: dict[str, Any] = {
        "appName": app,
        "authEyebrow": auth_eyebrow,
        "authLead": auth_lead,
        "authPoints": auth_points,
        "registerRoleHint": register_hint,
        "noticePageTitle": notice_page_title,
        "noticePageLead": notice_page_lead,
        "messagesPageLead": messages_page_lead,
    }
    if "recommend" in caps:
        labels["recommendSectionTitle"] = "猜你喜欢"
        labels["recommendLatestHint"] = recommend_latest_hint
    if user_publish:
        labels["myArchivePageTitle"] = f"我的{archive_label}"
        labels["myArchivePageLead"] = (
            f"本人发布的{archive_label}即时可见；站长下架后仍可在此查看状态。"
        )
    if peer_accept:
        labels["peerInboxTitle"] = (peer_inbox_label or "").strip() or "待我确认"
        labels["peerInboxLead"] = (peer_inbox_lead or "").strip() or (
            "他人向你发起的志愿，确认后即互选成功；也可婉拒。管理端可调剂。"
        )
        labels["peerInboxEmpty"] = (peer_inbox_empty or "").strip() or "暂无待确认志愿"
        labels["peerRejectDialogTitle"] = (peer_reject_dialog_title or "").strip() or "婉拒志愿"
        labels["peerConfirmDialogTitle"] = (peer_confirm_dialog_title or "").strip() or "确认互选"
        labels["peerConfirmDialogMessage"] = (peer_confirm_dialog_message or "").strip() or (
            "确认接受该志愿？"
        )
    if apply_from_list:
        labels["myTicketsPageLead"] = (my_tickets_page_lead or "").strip() or (
            f"在此{verbs.get('apply') or '提交'}并跟踪进度；档案页仅作说明查阅。"
        )
        labels["myTicketsEmpty"] = (my_tickets_empty or "").strip() or (
            f"还没有记录，点击右上角{verbs.get('apply') or '提交'}。"
        )
        labels["userHomePath"] = "/tickets"
    else:
        if my_tickets_page_lead:
            labels["myTicketsPageLead"] = my_tickets_page_lead.strip()
        if my_tickets_empty:
            labels["myTicketsEmpty"] = my_tickets_empty.strip()
    return {
        "version": 1,
        "title": title,
        "capabilities": caps,
        "roles": {
            "user": {"id": user_role_id, "label": user_label},
            "admin": {"id": "admin", "label": admin_label},
            "subadmin": {"id": "subadmin", "label": subadmin_label},
        },
        "entities": {
            "archive": archive_entity,
            "ticket": ticket_entity,
        },
        "menus": {
            "admin": admin_menus,
            "user": user_menus,
        },
        "labels": labels,
        "seeds": {
            "noticeTitle": notice_title,
            "noticeBody": notice_body,
        },
    }


def _with_portal_banners(schema: dict[str, Any], banners: list[dict[str, str]]) -> dict[str, Any]:
    out = dict(schema)
    out["portalBanners"] = banners
    return out



def archive_favorites_schema(
    title: str,
    *,
    domain: str,
    user_role_id: str,
    user_label: str,
    admin_label: str,
    subadmin_label: str,
    archive_key: str,
    archive_label: str,
    archive_plural: str,
    archive_fields: list[dict[str, Any]],
    archive_menu_admin: str,
    archive_menu_user: str,
    users_menu: str,
    auth_eyebrow: str,
    auth_lead: str,
    auth_points: list[str],
    register_hint: str,
    notice_title: str,
    notice_body: str,
    notice_page_title: str = "公告",
    notice_page_lead: str = "通知与须知，点击条目阅读全文。",
    favorites_page_lead: str = "收藏感兴趣的内容，方便随时回看。",
    play_url_field: str = "",
    body_field: str = "",
    stock_display: str = "toggle",
    soft_delete: bool = True,
    tag_filter: bool = False,
    recommend_latest_hint: str | None = None,
) -> dict[str, Any]:
    """内容流薄壳：档案浏览 + 即时收藏（无单据/审核）。"""
    from app.bake.features.favorites import attach_favorites_menus

    app = product_name_from_title(title)
    archive_entity: dict[str, Any] = {
        "key": archive_key,
        "label": archive_label,
        "labelPlural": archive_plural,
        "fields": archive_fields,
        "stockDisplay": stock_display,
        "softDelete": soft_delete,
        "tagFilter": tag_filter,
    }
    if play_url_field:
        archive_entity["playUrlField"] = play_url_field
    if body_field:
        archive_entity["bodyField"] = body_field
    if stock_display in ("available", "toggle"):
        from app.bake.ticket_copy_text import stock_unavailable_label

        stock_lab = "可点播"
        for f in archive_fields:
            if isinstance(f, dict) and f.get("key") == "stock":
                lab = str(f.get("label") or "").strip()
                if lab:
                    stock_lab = lab
                break
        archive_entity["stockUnavailableLabel"] = stock_unavailable_label(stock_lab)
    if recommend_latest_hint is None:
        recommend_latest_hint = "最新上架" if soft_delete else "最新发布"
    caps = list(DOMAIN_CAPABILITIES[domain])
    fav_labels: dict[str, Any] = {
            "appName": app,
            "authEyebrow": auth_eyebrow,
            "authLead": auth_lead,
            "authPoints": auth_points,
            "registerRoleHint": register_hint,
            "noticePageTitle": notice_page_title,
            "noticePageLead": notice_page_lead,
            "messagesPageLead": "系统通知。",
    }
    if "recommend" in caps:
        fav_labels["recommendSectionTitle"] = "猜你喜欢"
        fav_labels["recommendLatestHint"] = recommend_latest_hint
    schema: dict[str, Any] = {
        "version": 1,
        "title": title,
        "capabilities": caps,
        "roles": {
            "user": {"id": user_role_id, "label": user_label},
            "admin": {"id": "admin", "label": admin_label},
            "subadmin": {"id": "subadmin", "label": subadmin_label},
        },
        "entities": {
            "archive": archive_entity,
        },
        "menus": {
            "admin": [
                {"key": "dashboard", "label": "工作台"},
                {"key": "archive", "label": archive_menu_admin, "superOnly": True},
                {"key": "category", "label": category_menu_label(archive_fields), "superOnly": True},
                {"key": "users", "label": users_menu, "superOnly": True},
                {"key": "content", "label": "公告管理", "superOnly": True},
            ],
            "user": [
                {"key": "archive", "label": archive_menu_user},
                {"key": "content", "label": "公告"},
                {"key": "profile", "label": "个人资料"},
            ],
        },
        "labels": fav_labels,
        "seeds": {
            "noticeTitle": notice_title,
            "noticeBody": notice_body,
        },
    }
    attach_favorites_menus(schema, page_lead=favorites_page_lead)
    return schema



def standalone_ticket_schema(
    title: str,
    *,
    domain: str,
    user_role_id: str,
    user_label: str,
    admin_label: str,
    subadmin_label: str,
    ticket_key: str,
    ticket_label: str,
    ticket_plural: str,
    verbs: dict[str, str],
    states: dict[str, str],
    site_menu: str,
    type_menu: str,
    users_menu: str,
    auth_eyebrow: str,
    auth_lead: str,
    auth_points: list[str],
    register_hint: str,
    notice_title: str,
    notice_body: str,
    notice_page_title: str = "公告",
    notice_page_lead: str = "通知与须知，点击条目阅读全文。",
    my_tickets_label: str = "我的报修",
    pending_label: str = "报修受理",
    records_label: str = "报修记录",
    two_level_approve: bool = False,
    require_attach: bool = False,
    allow_rating: bool = False,
) -> dict[str, Any]:
    """报修/工单薄壳：主数据 + 用户 + 公告（总管）与单据流（子管）。"""
    app = product_name_from_title(title)
    states_out = dict(states)
    if two_level_approve and "pending_final" not in states_out:
        # 只插入待终审；保留 builder 的「待受理」等可见词（勿改成「待初审」穿帮开题）
        ordered: dict[str, str] = {}
        for k, v in states.items():
            ordered[k] = v
            if k == "pending":
                ordered["pending_final"] = "待终审"
        states_out = ordered
    return {
        "version": 1,
        "title": title,
        "capabilities": list(DOMAIN_CAPABILITIES[domain]),
        "roles": {
            "user": {"id": user_role_id, "label": user_label},
            "admin": {"id": "admin", "label": admin_label},
            "subadmin": {"id": "subadmin", "label": subadmin_label},
        },
        "entities": {
            "ticket": {
                "key": ticket_key,
                "label": ticket_label,
                "labelPlural": ticket_plural,
                "verbs": verbs,
                "states": states_out,
                "twoLevelApprove": two_level_approve,
                "requireAttach": require_attach,
                "allowRating": allow_rating,
                "applicantCompleteOnly": True,
            },
        },
        "menus": {
            "admin": [
                {"key": "dashboard", "label": "工作台"},
                {"key": "ticket_pending", "label": pending_label},
                {"key": "ticket_records", "label": records_label},
                {"key": "lookup_site", "label": site_menu, "superOnly": True},
                {"key": "lookup_type", "label": type_menu, "superOnly": True},
                {"key": "users", "label": users_menu, "superOnly": True},
                {"key": "content", "label": "公告管理", "superOnly": True},
            ],
            # deadline 菜单由 core_cap_scan 在扫到 SLA/逾期词后插入
            "user": [
                {"key": "my_tickets", "label": my_tickets_label},
                {"key": "content", "label": "公告"},
                {"key": "profile", "label": "个人资料"},
            ],
        },
        "labels": {
            "appName": app,
            "authEyebrow": auth_eyebrow,
            "authLead": auth_lead,
            "authPoints": auth_points,
            "registerRoleHint": register_hint,
            "noticePageTitle": notice_page_title,
            "noticePageLead": notice_page_lead,
            "messagesPageLead": "审核结果与系统通知。",
            "recommendLatestHint": "最新发布",
        },
        "seeds": {
            "noticeTitle": notice_title,
            "noticeBody": notice_body,
        },
    }



def generic_schema(title: str, domain: str) -> dict[str, Any]:
    caps = list(DOMAIN_CAPABILITIES.get(domain, DOMAIN_CAPABILITIES["DOM-GENERIC"]))
    return {
        "version": 1,
        "title": title,
        "capabilities": caps,
        "roles": {
            "user": {"id": "user", "label": "用户"},
            "admin": {"id": "admin", "label": "管理员"},
            "subadmin": {"id": "subadmin", "label": "经办员"},
        },
        "entities": {
            "archive": {
                "key": "item",
                "label": "业务对象",
                "labelPlural": "业务对象",
                "fields": [
                    {"key": "name", "label": "名称", "type": "string"},
                    {"key": "remark", "label": "备注", "type": "string"},
                ],
            },
        },
        "menus": {
            "admin": [
                {"key": "dashboard", "label": "工作台"},
                {"key": "archive", "label": "信息管理", "superOnly": True},
                {"key": "users", "label": "用户管理", "superOnly": True},
                {"key": "content", "label": "公告管理", "superOnly": True},
            ],
            "user": [
                {"key": "archive", "label": "浏览"},
                {"key": "content", "label": "公告"},
                {"key": "profile", "label": "个人资料"},
            ],
        },
        "labels": {
            "appName": product_name_from_title(title),
            "authEyebrow": "欢迎使用",
            "authLead": "验证码登录，开放注册；登录后可使用系统基础能力。",
            "authPoints": ["验证码登录", "开放注册", "个人资料与头像"],
            "registerRoleHint": "注册后即可使用系统",
            "noticePageTitle": "系统公告",
            "noticePageLead": "通知与须知，点击条目阅读全文。",
            "messagesPageLead": "审核结果与系统通知。",
            "recommendLatestHint": "最新发布",
        },
        "seeds": {
            "noticeTitle": "系统公告",
            "noticeBody": "系统已就绪。",
        },
    }


def order_shell_schema(
    title: str,
    *,
    domain: str,
    user_role_id: str,
    user_label: str,
    admin_label: str,
    subadmin_label: str,
    archive_key: str,
    archive_label: str,
    archive_plural: str,
    archive_fields: list[dict[str, Any]],
    archive_menu_admin: str,
    archive_menu_user: str,
    users_menu: str,
    cart_label: str,
    my_orders_label: str,
    orders_admin_label: str,
    auth_eyebrow: str,
    auth_lead: str,
    auth_points: list[str],
    register_hint: str,
    notice_title: str,
    notice_body: str,
    notice_page_title: str,
    order_states: dict[str, str] | None = None,
) -> dict[str, Any]:
    app = product_name_from_title(title)
    states = order_states or {
        "pending": "待确认",
        "confirmed": "已确认",
        "shipped": "配送中",
        "completed": "已完成",
        "cancelled": "已取消",
    }
    return {
        "version": 1,
        "title": title,
        "capabilities": list(DOMAIN_CAPABILITIES[domain]),
        "roles": {
            "user": {"id": user_role_id, "label": user_label},
            "admin": {"id": "admin", "label": admin_label},
            "subadmin": {"id": "subadmin", "label": subadmin_label},
        },
        "entities": {
            "archive": {
                "key": archive_key,
                "label": archive_label,
                "labelPlural": archive_plural,
                "fields": archive_fields,
                "stockDisplay": "count",
            },
            "order": {
                "key": "order",
                "label": "订单",
                "labelPlural": my_orders_label,
                "states": states,
            },
        },
        "menus": {
            "admin": [
                {"key": "dashboard", "label": "工作台"},
                {"key": "archive", "label": archive_menu_admin, "superOnly": True},
                {"key": "category", "label": category_menu_label(archive_fields), "superOnly": True},
                {"key": "users", "label": users_menu, "superOnly": True},
                {"key": "orders", "label": orders_admin_label},
                {"key": "guestbook", "label": "留言管理", "superOnly": True},
                {"key": "content", "label": "公告管理", "superOnly": True},
            ],
            "user": [
                {"key": "archive", "label": archive_menu_user},
                {"key": "cart", "label": cart_label},
                {"key": "my_orders", "label": my_orders_label},
                {"key": "addresses", "label": "收货地址"},
                {"key": "guestbook", "label": "留言"},
                {"key": "content", "label": "公告"},
                {"key": "profile", "label": "个人资料"},
            ],
        },
        "labels": {
            "appName": app,
            "authEyebrow": auth_eyebrow,
            "authLead": auth_lead,
            "authPoints": auth_points,
            "registerRoleHint": register_hint,
            "noticePageTitle": notice_page_title,
            "noticePageLead": "通知与须知，点击条目阅读全文。",
            "guestbookPageTitle": "留言板",
            "guestbookPageLead": "欢迎留下建议或咨询；管理员可简短回复。",
            "messagesPageLead": "订单进度与系统通知。",
            "recommendLatestHint": "最新上架",
        },
        "seeds": {"noticeTitle": notice_title, "noticeBody": notice_body},
    }


def slot_shell_schema(
    title: str,
    *,
    domain: str,
    user_role_id: str,
    user_label: str,
    admin_label: str,
    subadmin_label: str,
    archive_key: str,
    archive_label: str,
    archive_plural: str,
    archive_fields: list[dict[str, Any]],
    archive_menu_admin: str,
    archive_menu_user: str,
    users_menu: str,
    my_resv_label: str,
    resv_admin_label: str,
    auth_eyebrow: str,
    auth_lead: str,
    auth_points: list[str],
    register_hint: str,
    notice_title: str,
    notice_body: str,
    notice_page_title: str,
    with_orders: bool = False,
    reserve_require_remark: bool = False,
    reserve_remark_label: str = "备注",
    # 动作名词（取消/确认用）；勿带「记录」——记录仅给管理端列表菜单
    resv_label: str = "预约",
    category_menu: str | None = None,
    # 履约办结：confirmed → completed（入场/就诊/到店/入住离店）
    complete_verb: str = "办结",
    completed_label: str | None = None,
) -> dict[str, Any]:
    app = product_name_from_title(title)
    noun = (resv_label or "预约").removesuffix("记录").strip() or "预约"
    done_lab = completed_label or f"已{complete_verb}"
    cat_menu_label = category_menu_label(archive_fields, override=category_menu)
    admin_menus = [
        {"key": "dashboard", "label": "工作台"},
        {"key": "archive", "label": archive_menu_admin, "superOnly": True},
        {"key": "category", "label": cat_menu_label, "superOnly": True},
        {"key": "users", "label": users_menu, "superOnly": True},
        {"key": "reservations", "label": resv_admin_label},
    ]
    user_menus = [
        {"key": "archive", "label": archive_menu_user},
        {"key": "my_reservations", "label": my_resv_label},
        {"key": "content", "label": "公告"},
        {"key": "profile", "label": "个人资料"},
    ]
    reservation_entity: dict[str, Any] = {
        "key": "reservation",
        "label": noun,
        "labelPlural": my_resv_label,
        "states": {
            "pending": "待确认",
            "confirmed": f"已{noun}",
            "completed": done_lab,
            "cancelled": "已取消",
        },
        "completeVerb": complete_verb or "办结",
        "requireRemark": bool(reserve_require_remark),
        "remarkLabel": reserve_remark_label or "备注",
        "requireConfirm": False,
    }
    entities: dict[str, Any] = {
        "archive": {
            "key": archive_key,
            "label": archive_label,
            "labelPlural": archive_plural,
            "fields": archive_fields,
            "stockDisplay": "hidden",
        },
        "reservation": reservation_entity,
    }
    if with_orders:
        admin_menus.append({"key": "orders", "label": "预订订单"})
        user_menus.insert(2, {"key": "my_orders", "label": "我的订单"})
        # 收货地址簿仅订餐/商城订单壳；酒店预约订单不挂
        entities["order"] = {
            "key": "order",
            "label": "订单",
            "labelPlural": "我的订单",
            "states": {
                "pending": "待确认",
                "confirmed": "已确认",
                "shipped": "履约中",
                "completed": "已完成",
                "cancelled": "已取消",
            },
        }
    admin_menus.append({"key": "content", "label": "公告管理", "superOnly": True})
    return {
        "version": 1,
        "title": title,
        "capabilities": list(DOMAIN_CAPABILITIES[domain]),
        "roles": {
            "user": {"id": user_role_id, "label": user_label},
            "admin": {"id": "admin", "label": admin_label},
            "subadmin": {"id": "subadmin", "label": subadmin_label},
        },
        "entities": entities,
        "menus": {"admin": admin_menus, "user": user_menus},
        "labels": {
            "appName": app,
            "authEyebrow": auth_eyebrow,
            "authLead": auth_lead,
            "authPoints": auth_points,
            "registerRoleHint": register_hint,
            "noticePageTitle": notice_page_title,
            "noticePageLead": "通知与须知，点击条目阅读全文。",
            "messagesPageLead": "预约提醒与系统通知。",
            "recommendLatestHint": "最新发布",
        },
        "seeds": {"noticeTitle": notice_title, "noticeBody": notice_body},
    }


