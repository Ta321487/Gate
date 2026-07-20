"""各领域 Domain Schema 模板（文案/实体/菜单/种子）。"""

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


def _library_schema(title: str) -> dict[str, Any]:
    return {
        "version": 1,
        "title": title,
        "capabilities": list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
        "roles": {
            "user": {"id": "reader", "label": "读者"},
            "admin": {"id": "admin", "label": "馆长（总管）"},
            "subadmin": {"id": "subadmin", "label": "馆员"},
        },
        "entities": {
            "archive": {
                "key": "book",
                "label": "图书",
                "labelPlural": "图书",
                "fields": [
                    {"key": "title", "label": "书名", "type": "string"},
                    {"key": "author", "label": "作者", "type": "string"},
                    {"key": "isbn", "label": "ISBN", "type": "string"},
                    {"key": "publisher", "label": "出版社", "type": "string"},
                    {"key": "callNo", "label": "索书号", "type": "string"},
                    {"key": "category", "label": "分类", "type": "select"},
                    {"key": "stock", "label": "库存", "type": "number"},
                ],
                "softDelete": True,
            },
            "ticket": {
                "key": "borrow",
                "label": "借阅单",
                "labelPlural": "借阅",
                "verbs": {
                    "apply": "申请借阅",
                    "approve": "通过",
                    "reject": "驳回",
                    "return": "归还",
                    "remind": "催还",
                },
                "states": {
                    "pending": "待审核",
                    "approved": "借阅中",
                    "rejected": "已驳回",
                    "returned": "已归还",
                    "overdue": "已逾期",
                },
                "pickLoanPeriod": True,
                "allowQty": True,
                "dueLabel": "应还日",
                "fineLabel": "罚款",
                "finePaidLabel": "罚款已缴",
            },
        },
        "menus": {
            "admin": [
                {"key": "dashboard", "label": "工作台"},
                {"key": "archive", "label": "图书管理", "superOnly": True},
                {"key": "category", "label": "分类管理", "superOnly": True},
                {"key": "users", "label": "读者管理", "superOnly": True},
                {"key": "ticket_pending", "label": "借阅审核"},
                {"key": "ticket_records", "label": "借阅记录"},
                {"key": "deadline", "label": "逾期罚款"},
                {"key": "content", "label": "公告管理", "superOnly": True},
            ],
            "user": [
                {"key": "archive", "label": "图书检索"},
                {"key": "my_tickets", "label": "我的借阅"},
                {"key": "content", "label": "公告"},
                {"key": "profile", "label": "个人资料"},
            ],
        },
        "labels": {
            "appName": product_name_from_title(title),
            "authEyebrow": "欢迎使用",
            "authLead": "验证码登录，开放注册；读者可检索图书并申请借阅。",
            "authPoints": ["验证码登录", "开放注册", "借阅申请与归还"],
            "registerRoleHint": "注册后以读者身份使用系统",
            "noticePageTitle": "馆内公告",
            "noticePageLead": "开放时间、借阅须知与临时通知，点击条目阅读全文。",
            "messagesPageLead": "审核结果、还书提醒与系统通知。",
            "recommendSectionTitle": "猜你喜欢",
            "recommendLatestHint": "最新上架",
        },
        "seeds": {
            "noticeTitle": "开放借阅通知",
            "noticeBody": "系统已就绪，欢迎检索图书并提交借阅申请。",
        },
        "portalBanners": [
            {"title": "开架阅览", "lead": "按书名、作者或 ISBN 检索，在线提交借阅。"},
            {"title": "借阅须知", "lead": "每人同时最多借阅 5 本，请按时归还。"},
            {"title": "开放时间", "lead": "工作日开放；临时调整见馆内公告。"},
            {"title": "我的书架", "lead": "登录后查看借阅进度与到期提醒。"},
            {"title": "新书上架", "lead": "分类浏览最新到馆图书。"},
        ],
    }


def _archive_ticket_schema(
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
    check_mutex: bool = False,
    category_limit: int = 0,
    soft_delete: bool = False,
    tag_filter: bool = False,
    week_calendar: bool = False,
    week_calendar_label: str = "我的日程",
    allow_checkin: bool = False,
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
    if play_url_field:
        archive_entity["playUrlField"] = play_url_field
    if body_field:
        archive_entity["bodyField"] = body_field
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
        "noShowAfterEnd": bool(no_show_after_end and allow_checkin),
        "noShowPenaltyYuan": float(no_show_penalty_yuan or 0) if (no_show_after_end and allow_checkin) else 0,
        "pickLoanPeriod": bool(pick_loan_period),
        "allowQty": bool(allow_qty),
        "requireRemark": bool(require_remark),
        "remarkLabel": remark_label or "说明",
        "pickDateRange": bool(pick_date_range),
    }
    if due_label:
        ticket_entity["dueLabel"] = due_label
    if fine_label:
        ticket_entity["fineLabel"] = fine_label
    if fine_paid_label:
        ticket_entity["finePaidLabel"] = fine_paid_label
    if checkin_label:
        ticket_entity["checkinLabel"] = checkin_label
    if week_calendar:
        ticket_entity["weekCalendarLabel"] = week_calendar_label
    if rich_remark:
        ticket_entity["richRemark"] = True
    admin_menus = [
        {"key": "dashboard", "label": "工作台"},
        {"key": "archive", "label": archive_menu_admin, "superOnly": True},
        {"key": "category", "label": "分类管理", "superOnly": True},
        {"key": "users", "label": users_menu, "superOnly": True},
        {"key": "ticket_pending", "label": pending_label},
        {"key": "ticket_records", "label": records_label},
    ]
    if with_deadline:
        admin_menus.append({"key": "deadline", "label": deadline_label})
    admin_menus.append({"key": "content", "label": "公告管理", "superOnly": True})
    user_menus = [
        {"key": "archive", "label": archive_menu_user},
        {"key": "my_tickets", "label": my_tickets_label},
    ]
    if week_calendar:
        user_menus.append({"key": "week_calendar", "label": week_calendar_label})
    user_menus.extend(
        [
            {"key": "content", "label": "公告"},
            {"key": "profile", "label": "个人资料"},
        ]
    )
    if messages_page_lead is None:
        if with_deadline:
            messages_page_lead = f"审核结果、{remind}提醒与系统通知。"
        elif allow_checkin:
            messages_page_lead = "审核结果、活动提醒与系统通知。"
        else:
            messages_page_lead = "审核结果与系统通知。"
    if recommend_latest_hint is None:
        recommend_latest_hint = "最新上架" if soft_delete and stock_display == "count" else "最新发布"
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
            "archive": archive_entity,
            "ticket": ticket_entity,
        },
        "menus": {
            "admin": admin_menus,
            "user": user_menus,
        },
        "labels": {
            "appName": app,
            "authEyebrow": auth_eyebrow,
            "authLead": auth_lead,
            "authPoints": auth_points,
            "registerRoleHint": register_hint,
            "noticePageTitle": notice_page_title,
            "noticePageLead": notice_page_lead,
            "messagesPageLead": messages_page_lead,
            "recommendSectionTitle": "猜你喜欢",
            "recommendLatestHint": recommend_latest_hint,
        },
        "seeds": {
            "noticeTitle": notice_title,
            "noticeBody": notice_body,
        },
    }


