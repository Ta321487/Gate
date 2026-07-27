"""内容 / 媒资 / 社区域 builder。"""

from __future__ import annotations

from typing import Any

from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.schema.shells import (
    _with_portal_banners,
    archive_favorites_schema,
    archive_ticket_schema,
    category_menu_label,
    product_name_from_title,
)

def _media_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """影视点播：商业默认；校园媒资走 campus。"""
    from app.bake.scene_scan import scene_content_parts

    campus = scene_content_parts(title, proposal_text) == "campus"
    return _with_portal_banners(
        archive_favorites_schema(
            title,
            domain="DOM-MEDIA",
            user_role_id="user",
            user_label="师生" if campus else "观众",
            admin_label="媒资主管（总管）" if campus else "内容总监（总管）",
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
            archive_menu_admin="片单管理",
            archive_menu_user="片单检索",
            users_menu="用户管理",
            auth_eyebrow="校园媒资" if campus else "影视点播",
            auth_lead=(
                "验证码登录；浏览校园片单、在线播放，收藏想看的影视综。"
                if campus
                else "验证码登录；浏览片单、在线播放，收藏想看的影视综。"
            ),
            auth_points=["验证码登录", "片单检索与播放", "收藏想看"],
            register_hint="注册后可浏览片单并收藏",
            notice_title="观影须知",
            notice_body="片源仅供学习使用；请文明观影，勿传播未授权内容。",
            notice_page_title="平台公告",
            notice_page_lead="上新片单、维护窗口与观影须知，点击条目阅读全文。",
            favorites_page_lead="收藏想看的影视综，方便下次回看。",
            play_url_field="isbn",
            stock_display="toggle",
            soft_delete=True,
        ),
        [
            {
                "title": "热播片单",
                "lead": (
                    "教学片、纪录片、活动回放分类浏览，点击即可播放。"
                    if campus
                    else "电影、电视剧、综艺分类浏览，点击即可播放。"
                ),
            },
            {"title": "收藏想看", "lead": "感兴趣的内容一键收藏，方便下次回看。"},
            {"title": "平台公告", "lead": "上新与维护通知见公告栏。"},
            {"title": "猜你喜欢", "lead": "根据浏览偏好推荐片单。"},
            {"title": "分类点播", "lead": "按类型快速找到想看的内容。"},
        ],
    )

def _music_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """在线音乐：商业默认；校园曲库走 campus。"""
    from app.bake.scene_scan import scene_content_parts

    campus = scene_content_parts(title, proposal_text) == "campus"
    return _with_portal_banners(
        archive_favorites_schema(
            title,
            domain="DOM-MUSIC",
            user_role_id="user",
            user_label="师生" if campus else "听众",
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
            archive_menu_admin="曲库管理",
            archive_menu_user="曲库检索",
            users_menu="用户管理",
            auth_eyebrow="校园曲库" if campus else "在线音乐",
            auth_lead=(
                "验证码登录；浏览校园曲库、在线试听，收藏喜欢的歌曲。"
                if campus
                else "验证码登录；浏览曲库、在线试听，收藏喜欢的歌曲。"
            ),
            auth_points=["验证码登录", "曲库检索与播放", "收藏喜欢"],
            register_hint="注册后可浏览曲库并收藏",
            notice_title="试听须知",
            notice_body="曲源仅供学习使用；请尊重版权，勿传播未授权内容。",
            notice_page_title="平台公告",
            notice_page_lead="上新歌单、维护窗口与试听须知，点击条目阅读全文。",
            favorites_page_lead="收藏喜欢的歌曲，方便下次回听。",
            play_url_field="isbn",
            stock_display="toggle",
            soft_delete=True,
        ),
        [
            {
                "title": "热门曲库",
                "lead": (
                    "合唱、器乐、校园原创等分类浏览，点击即可试听。"
                    if campus
                    else "流行、摇滚、民谣等分类浏览，点击即可试听。"
                ),
            },
            {"title": "收藏喜欢", "lead": "喜欢的歌曲一键收藏，方便下次回听。"},
            {"title": "平台公告", "lead": "上新与维护通知见公告栏。"},
            {"title": "猜你喜欢", "lead": "根据听歌偏好推荐曲目。"},
            {"title": "曲风浏览", "lead": "按曲风快速找到想听的歌。"},
        ],
    )

