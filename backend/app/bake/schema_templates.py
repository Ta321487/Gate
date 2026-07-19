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
                    {"key": "category", "label": "分类", "type": "string"},
                    {"key": "stock", "label": "库存", "type": "number"},
                ],
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
            "recommendSectionTitle": "猜你喜欢",
        },
        "seeds": {
            "noticeTitle": "开放借阅通知",
            "noticeBody": "系统已就绪，欢迎检索图书并提交借阅申请。",
        },
        "portalBanners": [
            {"title": "开架阅览", "lead": "按书名、作者或 ISBN 检索，在线提交借阅。"},
            {"title": "借阅须知", "lead": "每人同时最多借阅 5 本，请按时归还。"},
            {"title": "开放时间", "lead": "工作日开放；临时调整见馆内公告。"},
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
    my_tickets_label: str = "我的借用",
    pending_label: str = "借用审核",
    records_label: str = "借用记录",
    deadline_label: str = "逾期催还",
    with_deadline: bool = True,
    play_url_field: str = "",
    body_field: str = "",
    stock_display: str = "count",
    rich_remark: bool = False,
) -> dict[str, Any]:
    """借用/收藏/回复薄壳：档案主数据 + 单据流（组 A / G）。"""
    app = product_name_from_title(title)
    archive_entity: dict[str, Any] = {
        "key": archive_key,
        "label": archive_label,
        "labelPlural": archive_plural,
        "fields": archive_fields,
        "stockDisplay": stock_display,
    }
    if play_url_field:
        archive_entity["playUrlField"] = play_url_field
    if body_field:
        archive_entity["bodyField"] = body_field
    ticket_entity: dict[str, Any] = {
        "key": ticket_key,
        "label": ticket_label,
        "labelPlural": ticket_plural,
        "verbs": verbs,
        "states": states,
    }
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
            "user": [
                {"key": "archive", "label": archive_menu_user},
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
            "recommendSectionTitle": "猜你喜欢",
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
                {"key": "category", "label": "分类", "type": "string"},
                {"key": "stock", "label": "可借数量", "type": "number"},
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
        ),
        [
            {"title": "实验室器材", "lead": "检索设备、查看库存，在线提交借用申请。"},
            {"title": "借用须知", "lead": "按需申请、按时归还；逾期将登记催还。"},
            {"title": "领用时段", "lead": "工作日办理领用与归还，详见实验室公告。"},
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
                {"key": "isbn", "label": "播放链接", "type": "string"},
                {"key": "category", "label": "分类", "type": "string"},
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
        ),
        [
            {"title": "热播片单", "lead": "电影、电视剧、综艺分类浏览，点击即可播放。"},
            {"title": "收藏想看", "lead": "感兴趣的内容一键收藏，方便下次回看。"},
            {"title": "平台公告", "lead": "上新与维护通知见公告栏。"},
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
                {"key": "isbn", "label": "播放链接", "type": "string"},
                {"key": "category", "label": "曲风", "type": "string"},
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
        ),
        [
            {"title": "热门曲库", "lead": "流行、摇滚、民谣等分类浏览，点击即可试听。"},
            {"title": "收藏喜欢", "lead": "喜欢的歌曲一键收藏，方便下次回听。"},
            {"title": "平台公告", "lead": "上新与维护通知见公告栏。"},
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
                {"key": "category", "label": "板块", "type": "string"},
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
        ),
        [
            {"title": "热门板块", "lead": "学习、生活、二手信息分区浏览主帖。"},
            {"title": "回复讨论", "lead": "富文本跟帖；可用 @昵称 一层引用，形成楼中楼。"},
            {"title": "站内公告", "lead": "版规与活动通知见公告栏。"},
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
                {"key": "isbn", "label": "正文", "type": "richtext"},
                {"key": "category", "label": "分类", "type": "string"},
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
        ),
        [
            {"title": "最新文章", "lead": "技术、随笔、资讯分类浏览富文本正文。"},
            {"title": "收藏订阅", "lead": "喜欢的文章一键收藏，方便回看。"},
            {"title": "站点公告", "lead": "上新与征稿通知见公告栏。"},
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
                {"key": "category", "label": "分类", "type": "string"},
                {"key": "stock", "label": "剩余名额", "type": "number"},
                {"key": "startAt", "label": "开始时间", "type": "datetime"},
                {"key": "endAt", "label": "结束时间", "type": "datetime"},
                {"key": "applyDeadlineAt", "label": "报名截止", "type": "datetime"},
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
                "overdue": "已失效",
            },
            archive_menu_admin="活动管理",
            archive_menu_user="活动检索",
            users_menu="用户管理",
            auth_eyebrow="活动报名",
            auth_lead="验证码登录；浏览活动并报名；系统检测时段冲突与报名截止。",
            auth_points=["验证码登录", "活动检索", "报名审核、名额与冲突检测"],
            register_hint="注册后可报名校园活动",
            notice_title="报名须知",
            notice_body="请如实填写资料；名额有限；时段冲突或已截止将无法提交。",
            notice_page_title="活动公告",
            notice_page_lead="报名须知、活动变更与临时通知，点击条目阅读全文。",
            my_tickets_label="我的报名",
            pending_label="报名审核",
            records_label="报名记录",
            with_deadline=False,
        ),
        [
            {"title": "热门活动", "lead": "社团、志愿、讲座分类浏览，在线报名。"},
            {"title": "冲突与截止", "lead": "与已报活动时段重叠或已过截止时间将无法提交。"},
            {"title": "活动公告", "lead": "变更与须知见公告栏。"},
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
            {"key": "category", "label": "分类", "type": "string"},
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
                {"key": "category", "label": "分类", "type": "string"},
                {"key": "stock", "label": "剩余名额", "type": "number"},
                {"key": "startAt", "label": "上课开始", "type": "datetime"},
                {"key": "endAt", "label": "上课结束", "type": "datetime"},
                {"key": "applyDeadlineAt", "label": "选课截止", "type": "datetime"},
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
            auth_lead="验证码登录；浏览公选课并申请；系统检测上课时段冲突与选课截止。",
            auth_points=["验证码登录", "课程检索", "选课、名额与冲突检测"],
            register_hint="注册后可以学生身份选课",
            notice_title="选课须知",
            notice_body="请在截止前选课；名额有限；上课时段冲突将无法提交。",
            notice_page_title="教务公告",
            notice_page_lead="选课须知、开放时段与临时通知，点击条目阅读全文。",
            my_tickets_label="我的选课",
            pending_label="选课审核",
            records_label="选课记录",
            with_deadline=False,
        ),
        [
            {"title": "本学期公选", "lead": "按分类浏览课程、课时与剩余名额。"},
            {"title": "冲突检测", "lead": "与已选课程上课时段重叠时无法提交申请。"},
            {"title": "教务公告", "lead": "开放时段与变更通知见公告栏。"},
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
) -> dict[str, Any]:
    """报修/工单薄壳：主数据 + 用户 + 公告（总管）与单据流（子管）。"""
    app = product_name_from_title(title)
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
                "states": states,
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
        notice_body="请如实填写宿舍与故障描述，宿管将尽快受理。",
        notice_page_title="宿舍公告",
        notice_page_lead="报修须知、宿舍安排与临时通知，点击条目阅读全文。",
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
        notice_body="请如实填写地址与故障描述，物业将尽快受理。",
        notice_page_title="物业公告",
        notice_page_lead="报修须知、社区安排与临时通知，点击条目阅读全文。",
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
        notice_body="请写明区域、终端与故障现象，运维将尽快受理。",
        notice_page_title="运维公告",
        notice_page_lead="故障处理须知与临时通知，点击条目阅读全文。",
        my_tickets_label="我的故障",
        pending_label="故障受理",
        records_label="报修记录",
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
        },
        "seeds": {
            "noticeTitle": "系统公告",
            "noticeBody": "系统已就绪。",
        },
    }


SCHEMA_BUILDERS = {
    "DOM-LIBRARY": _library_schema,
    "DOM-EQUIP": _equip_schema,
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
}