def _with_portal_banners(schema: dict[str, Any], banners: list[dict[str, str]]) -> dict[str, Any]:
    out = dict(schema)
    out["portalBanners"] = banners
    return out


def _equip_schema(title: str) -> dict[str, Any]:
    return _with_portal_banners(
        _archive_ticket_schema(
            title,
            domain="DOM-EQUIP",
            user_role_id="user",
            user_label="借用人",
            admin_label="实验室主管（总管）",
            subadmin_label="器材管理员",
            archive_key="equip",
            archive_label="设备",
            archive_plural="设备",
            archive_fields=[
                {"key": "title", "label": "设备名称", "type": "string"},
                {"key": "author", "label": "品牌/型号", "type": "string"},
                {"key": "isbn", "label": "资产编号", "type": "string"},
                {"key": "category", "label": "分类", "type": "select"},
                {"key": "stock", "label": "可借数量", "type": "number"},
                {"key": "requiresTraining", "label": "需培训(1是0否)", "type": "number"},
                {"key": "ownerName", "label": "责任人", "type": "string"},
            ],
            ticket_key="loan",
            ticket_label="借用单",
            ticket_plural="借用",
            verbs={
                "apply": "申请借用",
                "approve": "通过",
                "reject": "驳回",
                "return": "归还",
                "remind": "催还",
            },
            states={
                "pending": "待审核",
                "approved": "借用中",
                "rejected": "已驳回",
                "returned": "已归还",
                "overdue": "已逾期",
            },
            archive_menu_admin="设备管理",
            archive_menu_user="设备检索",
            users_menu="用户管理",
            auth_eyebrow="实验室设备",
            auth_lead="验证码登录；检索设备并申请借用，管理员审核后领用。",
            auth_points=["验证码登录", "设备检索", "借用申请与归还"],
            register_hint="注册后可申请借用实验室设备",
            notice_title="设备借用须知",
            notice_body="请按需申请、按时归还；逾期将登记催还。",
            notice_page_title="实验室公告",
            notice_page_lead="借用须知、开放时段与临时通知，点击条目阅读全文。",
            my_tickets_label="我的借用",
            pending_label="借用审核",
            records_label="借用记录",
            deadline_label="逾期催还",
            soft_delete=True,
        ),
        [
            {"title": "实验室器材", "lead": "检索设备、查看库存，在线提交借用申请。"},
            {"title": "借用须知", "lead": "按需申请、按时归还；逾期将登记催还。"},
            {"title": "领用时段", "lead": "工作日办理领用与归还，详见实验室公告。"},
            {"title": "我的借用", "lead": "登录后查看审核进度与归还期限。"},
            {"title": "器材公告", "lead": "检修停用与临时安排见公告栏。"},
        ],
    )


def _asset_schema(title: str) -> dict[str, Any]:
    """固定资产 / 耗材申领：档案+单据+库存，无逾期（与设备借用区分）。"""
    return _with_portal_banners(
        _archive_ticket_schema(
            title,
            domain="DOM-ASSET",
            user_role_id="user",
            user_label="申领人",
            admin_label="仓管主管（总管）",
            subadmin_label="库管员",
            archive_key="asset",
            archive_label="物资",
            archive_plural="物资",
            archive_fields=[
                {"key": "title", "label": "物资名称", "type": "string"},
                {"key": "author", "label": "规格/型号", "type": "string"},
                {"key": "isbn", "label": "资产编号", "type": "string"},
                {"key": "category", "label": "分类", "type": "select"},
                {"key": "stock", "label": "可领数量", "type": "number"},
            ],
            ticket_key="requisition",
            ticket_label="申领单",
            ticket_plural="申领",
            verbs={
                "apply": "提交申领",
                "approve": "通过出库",
                "reject": "驳回",
                "return": "退库",
                "remind": "催办",
            },
            states={
                "pending": "待审核",
                "approved": "已出库",
                "rejected": "已驳回",
                "returned": "已退库",
                "overdue": "已失效",
            },
            archive_menu_admin="物资台账",
            archive_menu_user="物资目录",
            users_menu="用户管理",
            auth_eyebrow="物资领用",
            auth_lead="验证码登录；浏览物资台账并提交申领，库管审核后出库。",
            auth_points=["验证码登录", "物资目录", "申领审核与出库"],
            register_hint="注册后可按部门申领办公物资与耗材",
            notice_title="领用须知",
            notice_body="请按需申领、如实填写用途；固定资产领用后请妥善保管，耗材出库不退。",
            notice_page_title="仓储公告",
            notice_page_lead="领用须知、盘点安排与临时通知，点击条目阅读全文。",
            my_tickets_label="我的申领",
            pending_label="申领审核",
            records_label="申领记录",
            with_deadline=False,
            soft_delete=True,
            allow_qty=True,
            require_remark=True,
            remark_label="用途说明",
        ),
        [
            {"title": "物资台账", "lead": "固定资产与耗材分类浏览，查看可领库存。"},
            {"title": "在线申领", "lead": "提交申领单，库管审核通过后办理出库。"},
            {"title": "仓储公告", "lead": "盘点安排与领用须知见公告栏。"},
            {"title": "我的申领", "lead": "登录后跟踪审核与出库进度。"},
            {"title": "分类检索", "lead": "按品类快速定位可领物资。"},
        ],
    )


