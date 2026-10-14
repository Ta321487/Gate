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
    """影视点播：商业默认；校园媒资 / 点播课分档。"""
    from app.bake.features.user_publish import scan_publish_review, scan_user_publish
    from app.bake.scene_scan import media_product_kind

    kind = media_product_kind(title, proposal_text)
    from app.bake.schema.kind_label_packs import media_label_pack

    p = media_label_pack(kind)
    noun, plural = p["noun"], p["plural"]
    author_lab, cat_lab = p["author_lab"], p["cat_lab"]
    brow, user, admin = p["eyebrow"], p["user"], p["admin"]
    lead, notice = p["lead"], p["notice"]
    banner_lead, menu_u, fav_lead = p["banner_lead"], p["menu_u"], p["fav_lead"]
    blob = f"{title}\n{proposal_text}"
    user_publish = scan_user_publish(blob, domain="DOM-MEDIA") or scan_publish_review(blob)
    if user_publish:
        lead = lead.rstrip("。") + "；开题点名投稿时可上传片源链接。"
    return _with_portal_banners(
        archive_favorites_schema(
            title,
            domain="DOM-MEDIA",
            user_role_id="user",
            user_label=user,
            admin_label=admin,
            subadmin_label="运营编辑",
            archive_key="media",
            archive_label=noun,
            archive_plural=plural,
            archive_fields=[
                {"key": "title", "label": p["title_field"], "type": "string"},
                {"key": "author", "label": author_lab, "type": "string"},
                {"key": "isbn", "label": "播放链接", "type": "url"},
                {"key": "durationSec", "label": "时长(秒)", "type": "number"},
                {"key": "category", "label": cat_lab, "type": "select"},
                {"key": "stock", "label": "可点播", "type": "number"},
            ],
            archive_menu_admin=f"{plural}管理" if kind == "coursevod" else "片单管理",
            archive_menu_user=menu_u,
            users_menu="用户管理",
            auth_eyebrow=brow,
            auth_lead=lead,
            auth_points=["验证码登录", f"{p['points_mid']}检索与播放", "收藏想看"]
            + (["上传投稿"] if user_publish else []),
            register_hint="注册后可浏览并收藏" + ("、投稿" if user_publish else ""),
            notice_title=p["notice_title"],
            notice_body=notice,
            notice_page_title="平台公告",
            notice_page_lead="上新与维护通知，点击条目阅读全文。",
            favorites_page_lead=fav_lead,
            play_url_field="isbn",
            stock_display="toggle",
            soft_delete=True,
            user_publish=user_publish,
        ),
        [
            {"title": p["hot_banner"], "lead": banner_lead},
            {"title": "收藏想看", "lead": fav_lead},
            {"title": "平台公告", "lead": "上新与维护通知见公告栏。"},
            {"title": "猜你喜欢", "lead": "根据浏览偏好推荐内容。"},
            {"title": "分类点播", "lead": "按类型快速找到想看的内容。"},
        ],
    )