def _forum_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """论坛：校园 BBS 默认；兴趣/小区社区走 community。"""
    from app.bake.scene_scan import scene_for

    community = scene_for("DOM-FORUM", title, proposal_text) == "community"
    schema = _with_portal_banners(
        archive_ticket_schema(
            title,
            domain="DOM-FORUM",
            user_role_id="user",
            user_label="居民" if community else "师生",
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
            auth_eyebrow="兴趣社区" if community else "校园论坛",
            auth_lead=(
                "验证码登录；发帖与按板块浏览，富文本回复讨论，支持楼中楼引用。"
                if not community
                else "验证码登录；邻里发帖与按板块浏览，富文本回复讨论，支持楼中楼引用。"
            ),
            auth_points=["验证码登录", "发帖与检索", "富文本回复与楼中楼"],
            register_hint="注册后可发帖并回复",
            notice_title="社区公约",
            notice_body="请文明讨论；用户可发主帖，违规帖由站长下架。回复经版主审核后展示；可 @他人 一层引用。",
            notice_page_title="站内公告",
            notice_page_lead="版规、维护窗口与活动通知，点击条目阅读全文。",
            my_tickets_label="我的回复",
            pending_label="回复审核",
            records_label="回复记录",
            with_deadline=False,
            body_field="isbn",
            rich_remark=True,
            stock_display="toggle",
            soft_delete=True,
            tag_filter=True,
            user_publish=True,
            approve_ends_flow=True,
        ),
        [
            {
                "title": "热门板块",
                "lead": (
                    "邻里互助、二手闲置、活动通知分区浏览主帖。"
                    if community
                    else "学习、生活、二手信息分区浏览主帖。"
                ),
            },
            {"title": "发帖讨论", "lead": "登录后发布主帖，跟帖回复支持引用。"},
            {"title": "站内公告", "lead": "版规与活动通知见公告栏。"},
            {"title": "我的帖子", "lead": "登录后管理本人发帖与回复进度。"},
            {"title": "标签筛选", "lead": "按标签快速找到感兴趣的话题。"},
        ],
    )
    # archive_ticket_schema 返回后补门户页导语（回复非「申请」）
    labels = dict(schema.get("labels") or {})
    labels.setdefault("myTicketsPageLead", "查看本人回复与审核进度；请先在帖子页跟帖。")
    labels.setdefault("ticketAppliedAtLabel", "回复于")
    labels.setdefault("myTicketsBrowseCta", "去帖子检索")
    labels.setdefault("myTicketsEmptyArchive", "还没有回复，请先在帖子页跟帖。")
    schema["labels"] = labels
    return schema