def _crm_schema(title: str) -> dict[str, Any]:
    """轻量 CRM：客户档案 + 跟进单据（非公海/外呼引擎）。"""
    return _with_portal_banners(
        _archive_ticket_schema(
            title,
            domain="DOM-CRM",
            user_role_id="user",
            user_label="业务员",
            admin_label="销售主管（总管）",
            subadmin_label="客户经理",
            archive_key="customer",
            archive_label="客户",
            archive_plural="客户",
            archive_fields=[
                {"key": "title", "label": "客户名称", "type": "string"},
                {"key": "author", "label": "联系人", "type": "string"},
                {"key": "isbn", "label": "电话/备注", "type": "string"},
                {"key": "stage", "label": "销售阶段", "type": "string"},
                {"key": "category", "label": "客户分级", "type": "select"},
                {"key": "stock", "label": "可跟进", "type": "number"},
            ],
            ticket_key="follow_up",
            ticket_label="跟进单",
            ticket_plural="跟进",
            verbs={
                "apply": "提交跟进",
                "approve": "确认",
                "reject": "驳回",
                "return": "完结",
                "remind": "催办",
            },
            states={
                "pending": "待确认",
                "approved": "跟进中",
                "rejected": "已驳回",
                "returned": "已完结",
                "overdue": "已失效",
            },
            archive_menu_admin="客户档案",
            archive_menu_user="客户列表",
            users_menu="用户管理",
            auth_eyebrow="客户跟进",
            auth_lead="验证码登录；维护客户档案并提交跟进记录，主管确认后完结。",
            auth_points=["验证码登录", "客户档案", "跟进审核"],
            register_hint="注册后可维护名下客户并提交跟进",
            notice_title="跟进须知",
            notice_body="请如实登记联系结果；重要商机请及时提交跟进单由主管确认。",
            notice_page_title="销售公告",
            notice_page_lead="跟进规范与临时通知，点击条目阅读全文。",
            my_tickets_label="我的跟进",
            pending_label="跟进确认",
            records_label="跟进记录",
            with_deadline=False,
            stock_display="available",
            require_remark=True,
            remark_label="跟进内容",
        ),
        [
            {"title": "客户档案", "lead": "按分级浏览客户，维护联系人与备注。"},
            {"title": "客户跟进", "lead": "提交跟进单，主管确认后进入跟进中并可完结。"},
            {"title": "销售公告", "lead": "跟进规范与活动通知见公告栏。"},
            {"title": "我的跟进", "lead": "登录后查看待办与跟进进度。"},
            {"title": "分级管理", "lead": "按客户分级筛选重点对象。"},
        ],
    )


def _media_schema(title: str) -> dict[str, Any]:
    return _with_portal_banners(
        _archive_ticket_schema(
            title,
            domain="DOM-MEDIA",
            user_role_id="user",
            user_label="观众",
            admin_label="内容总监（总管）",
            subadmin_label="运营编辑",
            archive_key="media",
            archive_label="影片",
            archive_plural="片单",
            archive_fields=[
                {"key": "title", "label": "片名", "type": "string"},
                {"key": "author", "label": "导演/主演", "type": "string"},
                {"key": "isbn", "label": "播放链接", "type": "url"},
                {"key": "durationSec", "label": "时长(秒)", "type": "number"},
                {"key": "category", "label": "分类", "type": "select"},
                {"key": "stock", "label": "可点播", "type": "number"},
            ],
            ticket_key="favorite",
            ticket_label="收藏单",
            ticket_plural="收藏",
            verbs={
                "apply": "收藏",
                "approve": "通过",
                "reject": "驳回",
                "return": "取消收藏",
                "remind": "提醒",
            },
            states={
                "pending": "待确认",
                "approved": "已收藏",
                "rejected": "已驳回",
                "returned": "已取消",
                "overdue": "已失效",
            },
            archive_menu_admin="片单管理",
            archive_menu_user="片单检索",
            users_menu="用户管理",
            auth_eyebrow="影视点播",
            auth_lead="验证码登录；浏览片单、在线播放，收藏想看的影视综。",
            auth_points=["验证码登录", "片单检索与播放", "收藏想看"],
            register_hint="注册后可浏览片单并收藏",
            notice_title="观影须知",
            notice_body="片源仅供学习演示；请文明观影，勿传播未授权内容。",
            notice_page_title="平台公告",
            notice_page_lead="上新片单、维护窗口与观影须知，点击条目阅读全文。",
            my_tickets_label="我的收藏",
            pending_label="收藏确认",
            records_label="收藏记录",
            with_deadline=False,
            play_url_field="isbn",
            stock_display="available",
            soft_delete=True,
        ),
        [
            {"title": "热播片单", "lead": "电影、电视剧、综艺分类浏览，点击即可播放。"},
            {"title": "收藏想看", "lead": "感兴趣的内容一键收藏，方便下次回看。"},
            {"title": "平台公告", "lead": "上新与维护通知见公告栏。"},
            {"title": "猜你喜欢", "lead": "根据浏览偏好推荐片单。"},
            {"title": "分类点播", "lead": "按类型快速找到想看的内容。"},
        ],
    )


def _music_schema(title: str) -> dict[str, Any]:
    return _with_portal_banners(
        _archive_ticket_schema(
            title,
            domain="DOM-MUSIC",
            user_role_id="user",
            user_label="听众",
            admin_label="曲库主管（总管）",
            subadmin_label="运营编辑",
            archive_key="track",
            archive_label="歌曲",
            archive_plural="曲库",
            archive_fields=[
                {"key": "title", "label": "歌名", "type": "string"},
                {"key": "author", "label": "歌手/专辑", "type": "string"},
                {"key": "isbn", "label": "播放链接", "type": "url"},
                {"key": "durationSec", "label": "时长(秒)", "type": "number"},
                {"key": "category", "label": "曲风", "type": "select"},
                {"key": "stock", "label": "可播放", "type": "number"},
            ],
            ticket_key="favorite",
            ticket_label="收藏单",
            ticket_plural="收藏",
            verbs={
                "apply": "收藏",
                "approve": "通过",
                "reject": "驳回",
                "return": "取消收藏",
                "remind": "提醒",
            },
            states={
                "pending": "待确认",
                "approved": "已收藏",
                "rejected": "已驳回",
                "returned": "已取消",
                "overdue": "已失效",
            },
            archive_menu_admin="曲库管理",
            archive_menu_user="曲库检索",
            users_menu="用户管理",
            auth_eyebrow="在线音乐",
            auth_lead="验证码登录；浏览曲库、在线试听，收藏喜欢的歌曲。",
            auth_points=["验证码登录", "曲库检索与播放", "收藏喜欢"],
            register_hint="注册后可浏览曲库并收藏",
            notice_title="试听须知",
            notice_body="曲源仅供学习演示；请尊重版权，勿传播未授权内容。",
            notice_page_title="平台公告",
            notice_page_lead="上新歌单、维护窗口与试听须知，点击条目阅读全文。",
            my_tickets_label="我的收藏",
            pending_label="收藏确认",
            records_label="收藏记录",
            with_deadline=False,
            play_url_field="isbn",
            stock_display="available",
            soft_delete=True,
        ),
        [
            {"title": "热门曲库", "lead": "流行、摇滚、民谣等分类浏览，点击即可试听。"},
            {"title": "收藏喜欢", "lead": "喜欢的歌曲一键收藏，方便下次回听。"},
            {"title": "平台公告", "lead": "上新与维护通知见公告栏。"},
            {"title": "猜你喜欢", "lead": "根据听歌偏好推荐曲目。"},
            {"title": "曲风浏览", "lead": "按曲风快速找到想听的歌。"},
        ],
    )


