"""内容 / 媒资 / 社区域 builder。"""

from __future__ import annotations

from typing import Any

from app.bake.schema.shells import (
    _with_portal_banners,
    archive_favorites_schema,
    archive_ticket_schema,
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
            notice_body="片源仅供学习演示；请文明观影，勿传播未授权内容。",
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
            notice_body="曲源仅供学习演示；请尊重版权，勿传播未授权内容。",
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
    return _with_portal_banners(
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
            notice_body="文章仅供学习演示；转载请注明出处。内容由主编维护发布。",
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