def _blog_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """博客：个人站默认；校园院刊/学工资讯走 campus。

    上架/下架走 softDelete（shelfCopy：在架/已下架），不再叠一层 stock 开关，
    避免「可阅读/已阅读」与软删文案打架、看起来像资讯 CMS。
    """
    from app.bake.scene_scan import scene_content_parts

    campus = scene_content_parts(title, proposal_text) == "campus"
    return _with_portal_banners(
        archive_favorites_schema(
            title,
            domain="DOM-BLOG",
            user_role_id="user",
            user_label="师生" if campus else "读者",
            admin_label="主编（总管）",
            subadmin_label="编辑",
            archive_key="article",
            archive_label="文章",
            archive_plural="文章",
            archive_fields=[
                {"key": "title", "label": "标题", "type": "string"},
                {"key": "author", "label": "作者", "type": "string"},
                {"key": "summary", "label": "摘要", "type": "textarea"},
                {"key": "isbn", "label": "正文", "type": "richtext"},
                {"key": "category", "label": "分类", "type": "select"},
                # 列仍保留供 ArchiveStore；展示隐藏，上下架只靠 softDelete
                {"key": "stock", "label": "在架", "type": "hidden"},
            ],
            archive_menu_admin="文章管理",
            archive_menu_user="文章检索",
            users_menu="用户管理",
            auth_eyebrow="校园资讯" if campus else "个人博客",
            auth_lead=(
                "验证码登录；按分类阅读院刊/学工资讯，收藏喜欢的文章。"
                if campus
                else "验证码登录；按分类阅读富文本文章，收藏喜欢的博文。"
            ),
            auth_points=["验证码登录", "文章检索与阅读", "收藏订阅"],
            register_hint="注册后可浏览文章并收藏",
            notice_title="阅读须知",
            notice_body="文章仅供学习使用；转载请注明出处。内容由主编维护发布。",
            notice_page_title="站点公告",
            notice_page_lead=(
                "上新、维护与征稿通知，点击条目阅读全文。"
                if campus
                else "上新与维护通知，点击条目阅读全文。"
            ),
            favorites_page_lead="收藏喜欢的文章，方便回看。",
            body_field="isbn",
            stock_display="hidden",
            soft_delete=True,
        ),
        [
            {
                "title": "最新文章",
                "lead": (
                    "教学、学工、活动资讯分类浏览富文本正文。"
                    if campus
                    else "技术、随笔、教程分类浏览富文本正文。"
                ),
            },
            {"title": "收藏订阅", "lead": "喜欢的文章一键收藏，方便回看。"},
            {
                "title": "站点公告",
                "lead": "上新与征稿通知见公告栏。" if campus else "上新与维护通知见公告栏。",
            },
            {"title": "猜你喜欢", "lead": "根据阅读偏好推荐文章。"},
            {"title": "分类阅读", "lead": "按分类快速进入感兴趣的专栏。"},
        ],
    )


def _survey_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """简易问卷：问卷项目档案 + 填写回收统计（无单据）。"""
    app = product_name_from_title(title)
    fields = [
        {"key": "title", "label": "问卷标题", "type": "string"},
        {"key": "author", "label": "发布单位", "type": "string"},
        {"key": "isbn", "label": "说明", "type": "textarea"},
        {"key": "category", "label": "分类", "type": "select"},
        {"key": "stock", "label": "开放", "type": "number"},
    ]
    schema: dict[str, Any] = {
        "version": 1,
        "title": title,
        "capabilities": list(DOMAIN_CAPABILITIES["DOM-SURVEY"]),
        "roles": {
            "user": {"id": "user", "label": "受访者"},
            "admin": {"id": "admin", "label": "调研主管（总管）"},
            "subadmin": {"id": "subadmin", "label": "调研员"},
        },
        "entities": {
            "archive": {
                "key": "survey_form",
                "label": "问卷项目",
                "labelPlural": "问卷项目",
                "fields": fields,
                "stockDisplay": "toggle",
            }
        },
        "menus": {
            "admin": [
                {"key": "dashboard", "label": "工作台"},
                {"key": "archive", "label": "问卷项目", "superOnly": True},
                {"key": "category", "label": category_menu_label(fields), "superOnly": True},
                {"key": "users", "label": "用户管理", "superOnly": True},
                {"key": "content", "label": "公告管理", "superOnly": True},
            ],
            "user": [
                {"key": "archive", "label": "问卷项目"},
                {"key": "content", "label": "公告"},
                {"key": "profile", "label": "个人资料"},
            ],
        },
        "labels": {
            "appName": app,
            "authEyebrow": "问卷调研",
            "authLead": "验证码登录；填写已发布问卷，查看本人答卷与回收统计。",
            "authPoints": ["验证码登录", "问卷填写", "回收统计"],
            "registerRoleHint": "注册后可填写已发布问卷",
            "noticePageTitle": "调研公告",
            "noticePageLead": "调研安排与须知，点击条目阅读全文。",
            "messagesPageLead": "问卷与系统通知。",
        },
        "seeds": {
            "noticeTitle": "问卷须知",
            "noticeBody": "请如实填写；每人每卷限填一次。本期无跳题逻辑与 SPSS 导出。",
        },
    }
    return _with_portal_banners(
        schema,
        [
            {"title": "问卷项目", "lead": "按分类浏览开放问卷。"},
            {"title": "在线填写", "lead": "提交后可在「我的答卷」回看。"},
            {"title": "回收统计", "lead": "管理端查看选项计数。"},
            {"title": "调研公告", "lead": "安排与须知见公告栏。"},
        ],
    )