def _forum_schema(title: str) -> dict[str, Any]:
    return _with_portal_banners(
        _archive_ticket_schema(
            title,
            domain="DOM-FORUM",
            user_role_id="user",
            user_label="用户",
            admin_label="站长（总管）",
            subadmin_label="版主",
            archive_key="post",
            archive_label="主帖",
            archive_plural="主帖",
            archive_fields=[
                {"key": "title", "label": "标题", "type": "string"},
                {"key": "author", "label": "楼主", "type": "string"},
                {"key": "isbn", "label": "正文", "type": "richtext"},
                {"key": "category", "label": "板块", "type": "select"},
                {"key": "stock", "label": "可见", "type": "number"},
            ],
            ticket_key="reply",
            ticket_label="回复",
            ticket_plural="回复",
            verbs={
                "apply": "回复",
                "approve": "通过",
                "reject": "驳回",
                "return": "撤回",
                "remind": "提醒",
            },
            states={
                "pending": "待审核",
                "approved": "已展示",
                "rejected": "已驳回",
                "returned": "已撤回",
                "overdue": "已失效",
            },
            archive_menu_admin="主帖管理",
            archive_menu_user="帖子检索",
            users_menu="用户管理",
            auth_eyebrow="校园论坛",
            auth_lead="验证码登录；按板块浏览主帖，富文本回复讨论，支持楼中楼引用。",
            auth_points=["验证码登录", "板块与主帖检索", "富文本回复与楼中楼"],
            register_hint="注册后可浏览主帖并回复",
            notice_title="社区公约",
            notice_body="请文明讨论；回复经版主审核后展示。主帖由站长维护，回复可 @他人 一层引用。",
            notice_page_title="站内公告",
            notice_page_lead="版规、维护窗口与活动通知，点击条目阅读全文。",
            my_tickets_label="我的回复",
            pending_label="回复审核",
            records_label="回复记录",
            with_deadline=False,
            body_field="isbn",
            rich_remark=True,
            stock_display="available",
            soft_delete=True,
            tag_filter=True,
        ),
        [
            {"title": "热门板块", "lead": "学习、生活、二手信息分区浏览主帖。"},
            {"title": "讨论交流", "lead": "跟帖回复，支持引用他人发言。"},
            {"title": "站内公告", "lead": "版规与活动通知见公告栏。"},
            {"title": "我的帖子", "lead": "登录后管理发帖与回复进度。"},
            {"title": "标签筛选", "lead": "按标签快速找到感兴趣的话题。"},
        ],
    )


def _blog_schema(title: str) -> dict[str, Any]:
    return _with_portal_banners(
        _archive_ticket_schema(
            title,
            domain="DOM-BLOG",
            user_role_id="user",
            user_label="读者",
            admin_label="主编（总管）",
            subadmin_label="编辑",
            archive_key="article",
            archive_label="文章",
            archive_plural="文章",
            archive_fields=[
                {"key": "title", "label": "标题", "type": "string"},
                {"key": "author", "label": "作者", "type": "string"},
                {"key": "summary", "label": "摘要", "type": "string"},
                {"key": "isbn", "label": "正文", "type": "richtext"},
                {"key": "category", "label": "分类", "type": "select"},
                {"key": "stock", "label": "可阅读", "type": "number"},
            ],
            ticket_key="favorite",
            ticket_label="收藏单",
            ticket_plural="收藏",
            verbs={
                "apply": "收藏",
                "approve": "通过",
                "reject": "驳回",
                "return": "取消收藏",
                "remind": "提醒",
            },
            states={
                "pending": "待确认",
                "approved": "已收藏",
                "rejected": "已驳回",
                "returned": "已取消",
                "overdue": "已失效",
            },
            archive_menu_admin="文章管理",
            archive_menu_user="文章检索",
            users_menu="用户管理",
            auth_eyebrow="个人博客",
            auth_lead="验证码登录；按分类阅读富文本文章，收藏喜欢的博文。",
            auth_points=["验证码登录", "文章检索与阅读", "收藏订阅"],
            register_hint="注册后可阅读文章并收藏",
            notice_title="阅读须知",
            notice_body="文章仅供学习演示；转载请注明出处。内容由主编维护发布。",
            notice_page_title="站点公告",
            notice_page_lead="上新、维护与征稿通知，点击条目阅读全文。",
            my_tickets_label="我的收藏",
            pending_label="收藏确认",
            records_label="收藏记录",
            with_deadline=False,
            body_field="isbn",
            stock_display="available",
            soft_delete=True,
        ),
        [
            {"title": "最新文章", "lead": "技术、随笔、资讯分类浏览富文本正文。"},
            {"title": "收藏订阅", "lead": "喜欢的文章一键收藏，方便回看。"},
            {"title": "站点公告", "lead": "上新与征稿通知见公告栏。"},
            {"title": "猜你喜欢", "lead": "根据阅读偏好推荐文章。"},
            {"title": "分类阅读", "lead": "按分类快速进入感兴趣的专栏。"},
        ],
    )