def _music_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """在线音乐：商业默认；校园曲库 / 点歌台分档。"""
    from app.bake.features.user_publish import scan_user_publish
    from app.bake.scene_scan import music_product_kind

    kind = music_product_kind(title, proposal_text)
    from app.bake.schema.kind_label_packs import music_label_pack

    p = music_label_pack(kind)
    brow, user, admin = p["eyebrow"], p["user"], p["admin"]
    lead, notice = p["lead"], p["notice"]
    banner_lead, cat_lab = p["banner_lead"], p["cat_lab"]
    user_publish = scan_user_publish(f"{title}\n{proposal_text}", domain="DOM-MUSIC")
    if user_publish:
        lead = lead.rstrip("。") + "；开题点名时可上传曲目链接。"
    return _with_portal_banners(
        archive_favorites_schema(
            title,
            domain="DOM-MUSIC",
            user_role_id="user",
            user_label=user,
            admin_label=admin,
            subadmin_label="运营编辑",
            archive_key="track",
            archive_label="歌曲",
            archive_plural="曲库",
            archive_fields=[
                {"key": "title", "label": "歌名", "type": "string"},
                {"key": "author", "label": "歌手/专辑", "type": "string"},
                {"key": "isbn", "label": "播放链接", "type": "url"},
                {"key": "durationSec", "label": "时长(秒)", "type": "number"},
                {"key": "category", "label": cat_lab, "type": "select"},
                {"key": "stock", "label": "可播放", "type": "number"},
            ],
            archive_menu_admin="曲库管理",
            archive_menu_user="曲库检索",
            users_menu="用户管理",
            auth_eyebrow=brow,
            auth_lead=lead,
            auth_points=["验证码登录", "曲库检索与播放", "收藏喜欢"]
            + (["上传曲目"] if user_publish else []),
            register_hint="注册后可浏览曲库并收藏" + ("、上传" if user_publish else ""),
            notice_title=p["notice_title"],
            notice_body=notice,
            notice_page_title="平台公告",
            # 勿写「歌单」：开题常把独立歌单/协作编辑标非本期，营销「歌单」易被 QA 当成范围冲突
            notice_page_lead="曲库上新、维护窗口与试听须知，点击条目阅读全文。",
            favorites_page_lead="收藏喜欢的歌曲，方便下次回听。",
            play_url_field="isbn",
            stock_display="toggle",
            soft_delete=True,
            user_publish=user_publish,
        ),
        [
            {"title": "热门曲目", "lead": banner_lead},
            {"title": "收藏喜欢", "lead": "感兴趣的歌曲一键收藏，方便下次回听。"},
            {"title": "平台公告", "lead": "上新与维护通知见公告栏。"},
            {"title": "猜你喜欢", "lead": "根据听歌偏好推荐曲目。"},
            {"title": p["browse_banner"], "lead": "按分区快速找到想听的歌。"},
        ],
    )