def _doclib_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """文库资料：资料档案 + 附件权限下载台账（无单据）。"""
    app = product_name_from_title(title)
    fields = [
        {"key": "title", "label": "资料标题", "type": "string"},
        {"key": "author", "label": "发布单位", "type": "string"},
        {"key": "isbn", "label": "摘要说明", "type": "textarea"},
        {"key": "category", "label": "分类", "type": "select"},
        {"key": "stock", "label": "开放", "type": "number"},
    ]
    schema: dict[str, Any] = {
        "version": 1,
        "title": title,
        "capabilities": list(DOMAIN_CAPABILITIES["DOM-DOCLIB"]),
        "roles": {
            "user": {"id": "user", "label": "读者"},
            "admin": {"id": "admin", "label": "资料主管（总管）"},
            "subadmin": {"id": "subadmin", "label": "资料员"},
        },
        "entities": {
            "archive": {
                "key": "doc_item",
                "label": "资料条目",
                "labelPlural": "资料条目",
                "fields": fields,
                "stockDisplay": "toggle",
            }
        },
        "menus": {
            "admin": [
                {"key": "dashboard", "label": "工作台"},
                {"key": "archive", "label": "资料条目", "superOnly": True},
                {"key": "category", "label": category_menu_label(fields), "superOnly": True},
                {"key": "users", "label": "用户管理", "superOnly": True},
                {"key": "content", "label": "公告管理", "superOnly": True},
            ],
            "user": [
                {"key": "archive", "label": "资料条目"},
                {"key": "content", "label": "公告"},
                {"key": "profile", "label": "个人资料"},
            ],
        },
        "labels": {
            "appName": app,
            "authEyebrow": "文库资料",
            "authLead": "验证码登录；浏览资料并按权限下载，查看本人下载台账。",
            "authPoints": ["验证码登录", "资料下载", "下载台账"],
            "registerRoleHint": "注册后可浏览并下载开放资料",
            "noticePageTitle": "文库公告",
            "noticePageLead": "资料更新与须知，点击条目阅读全文。",
            "messagesPageLead": "文库与系统通知。",
        },
        "seeds": {
            "noticeTitle": "文库须知",
            "noticeBody": "下载将记入台账；附件为占位 URL，无真对象存储签名。",
        },
    }
    return _with_portal_banners(
        schema,
        [
            {"title": "资料条目", "lead": "按分类浏览开放资料。"},
            {"title": "按权限下载", "lead": "按登录与管理权限下载。"},
            {"title": "下载台账", "lead": "管理端可查下载记录。"},
            {"title": "文库公告", "lead": "安排与须知见公告栏。"},
        ],
    )


def _vote_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """投票评选：评选活动档案 + 候选人投票计票（无单据）。"""
    app = product_name_from_title(title)
    fields = [
        {"key": "title", "label": "活动标题", "type": "string"},
        {"key": "author", "label": "主办单位", "type": "string"},
        {"key": "isbn", "label": "规则说明", "type": "textarea"},
        {"key": "category", "label": "分类", "type": "select"},
        {"key": "stock", "label": "每人限票", "type": "number"},
    ]
    schema: dict[str, Any] = {
        "version": 1,
        "title": title,
        "capabilities": list(DOMAIN_CAPABILITIES["DOM-VOTE"]),
        "roles": {
            "user": {"id": "user", "label": "投票人"},
            "admin": {"id": "admin", "label": "评选主管（总管）"},
            "subadmin": {"id": "subadmin", "label": "评选员"},
        },
        "entities": {
            "archive": {
                "key": "vote_campaign",
                "label": "评选活动",
                "labelPlural": "评选活动",
                "fields": fields,
                "stockDisplay": "number",
            }
        },
        "menus": {
            "admin": [
                {"key": "dashboard", "label": "工作台"},
                {"key": "archive", "label": "评选活动", "superOnly": True},
                {"key": "category", "label": category_menu_label(fields), "superOnly": True},
                {"key": "users", "label": "用户管理", "superOnly": True},
                {"key": "content", "label": "公告管理", "superOnly": True},
            ],
            "user": [
                {"key": "archive", "label": "评选活动"},
                {"key": "content", "label": "公告"},
                {"key": "profile", "label": "个人资料"},
            ],
        },
        "labels": {
            "appName": app,
            "authEyebrow": "投票评选",
            "authLead": "验证码登录；参与开放评选投票，查看本人选票与结果公示。",
            "authPoints": ["验证码登录", "在线投票", "结果公示"],
            "registerRoleHint": "注册后可参与开放评选投票",
            "noticePageTitle": "评选公告",
            "noticePageLead": "评选安排与须知，点击条目阅读全文。",
            "messagesPageLead": "投票与系统通知。",
        },
        "seeds": {
            "noticeTitle": "投票须知",
            "noticeBody": "请公正投票；每人按活动限票数投给不同候选人。本期无刷票防护。",
        },
    }
    return _with_portal_banners(
        schema,
        [
            {"title": "评选活动", "lead": "按分类浏览开放评选。"},
            {"title": "在线投票", "lead": "按限票数投给候选人。"},
            {"title": "结果公示", "lead": "管理端与门户可查看得票。"},
            {"title": "评选公告", "lead": "安排与须知见公告栏。"},
        ],
    )