def _activity_schema(title: str) -> dict[str, Any]:
    return _with_portal_banners(
        _archive_ticket_schema(
            title,
            domain="DOM-ACTIVITY",
            user_role_id="user",
            user_label="报名者",
            admin_label="活动主管（总管）",
            subadmin_label="活动助理",
            archive_key="activity",
            archive_label="活动",
            archive_plural="活动",
            archive_fields=[
                {"key": "title", "label": "活动名称", "type": "string"},
                {"key": "author", "label": "主办方", "type": "string"},
                {"key": "isbn", "label": "地点", "type": "string"},
                {"key": "category", "label": "分类", "type": "select"},
                {"key": "stock", "label": "剩余名额", "type": "number"},
                {"key": "checkinCode", "label": "签到码", "type": "string"},
                {"key": "startAt", "label": "开始时间", "type": "datetime", "timeStepMinutes": 30},
                {"key": "endAt", "label": "结束时间", "type": "datetime", "timeStepMinutes": 30},
                {"key": "applyDeadlineAt", "label": "报名截止", "type": "datetime", "timeStepMinutes": 30},
                {"key": "serviceHours", "label": "志愿时长(小时)", "type": "number"},
            ],
            ticket_key="signup",
            ticket_label="报名单",
            ticket_plural="报名",
            verbs={
                "apply": "报名",
                "approve": "通过",
                "reject": "驳回",
                "return": "取消报名",
                "remind": "提醒",
            },
            states={
                "pending": "待审核",
                "approved": "已报名",
                "rejected": "已驳回",
                "returned": "已取消",
                "overdue": "爽约",
            },
            archive_menu_admin="活动管理",
            archive_menu_user="活动检索",
            users_menu="用户管理",
            auth_eyebrow="活动报名",
            auth_lead="验证码登录；浏览活动并报名；系统检测时段冲突与报名截止；到场口令签到；结束未签到记爽约。",
            auth_points=["验证码登录", "活动检索", "报名、冲突检测、口令签到与爽约"],
            register_hint="注册后可报名校园活动",
            notice_title="报名须知",
            notice_body="请如实填写资料；名额有限；时段冲突或已截止将无法提交；到场请向主办方索取签到码；活动结束后未签到将记为爽约。",
            notice_page_title="活动公告",
            notice_page_lead="报名须知、活动变更与临时通知，点击条目阅读全文。",
            my_tickets_label="我的报名",
            pending_label="报名审核",
            records_label="报名记录",
            with_deadline=False,
            allow_rating=True,
            week_calendar=True,
            week_calendar_label="我的日程",
            allow_checkin=True,
            no_show_after_end=True,
            no_show_penalty_yuan=0,
        ),
        [
            {"title": "热门活动", "lead": "社团、志愿、讲座分类浏览，在线报名。"},
            {"title": "到场签到", "lead": "到场向主办方索取签到码完成核验；时段重叠将无法重复报名。"},
            {"title": "活动公告", "lead": "变更与须知见公告栏。"},
            {"title": "我的日程", "lead": "登录后查看已报名活动与时段安排。"},
            {"title": "志愿时长", "lead": "志愿类活动可登记服务时长。"},
        ],
    )


def _lost_schema(title: str) -> dict[str, Any]:
    return _archive_ticket_schema(
        title,
        domain="DOM-LOST",
        user_role_id="user",
        user_label="用户",
        admin_label="招领主管（总管）",
        subadmin_label="招领管理员",
        archive_key="lost_item",
        archive_label="启事",
        archive_plural="启事",
        archive_fields=[
            {"key": "title", "label": "物品名称", "type": "string"},
            {"key": "author", "label": "拾获/登记人", "type": "string"},
            {"key": "isbn", "label": "地点/特征", "type": "string"},
            {"key": "itemKind", "label": "类型(招领/寻物)", "type": "string"},
            {"key": "foundAt", "label": "拾获时间", "type": "datetime"},
            {"key": "category", "label": "分类", "type": "select"},
            {"key": "stock", "label": "可认领", "type": "number"},
        ],
        ticket_key="claim",
        ticket_label="认领单",
        ticket_plural="认领",
        verbs={
            "apply": "申请认领",
            "approve": "通过",
            "reject": "驳回",
            "return": "撤销认领",
            "remind": "提醒",
        },
        states={
            "pending": "待审核",
            "approved": "已认领",
            "rejected": "已驳回",
            "returned": "已撤销",
            "overdue": "已失效",
        },
        archive_menu_admin="启事管理",
        archive_menu_user="失物检索",
        users_menu="用户管理",
        auth_eyebrow="失物招领",
        auth_lead="验证码登录；浏览失物启事，提交认领申请，管理员审核后领取。",
        auth_points=["验证码登录", "失物检索", "认领申请与审核"],
        register_hint="注册后可浏览启事并申请认领",
        notice_title="招领须知",
        notice_body="认领时请提供有效身份与物品特征；审核通过后到指定地点领取。",
        notice_page_title="招领公告",
        notice_page_lead="招领须知与临时通知，点击条目阅读全文。",
        my_tickets_label="我的认领",
        pending_label="认领审核",
        records_label="认领记录",
        with_deadline=False,
        stock_display="available",
        require_attach=True,
        allow_rating=True,
        require_remark=True,
        remark_label="认领说明",
    )


def _course_schema(title: str) -> dict[str, Any]:
    return _with_portal_banners(
        _archive_ticket_schema(
            title,
            domain="DOM-COURSE",
            user_role_id="student",
            user_label="学生",
            admin_label="教务主管（总管）",
            subadmin_label="选课管理员",
            archive_key="course",
            archive_label="课程",
            archive_plural="课程",
            archive_fields=[
                {"key": "title", "label": "课程名称", "type": "string"},
                {"key": "author", "label": "授课教师", "type": "string"},
                {"key": "isbn", "label": "课号/教室", "type": "string"},
                {"key": "category", "label": "分类", "type": "select"},
                {"key": "stock", "label": "剩余名额", "type": "number"},
                {"key": "mutexCode", "label": "互斥码", "type": "string"},
                {"key": "startAt", "label": "上课开始", "type": "datetime"},
                {"key": "endAt", "label": "上课结束", "type": "datetime"},
                {"key": "applyDeadlineAt", "label": "选课截止", "type": "datetime"},
                {"key": "credit", "label": "学分", "type": "number"},
            ],
            ticket_key="enrollment",
            ticket_label="选课单",
            ticket_plural="选课",
            verbs={
                "apply": "申请选课",
                "approve": "通过",
                "reject": "驳回",
                "return": "退选",
                "remind": "提醒",
            },
            states={
                "pending": "待审核",
                "approved": "已选上",
                "rejected": "已驳回",
                "returned": "已退选",
                "overdue": "已失效",
            },
            archive_menu_admin="课程管理",
            archive_menu_user="课程检索",
            users_menu="学生管理",
            auth_eyebrow="公选选课",
            auth_lead="验证码登录；浏览公选课并申请；系统检测上课时段冲突、互斥组与分类限额。",
            auth_points=["验证码登录", "课程检索", "选课、冲突/互斥与分类限额"],
            register_hint="注册后可以学生身份选课",
            notice_title="选课须知",
            notice_body="请在截止前选课；名额有限；时段冲突、互斥组或分类超额将无法提交。",
            notice_page_title="教务公告",
            notice_page_lead="选课须知、开放时段与临时通知，点击条目阅读全文。",
            my_tickets_label="我的选课",
            pending_label="选课审核",
            records_label="选课记录",
            with_deadline=False,
            check_mutex=True,
            category_limit=1,
            week_calendar=True,
            week_calendar_label="我的课表",
        ),
        [
            {"title": "本学期公选", "lead": "按分类浏览课程、课时与剩余名额。"},
            {"title": "选课须知", "lead": "时段重叠或名额已满时无法提交，请注意截止时间。"},
            {"title": "教务公告", "lead": "开放时段与变更通知见公告栏。"},
            {"title": "我的课表", "lead": "登录后查看已选课程与上课时间。"},
            {"title": "学分一览", "lead": "选课前可查看课程学分与教师信息。"},
        ],
    )