def _forum_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """论坛：校园 BBS 默认；表白墙 / 社区分档。"""
    from app.bake.scene_scan import forum_product_kind, scene_for

    kind = forum_product_kind(title, proposal_text)
    community = scene_for("DOM-FORUM", title, proposal_text) == "community" or kind == "community"
    wall = kind == "wall"
    if wall:
        brow, lead = (
            "表白墙",
            "验证码登录；在表白墙/树洞发帖，跟帖回复经版主审核后展示。",
        )
        banner_lead = "表白、树洞、寻物墙分类浏览；文明发言。"
        notice = "请文明发言；回复经版主审核后展示。禁止人身攻击与广告。"
        notice_t = "表白墙公约"
    elif community:
        brow, lead = (
            "兴趣社区",
            "验证码登录；在邻里版块发帖，跟帖回复经版主审核后展示。",
        )
        banner_lead = "邻里互助、二手闲置、活动通知分类浏览。"
        notice = "请文明发帖；广告与人身攻击帖将被下架。"
        notice_t = "社区公约"
    else:
        brow, lead = (
            "校园论坛",
            "验证码登录；在校园版块发帖，跟帖回复经版主审核后展示。",
        )
        banner_lead = "学习交流、校园生活、二手信息分类浏览。"
        notice = "请文明讨论；回复经版主审核后展示。"
        notice_t = "社区公约"
    schema = _with_portal_banners(
        archive_ticket_schema(
            title,
            domain="DOM-FORUM",
            user_role_id="user",
            user_label="居民" if community and not wall else "师生",
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
            auth_eyebrow=brow,
            auth_lead=lead,
            auth_points=["验证码登录", "发帖与检索", "富文本回复与楼中楼"],
            register_hint="注册后可发帖并回复",
            notice_title=notice_t,
            notice_body=notice,
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
            {"title": "热门板块", "lead": banner_lead},
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
    """博客：个人站默认；校园院刊 / 记者站稿件分档。

    上架/下架走 softDelete（shelfCopy：在架/已下架），不再叠一层 stock 开关，
    避免「可阅读/已阅读」与软删文案打架、看起来像资讯 CMS。
    """
    from app.bake.features.user_publish import scan_publish_review, scan_user_publish
    from app.bake.scene_scan import blog_product_kind

    kind = blog_product_kind(title, proposal_text)
    from app.bake.schema.kind_label_packs import blog_label_pack

    bp = blog_label_pack(kind)
    brow, user, admin = bp["eyebrow"], bp["user"], bp["admin"]
    lead, notice = bp["lead"], bp["notice"]
    banner_lead = bp["banner_lead"]
    cat_lab, article_lab = bp["cat_lab"], bp["article_lab"]
    blob = f"{title}\n{proposal_text}"
    user_publish = scan_user_publish(blob, domain="DOM-BLOG") or scan_publish_review(blob)
    if user_publish:
        lead = lead.rstrip("。") + "；开题点名投稿时可自行发布文稿。"
        notice = notice.rstrip("。") + "；用户投稿即时可见，违规由管理员下架。"
    return _with_portal_banners(
        archive_favorites_schema(
            title,
            domain="DOM-BLOG",
            user_role_id="user",
            user_label=user,
            admin_label=admin,
            subadmin_label="编辑",
            archive_key="article",
            archive_label=article_lab,
            archive_plural=article_lab,
            archive_fields=[
                {"key": "title", "label": "标题", "type": "string"},
                {"key": "author", "label": "作者", "type": "string"},
                {"key": "summary", "label": "摘要", "type": "textarea"},
                {"key": "isbn", "label": "正文", "type": "richtext"},
                {"key": "category", "label": cat_lab, "type": "select"},
                {"key": "stock", "label": "在架", "type": "hidden"},
            ],
            archive_menu_admin=f"{article_lab}管理",
            archive_menu_user=f"{article_lab}检索",
            users_menu="用户管理",
            auth_eyebrow=brow,
            auth_lead=lead,
            auth_points=["验证码登录", f"{article_lab}检索与阅读", "收藏订阅"]
            + (["在线投稿"] if user_publish else []),
            register_hint=f"注册后可浏览{article_lab}并收藏"
            + ("、投稿" if user_publish else ""),
            notice_title="投稿须知" if kind == "press" or user_publish else "阅读须知",
            notice_body=notice,
            notice_page_title="站点公告",
            notice_page_lead="上新与征稿通知，点击条目阅读全文。",
            favorites_page_lead=f"收藏喜欢的{article_lab}，方便回看。",
            body_field="isbn",
            stock_display="hidden",
            soft_delete=True,
            user_publish=user_publish,
        ),
        [
            {"title": f"最新{article_lab}", "lead": banner_lead},
            {"title": "收藏订阅", "lead": f"喜欢的{article_lab}一键收藏，方便回看。"},
            {"title": "站点公告", "lead": "上新与征稿通知见公告栏。"},
            {"title": "猜你喜欢", "lead": "根据阅读偏好推荐内容。"},
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
            "noticeBody": "请如实填写；每人每卷限填一次。",
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
            "noticeBody": "下载将记入台账；按权限开放附件下载。",
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
            "noticeBody": "请公正投票；每人按活动限票数投给不同候选人。",
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
            "authLead": "验证码登录；浏览考试科目，参加已发布试卷。客观题交卷自动判分，主观题由教务主管阅卷。",
            "authPoints": ["验证码登录", "题库与组卷", "在线作答与判分"],
            "registerRoleHint": "注册后可参加已发布考试",
            "noticePageTitle": "考试公告",
            "noticePageLead": "考试安排与须知，点击条目阅读全文。",
            "messagesPageLead": "成绩与系统通知。",
        },
        "seeds": {
            "noticeTitle": "考试须知",
            "noticeBody": "请独立完成作答；客观题自动判分，主观题由教务主管阅卷后出总分。",
        },
        "examSkin": skin,
    }
    return _with_portal_banners(
        schema,
        [
            {"title": "考试科目", "lead": "按分类浏览开放科目与说明。"},
            {"title": "在线作答", "lead": "选择已发布试卷开考；客观题自动判分，主观题待教务主管阅卷。"},
            {"title": "成绩查阅", "lead": "查看本人历史成绩与得分明细。"},
            {"title": "考试公告", "lead": "安排与须知见公告栏。"},
        ],
    )