def _exam_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """在线考试：科目档案 + 题库组卷作答（无单据/收藏）。"""
    from app.bake.features.exam import scan_exam_skin

    skin = scan_exam_skin(f"{title}\n{proposal_text}")
    app = product_name_from_title(title)
    fields = [
        {"key": "title", "label": "科目名称", "type": "string"},
        {"key": "author", "label": "开课单位", "type": "string"},
        {"key": "isbn", "label": "说明", "type": "textarea"},
        {"key": "category", "label": "分类", "type": "select"},
        {"key": "stock", "label": "开放", "type": "number"},
    ]
    schema: dict[str, Any] = {
        "version": 1,
        "title": title,
        "capabilities": list(DOMAIN_CAPABILITIES["DOM-EXAM"]),
        "roles": {
            "user": {"id": "user", "label": "考生"},
            "admin": {"id": "admin", "label": "教务主管（总管）"},
            "subadmin": {"id": "subadmin", "label": "教务员"},
        },
        "entities": {
            "archive": {
                "key": "exam_subject",
                "label": "考试科目",
                "labelPlural": "考试科目",
                "fields": fields,
                "stockDisplay": "toggle",
            }
        },
        "menus": {
            "admin": [
                {"key": "dashboard", "label": "工作台"},
                {"key": "archive", "label": "科目管理", "superOnly": True},
                {"key": "category", "label": category_menu_label(fields), "superOnly": True},
                {"key": "users", "label": "用户管理", "superOnly": True},
                {"key": "content", "label": "公告管理", "superOnly": True},
            ],
            "user": [
                {"key": "archive", "label": "考试科目"},
                {"key": "content", "label": "公告"},
                {"key": "profile", "label": "个人资料"},
            ],
        },
        "labels": {
            "appName": app,
            "authEyebrow": "在线考试",
            "authLead": "验证码登录；浏览考试科目，参加已发布试卷并自动判分。",
            "authPoints": ["验证码登录", "题库与组卷", "在线作答与判分"],
            "registerRoleHint": "注册后可参加已发布考试",
            "noticePageTitle": "考试公告",
            "noticePageLead": "考试安排与须知，点击条目阅读全文。",
            "messagesPageLead": "成绩与系统通知。",
        },
        "seeds": {
            "noticeTitle": "考试须知",
            "noticeBody": "请独立完成作答；客观题自动判分，主观题按关键词/正则自动判分。",
        },
        "examSkin": skin,
    }
    return _with_portal_banners(
        schema,
        [
            {"title": "考试科目", "lead": "按分类浏览开放科目与说明。"},
            {"title": "在线作答", "lead": "选择已发布试卷开考，提交后自动判分。"},
            {"title": "成绩查阅", "lead": "查看本人历史成绩与得分明细。"},
            {"title": "考试公告", "lead": "安排与须知见公告栏。"},
        ],
    )