def _standalone_ticket_schema(
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
        ordered: dict[str, str] = {}
        for k, v in states.items():
            if k == "pending":
                ordered["pending"] = "待初审" if v in ("待受理", "待审核") else v
                ordered["pending_final"] = "待终审"
            else:
                ordered[k] = v
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


def _dorm_schema(title: str) -> dict[str, Any]:
    return _standalone_ticket_schema(
        title,
        domain="DOM-DORM",
        user_role_id="student",
        user_label="学生",
        admin_label="宿管（总管）",
        subadmin_label="楼管",
        ticket_key="repair",
        ticket_label="报修单",
        ticket_plural="报修",
        verbs={
            "apply": "提交报修",
            "approve": "受理",
            "reject": "驳回",
            "return": "完成",
        },
        states={
            "pending": "待受理",
            "approved": "处理中",
            "rejected": "已驳回",
            "returned": "已完成",
        },
        site_menu="楼栋房间",
        type_menu="报修类型",
        users_menu="学生管理",
        auth_eyebrow="宿舍服务",
        auth_lead="验证码登录；学生可提交报修，宿管受理跟进。",
        auth_points=["验证码登录", "报修申请", "受理进度"],
        register_hint="注册后以学生身份提交报修",
        notice_title="报修须知",
        notice_body="请如实填写宿舍与故障描述并上传现场照片，宿管将尽快受理。",
        notice_page_title="宿舍公告",
        notice_page_lead="报修须知、宿舍安排与临时通知，点击条目阅读全文。",
        two_level_approve=True,
        require_attach=True,
        allow_rating=True,
    )


def _property_schema(title: str) -> dict[str, Any]:
    return _standalone_ticket_schema(
        title,
        domain="DOM-PROPERTY",
        user_role_id="user",
        user_label="住户",
        admin_label="物业主管",
        subadmin_label="维修员",
        ticket_key="repair",
        ticket_label="报修单",
        ticket_plural="报修",
        verbs={
            "apply": "提交报修",
            "approve": "受理",
            "reject": "驳回",
            "return": "完成",
        },
        states={
            "pending": "待受理",
            "approved": "处理中",
            "rejected": "已驳回",
            "returned": "已完成",
        },
        site_menu="楼栋房间",
        type_menu="报修类型",
        users_menu="用户管理",
        auth_eyebrow="物业报修",
        auth_lead="验证码登录；住户提交报修，物业受理跟进。",
        auth_points=["验证码登录", "报修申请", "受理进度"],
        register_hint="注册后以住户身份提交报修",
        notice_title="报修须知",
        notice_body="请如实填写地址与故障描述并上传现场照片，物业将尽快受理。",
        notice_page_title="物业公告",
        notice_page_lead="报修须知、社区安排与临时通知，点击条目阅读全文。",
        two_level_approve=True,
        require_attach=True,
        allow_rating=True,
    )


def _it_schema(title: str) -> dict[str, Any]:
    return _standalone_ticket_schema(
        title,
        domain="DOM-IT",
        user_role_id="user",
        user_label="师生",
        admin_label="运维主管",
        subadmin_label="运维员",
        ticket_key="ticket",
        ticket_label="故障单",
        ticket_plural="故障报修",
        verbs={
            "apply": "提交故障",
            "approve": "受理",
            "reject": "驳回",
            "return": "完成",
        },
        states={
            "pending": "待受理",
            "approved": "处理中",
            "rejected": "已驳回",
            "returned": "已完成",
        },
        site_menu="区域终端",
        type_menu="故障类型",
        users_menu="用户管理",
        auth_eyebrow="校园网运维",
        auth_lead="验证码登录；师生提交故障，运维受理跟进。",
        auth_points=["验证码登录", "故障报修", "受理进度"],
        register_hint="注册后可提交故障报修",
        notice_title="报修须知",
        notice_body="请写明区域、终端与故障现象并上传截图/照片，运维将尽快受理。",
        notice_page_title="运维公告",
        notice_page_lead="故障处理须知与临时通知，点击条目阅读全文。",
        my_tickets_label="我的故障",
        pending_label="故障受理",
        records_label="报修记录",
        two_level_approve=True,
        require_attach=True,
        allow_rating=True,
    )


def _generic_schema(title: str, domain: str) -> dict[str, Any]:
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


def _order_shell_schema(
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
                {"key": "category", "label": "分类管理", "superOnly": True},
                {"key": "users", "label": users_menu, "superOnly": True},
                {"key": "orders", "label": orders_admin_label},
                {"key": "content", "label": "公告管理", "superOnly": True},
            ],
            "user": [
                {"key": "archive", "label": archive_menu_user},
                {"key": "cart", "label": cart_label},
                {"key": "my_orders", "label": my_orders_label},
                {"key": "addresses", "label": "收货地址"},
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
            "messagesPageLead": "订单进度与系统通知。",
            "recommendLatestHint": "最新上架",
        },
        "seeds": {"noticeTitle": notice_title, "noticeBody": notice_body},
    }


def _slot_shell_schema(
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
) -> dict[str, Any]:
    app = product_name_from_title(title)
    admin_menus = [
        {"key": "dashboard", "label": "工作台"},
        {"key": "archive", "label": archive_menu_admin, "superOnly": True},
        {"key": "category", "label": "分类管理", "superOnly": True},
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
        "label": "预约",
        "labelPlural": my_resv_label,
        "states": {
            "pending": "待确认",
            "confirmed": "已预约",
            "cancelled": "已取消",
        },
        "requireRemark": bool(reserve_require_remark),
        "remarkLabel": reserve_remark_label or "备注",
    }
    entities: dict[str, Any] = {
        "archive": {
            "key": archive_key,
            "label": archive_label,
            "labelPlural": archive_plural,
            "fields": archive_fields,
            "stockDisplay": "available",
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


def _shop_schema(title: str) -> dict[str, Any]:
    t = title or ""
    campus = any(k in t for k in ("校园", "校内", "二手", "学校"))
    brow = "校园商城" if campus else "在线商城"
    lead = (
        "验证码登录；浏览商品、加入购物车并提交订单（演示无真支付）。"
        if not campus
        else "验证码登录；浏览校园商品、加入购物车并提交订单（演示无真支付）。"
    )
    return _order_shell_schema(
        title,
        domain="DOM-SHOP",
        user_role_id="user",
        user_label="买家",
        admin_label="商城主管（总管）",
        subadmin_label="订单管理员",
        archive_key="product",
        archive_label="商品",
        archive_plural="商品",
            archive_fields=[
            {"key": "title", "label": "商品名", "type": "string"},
            {"key": "author", "label": "单价(元)", "type": "number"},
            {"key": "isbn", "label": "货号", "type": "string"},
            {"key": "conditionGrade", "label": "成色", "type": "string"},
            {"key": "sellerNote", "label": "卖家备注", "type": "string"},
            {"key": "category", "label": "分类", "type": "select"},
            {"key": "stock", "label": "库存", "type": "number"},
        ],
        archive_menu_admin="商品管理",
        archive_menu_user="商品浏览",
        users_menu="用户管理",
        cart_label="购物车",
        my_orders_label="我的订单",
        orders_admin_label="订单管理",
        auth_eyebrow=brow,
        auth_lead=lead,
        auth_points=["验证码登录", "商品浏览", "购物车与订单"],
        register_hint="注册后可购物下单",
        notice_title="商城须知",
        notice_body="演示环境无真支付；下单后由管理员确认发货/自提。",
        notice_page_title="商城公告",
    )


def _food_schema(title: str) -> dict[str, Any]:
    t = title or ""
    canteen = any(k in t for k in ("食堂", "校园", "档口", "学子"))
    if canteen:
        admin, sub, brow, win, notice = "食堂主管（总管）", "档口管理员", "食堂点餐", "窗口", "食堂公告"
        body = "下单后到对应窗口取餐或按约定配送；演示无真支付。"
    else:
        admin, sub, brow, win, notice = "门店主管（总管）", "店员", "点餐外卖", "档口/门店", "门店公告"
        body = "支持堂食、自取或外卖配送演示；无真支付。"
    return _order_shell_schema(
        title,
        domain="DOM-FOOD",
        user_role_id="user",
        user_label="用餐者",
        admin_label=admin,
        subadmin_label=sub,
        archive_key="dish",
        archive_label="菜品",
        archive_plural="菜品",
        archive_fields=[
            {"key": "title", "label": "菜品名", "type": "string"},
            {"key": "author", "label": "单价(元)", "type": "number"},
            {"key": "isbn", "label": win, "type": "string"},
            {"key": "spicyLevel", "label": "辣度", "type": "string"},
            {"key": "isVegetarian", "label": "素食(1是0否)", "type": "number"},
            {"key": "category", "label": "分类", "type": "select"},
            {"key": "stock", "label": "可售份数", "type": "number"},
        ],
        archive_menu_admin="菜品管理",
        archive_menu_user="点餐",
        users_menu="用户管理",
        cart_label="已选菜品",
        my_orders_label="我的订单",
        orders_admin_label="订单管理",
        auth_eyebrow=brow,
        auth_lead="验证码登录；选菜加入清单并下单（演示无真支付）。",
        auth_points=["验证码登录", "菜品浏览", "下单"],
        register_hint="注册后可点餐",
        notice_title="点餐须知",
        notice_body=body,
        notice_page_title=notice,
        order_states={
            "pending": "待出餐",
            "confirmed": "制作中",
            "shipped": "配送中/待取",
            "completed": "已完成",
            "cancelled": "已取消",
        },
    )


def _meeting_schema(title: str) -> dict[str, Any]:
    """会议室 / 琴房 / 体育场 / 自习室等共用时段预约壳，文案跟题名走。"""
    t = title or ""
    if any(k in t for k in ("琴房", "排练", "舞蹈")):
        noun, remark, admin, sub = "琴房", "排练说明", "琴房管理员（总管）", "琴房值班"
    elif any(k in t for k in ("体育场", "体育馆", "球馆", "羽毛球场", "篮球场", "足球场", "游泳")):
        noun, remark, admin, sub = "场地", "预约说明", "场馆主管（总管）", "场馆管理员"
    elif any(k in t for k in ("自习室", "研习室", "研讨室")):
        noun, remark, admin, sub = "自习室", "用途说明", "教务主管（总管）", "自习室管理员"
    elif any(k in t for k in ("实验室", "实训室")):
        noun, remark, admin, sub = "实验室", "使用说明", "实验室主管（总管）", "实验室管理员"
    elif "会议" in t:
        noun, remark, admin, sub = "会议室", "会议主题", "会务主管（总管）", "会务管理员"
    else:
        noun, remark, admin, sub = "场地", "预约说明", "场地主管（总管）", "场地管理员"
    return _slot_shell_schema(
        title,
        domain="DOM-MEETING",
        user_role_id="user",
        user_label="预约人",
        admin_label=admin,
        subadmin_label=sub,
        archive_key="room",
        archive_label=noun,
        archive_plural=noun,
        archive_fields=[
            {"key": "title", "label": noun, "type": "string"},
            {"key": "author", "label": "费用", "type": "number"},
            {"key": "isbn", "label": "位置", "type": "string"},
            {"key": "seatCapacity", "label": "容纳人数", "type": "number"},
            {"key": "category", "label": "类型", "type": "select"},
        ],
        archive_menu_admin=f"{noun}管理",
        archive_menu_user=noun,
        users_menu="用户管理",
        my_resv_label="我的预约",
        resv_admin_label="预约记录",
        auth_eyebrow=f"{noun}预约",
        auth_lead=f"验证码登录；选择{noun}与时段，占坑预约（约满不可再约）。",
        auth_points=["验证码登录", f"{noun}检索", "时段占坑预约"],
        register_hint=f"注册后可预约{noun}",
        notice_title="预约须知",
        notice_body=f"请填写{remark}；按时使用并及时取消不用的预约以释放时段。",
        notice_page_title="预约公告",
        reserve_require_remark=True,
        reserve_remark_label=remark,
    )


def _hospital_schema(title: str) -> dict[str, Any]:
    return _slot_shell_schema(
        title,
        domain="DOM-HOSPITAL",
        user_role_id="patient",
        user_label="患者",
        admin_label="医务主管（总管）",
        subadmin_label="挂号员",
        archive_key="doctor",
        archive_label="医生",
        archive_plural="医生",
        archive_fields=[
            {"key": "title", "label": "医生", "type": "string"},
            {"key": "author", "label": "挂号费(元)", "type": "number"},
            {"key": "isbn", "label": "职称/说明", "type": "string"},
            {"key": "category", "label": "科室", "type": "select"},
        ],
        archive_menu_admin="医生管理",
        archive_menu_user="选医生",
        users_menu="患者管理",
        my_resv_label="我的挂号",
        resv_admin_label="挂号记录",
        auth_eyebrow="门诊挂号",
        auth_lead="验证码登录；选择科室医生与号源时段挂号。",
        auth_points=["验证码登录", "医生检索", "分时挂号"],
        register_hint="注册后可以患者身份挂号",
        notice_title="挂号须知",
        notice_body="号源有限；请填写就诊人姓名，按时就诊，取消请提前操作。",
        notice_page_title="医院公告",
        reserve_require_remark=True,
        reserve_remark_label="就诊人",
    )


def _parking_schema(title: str) -> dict[str, Any]:
    return _slot_shell_schema(
        title,
        domain="DOM-PARKING",
        user_role_id="user",
        user_label="车主",
        admin_label="车场主管（总管）",
        subadmin_label="车场管理员",
        archive_key="space",
        archive_label="车位",
        archive_plural="车位",
        archive_fields=[
            {"key": "title", "label": "车位号", "type": "string"},
            {"key": "author", "label": "费用(元)", "type": "number"},
            {"key": "isbn", "label": "位置", "type": "string"},
            {"key": "feeRule", "label": "计费规则", "type": "string"},
            {"key": "category", "label": "分区", "type": "select"},
        ],
        archive_menu_admin="车位管理",
        archive_menu_user="选车位",
        users_menu="用户管理",
        my_resv_label="我的预约",
        resv_admin_label="预约记录",
        auth_eyebrow="车位预约",
        auth_lead="验证码登录；选择车位与时段占坑预约。",
        auth_points=["验证码登录", "车位检索", "时段预约"],
        register_hint="注册后可预约车位",
        notice_title="停车须知",
        notice_body="请按时入场；取消预约将释放时段。请填写车牌号便于核对。",
        notice_page_title="车场公告",
        reserve_require_remark=True,
        reserve_remark_label="车牌号",
    )


def _salon_schema(title: str) -> dict[str, Any]:
    return _slot_shell_schema(
        title,
        domain="DOM-SALON",
        user_role_id="user",
        user_label="顾客",
        admin_label="门店主管（总管）",
        subadmin_label="预约管理员",
        archive_key="service",
        archive_label="服务",
        archive_plural="服务",
        archive_fields=[
            {"key": "title", "label": "服务项目", "type": "string"},
            {"key": "author", "label": "价格(元)", "type": "number"},
            {"key": "isbn", "label": "时长说明", "type": "string"},
            {"key": "stylistName", "label": "默认技师", "type": "string"},
            {"key": "category", "label": "分类", "type": "select"},
        ],
        archive_menu_admin="服务管理",
        archive_menu_user="选服务",
        users_menu="顾客管理",
        my_resv_label="我的预约",
        resv_admin_label="预约记录",
        auth_eyebrow="服务预约",
        auth_lead="验证码登录；选择服务项目与时段预约到店。",
        auth_points=["验证码登录", "服务浏览", "时段预约"],
        register_hint="注册后可预约服务",
        notice_title="预约须知",
        notice_body="请准时到店；改约请先取消原时段。",
        notice_page_title="门店公告",
    )


def _hotel_schema(title: str) -> dict[str, Any]:
    return _slot_shell_schema(
        title,
        domain="DOM-HOTEL",
        user_role_id="user",
        user_label="住客",
        admin_label="酒店主管（总管）",
        subadmin_label="前台",
        archive_key="room_type",
        archive_label="房型",
        archive_plural="房型",
        archive_fields=[
            {"key": "title", "label": "房型", "type": "string"},
            {"key": "author", "label": "房价(元)", "type": "number"},
            {"key": "isbn", "label": "说明", "type": "string"},
            {"key": "category", "label": "分类", "type": "select"},
            {"key": "stock", "label": "可售间数", "type": "number"},
        ],
        archive_menu_admin="房型管理",
        archive_menu_user="选房型",
        users_menu="住客管理",
        my_resv_label="我的预订",
        resv_admin_label="预订记录",
        auth_eyebrow="客房预订",
        auth_lead="验证码登录；选择房型与入住时段预订，同步生成订单（无真支付）。",
        auth_points=["验证码登录", "房型浏览", "分时预订与订单"],
        register_hint="注册后可预订客房",
        notice_title="入住须知",
        notice_body="演示环境无真支付；预约成功即占坑并生成订单。",
        notice_page_title="酒店公告",
        with_orders=True,
    )


SCHEMA_BUILDERS = {
    "DOM-LIBRARY": _library_schema,
    "DOM-EQUIP": _equip_schema,
    "DOM-ASSET": _asset_schema,
    "DOM-CRM": _crm_schema,
    "DOM-MEDIA": _media_schema,
    "DOM-MUSIC": _music_schema,
    "DOM-FORUM": _forum_schema,
    "DOM-BLOG": _blog_schema,
    "DOM-ACTIVITY": _activity_schema,
    "DOM-LOST": _lost_schema,
    "DOM-COURSE": _course_schema,
    "DOM-DORM": _dorm_schema,
    "DOM-PROPERTY": _property_schema,
    "DOM-IT": _it_schema,
    "DOM-SHOP": _shop_schema,
    "DOM-FOOD": _food_schema,
    "DOM-MEETING": _meeting_schema,
    "DOM-HOSPITAL": _hospital_schema,
    "DOM-PARKING": _parking_schema,
    "DOM-SALON": _salon_schema,
    "DOM-HOTEL": _hotel_schema,
}


