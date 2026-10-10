"""内容组加厚（§1.8）：archive 浏览壳上的通识钉齐与域皮。

C-00：脚手架（CONTENT_DOMAINS + 注册点）。
C-01：通识——阅读数 / 热门排行 / 个人足迹 / 标题搜索。
C-02：FORUM 运营——精华置顶 / 锁定 / 草稿 / 移版 / 发帖上限 / 审后可见 / 版块公告。
C-03：FORUM 互动治理——楼中楼 / @提醒 / 禁言到期 / 举报通知 / 评论点赞 /
      敏感词 / 版主 / 评论折叠 / 操作日志 / 举报时效。
C-04：BLOG 域皮——订阅与订阅信 / 定时发撤 / 归档 / 系列文 / 原创声明 /
      作者主页 / 评论通知 / 密码访问 / 友情链接 / 订阅数。
C-05：MEDIA 域皮——进度 / 选集完播 / 海报墙 / 播放榜 / 下架原因 /
      分集通知 / 定时发布叠 / 分享码 / 片单说明。
C-06：MUSIC 域皮——歌手专辑筛 / 歌单公开私密 / 歌词 / 翻唱 /
      收藏夹分组 / 分享码 / 音质文案 / 下架原因叠。
C-07：DOCLIB 域皮——下载记录 / 预览 / 权限角色 / 章节目录 / 版本 /
      限额 / 审核 / 水印 / 标签云 / 试读说明 / 纠错 / 侵权投诉。
C-08：能力岛加深——仅当已挂对应 cap（points/wallet/content_report/userPublish 等）；
      未挂则无旗/无按钮/无扣点入口。
C-09：扫尾对照地图「本组待补」清零。

硬约束
------
- 只挂 CONTENT_DOMAINS = MEDIA / MUSIC / FORUM / BLOG / DOCLIB。
- 不碰 §1.6 交易、§1.7 预约、§1.9 互动；婚恋举报等归邻组。
- Store 主战场 ArchiveStore；论坛跟帖辅 TicketStore；辅 Message / Favorites /
  ItemComment / DemoScheduleJobs。
- 热门=计数排序，≠协同过滤；足迹禁止第二套表（复用 browse_history）。
- 楼中楼仅一层；敏感词≠云审核；禁言到期复用 post_mute。
- 点赞/举报/禁言/积分等仅 cap 已挂时加深（C-08），禁止因「论坛常见」永远开。
- 精华/置顶≠推荐引擎；转码 / CDN / 弹幕 / 真支付 / 版权结算 / 片单协作 /
  协同过滤 / RAG 冒充文库 / 实时聊天室 SDK → 不支持，不进待补。
"""

from __future__ import annotations

import re
from typing import Any

CONTENT_DOMAINS = frozenset(
    {
        "DOM-MEDIA",
        "DOM-MUSIC",
        "DOM-FORUM",
        "DOM-BLOG",
        "DOM-DOCLIB",
    }
)

# C-01：足迹域默认 MEDIA/MUSIC/BLOG（FORUM/DOCLIB 可选，本批不硬挂）
_BROWSE_HISTORY_DOMAINS = frozenset({"DOM-MEDIA", "DOM-MUSIC", "DOM-BLOG"})
# C-01：标题搜索 FORUM/BLOG 为主，五域可叠
_TITLE_SEARCH_DOMAINS = frozenset(CONTENT_DOMAINS)

_FORUM_DAILY_POST_LIMIT_DEFAULT = 10

_CONTENT_VIEW_COLS: list[tuple[str, str]] = [
    ("view_count", "INT NOT NULL DEFAULT 0"),
]
# C-01 下载计数 + C-07 域皮列（预览≠转码云；试读≠DRM；积分下载归 C-08）
_CONTENT_DOCLIB_COLS: list[tuple[str, str]] = [
    ("download_count", "INT NOT NULL DEFAULT 0"),
    ("preview_url", "VARCHAR(512) NOT NULL DEFAULT ''"),
    ("download_roles", "VARCHAR(255) NOT NULL DEFAULT ''"),
    ("trial_read_note", "TEXT NULL"),
    ("watermark_on", "TINYINT NOT NULL DEFAULT 0"),
    ("needs_download_audit", "TINYINT NOT NULL DEFAULT 0"),
    ("daily_download_limit", "INT NOT NULL DEFAULT 0"),
    # C-08：积分/点券下载价（未挂 points 时列为 0，无扣点入口）
    ("download_cost_points", "INT NOT NULL DEFAULT 0"),
]
_DOCLIB_CHAPTER_DDL = """
CREATE TABLE IF NOT EXISTS doc_chapter (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  item_id BIGINT NOT NULL,
  title VARCHAR(128) NOT NULL,
  anchor VARCHAR(64) NOT NULL DEFAULT '',
  sort_ord INT NOT NULL DEFAULT 0,
  KEY idx_dc_item (item_id, sort_ord, id)
);
"""
_DOCLIB_VERSION_DDL = """
CREATE TABLE IF NOT EXISTS doc_version (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  item_id BIGINT NOT NULL,
  version_no VARCHAR(32) NOT NULL,
  note VARCHAR(512) NOT NULL DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_dv_item (item_id, id)
);
"""
_DOCLIB_FEEDBACK_DDL = """
CREATE TABLE IF NOT EXISTS doc_feedback (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  item_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  kind VARCHAR(16) NOT NULL,
  body VARCHAR(1000) NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'pending',
  handle_note VARCHAR(512) NOT NULL DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  handled_at DATETIME NULL,
  KEY idx_df_item (item_id, id),
  KEY idx_df_status (status, id)
);
"""
_DOCLIB_AUDIT_DDL = """
CREATE TABLE IF NOT EXISTS doc_download_request (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  item_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'pending',
  handle_note VARCHAR(512) NOT NULL DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  handled_at DATETIME NULL,
  KEY idx_ddr_user (username, status, id),
  KEY idx_ddr_item (item_id, id)
);
"""
_DOCLIB_TAG_DDL = """
CREATE TABLE IF NOT EXISTS doc_tag (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL,
  use_count INT NOT NULL DEFAULT 0,
  UNIQUE KEY uk_dt_name (name)
);
CREATE TABLE IF NOT EXISTS doc_item_tag (
  item_id BIGINT NOT NULL,
  tag_id BIGINT NOT NULL,
  PRIMARY KEY (item_id, tag_id),
  KEY idx_dit_tag (tag_id)
);
"""
_DOCLIB_DAILY_DOWNLOAD_LIMIT_DEFAULT = 20
_FORUM_POST_COLS: list[tuple[str, str]] = [
    ("pin_top", "TINYINT NOT NULL DEFAULT 0"),
    ("essence", "TINYINT NOT NULL DEFAULT 0"),
    ("locked", "TINYINT NOT NULL DEFAULT 0"),
]
_FORUM_CATEGORY_COLS: list[tuple[str, str]] = [
    ("section_notice", "VARCHAR(512) NOT NULL DEFAULT ''"),
]
# C-03：跟帖楼中楼 / 评论点赞 / 举报时效
_FORUM_TICKET_COLS: list[tuple[str, str]] = [
    ("parent_ticket_id", "BIGINT NULL"),
    ("like_count", "INT NOT NULL DEFAULT 0"),
]
_ITEM_COMMENT_GOV_COLS: list[tuple[str, str]] = [
    ("parent_id", "BIGINT NULL"),
    ("like_count", "INT NOT NULL DEFAULT 0"),
    ("followers_only", "TINYINT NOT NULL DEFAULT 0"),
]
_USER_FOLLOW_DDL = """
CREATE TABLE IF NOT EXISTS user_follow (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  follower VARCHAR(64) NOT NULL,
  followee VARCHAR(64) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_uf_pair (follower, followee),
  KEY idx_uf_followee (followee)
);
"""
_DEFAULT_REPORT_REASONS = ["垃圾广告", "人身攻击", "侵权抄袭", "违法违规", "其他"]
_ESSENCE_POINTS_REWARD_DEFAULT = 5
_POINTS_CHECK_IN_AMOUNT_DEFAULT = 10
_REPORT_GOV_COLS: list[tuple[str, str]] = [
    ("handle_deadline_at", "DATETIME NULL"),
]
# C-04：BLOG 域皮列（定时发撤复用语义名 publish_at/unpublish_at，≠交易 shelf_on）
_BLOG_POST_COLS: list[tuple[str, str]] = [
    ("publish_at", "DATETIME NULL"),
    ("unpublish_at", "DATETIME NULL"),
    ("series_id", "BIGINT NULL"),
    ("series_ord", "INT NOT NULL DEFAULT 0"),
    ("origin_kind", "VARCHAR(16) NOT NULL DEFAULT 'original'"),
    ("access_password", "VARCHAR(64) NOT NULL DEFAULT ''"),
]
_CATEGORY_FOLLOW_DDL = """
CREATE TABLE IF NOT EXISTS category_follow (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  category_id BIGINT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_cf_user_cat (username, category_id),
  KEY idx_cf_cat (category_id)
);
"""
_BLOG_FRIEND_LINK_DDL = """
CREATE TABLE IF NOT EXISTS blog_friend_link (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(128) NOT NULL,
  url VARCHAR(512) NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  enabled TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_bfl_sort (enabled, sort_order, id)
);
"""
# C-05：MEDIA 域皮列（定时发撤叠 C-04 列名；播放榜≠协同过滤）
_MEDIA_POST_COLS: list[tuple[str, str]] = [
    ("play_count", "INT NOT NULL DEFAULT 0"),
    ("off_shelf_reason", "VARCHAR(255) NOT NULL DEFAULT ''"),
    ("share_code", "VARCHAR(32) NOT NULL DEFAULT ''"),
    ("publish_at", "DATETIME NULL"),
    ("unpublish_at", "DATETIME NULL"),
]
_MEDIA_EPISODE_DDL = """
CREATE TABLE IF NOT EXISTS media_episode (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  item_id BIGINT NOT NULL,
  title VARCHAR(128) NOT NULL,
  sort_ord INT NOT NULL DEFAULT 0,
  media_url VARCHAR(512) NOT NULL DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_me_item (item_id, sort_ord, id)
);
"""
_MEDIA_PLAY_PROGRESS_DDL = """
CREATE TABLE IF NOT EXISTS media_play_progress (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  item_id BIGINT NOT NULL,
  episode_id BIGINT NOT NULL DEFAULT 0,
  position_sec INT NOT NULL DEFAULT 0,
  completed TINYINT NOT NULL DEFAULT 0,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_mpp_user_item_ep (username, item_id, episode_id),
  KEY idx_mpp_item (item_id)
);
"""
# C-06：MUSIC 域皮列（播放/分享/下架叠 C-05；歌手字段可与 archive_columns.artist 并存）
_MUSIC_POST_COLS: list[tuple[str, str]] = [
    ("play_count", "INT NOT NULL DEFAULT 0"),
    ("off_shelf_reason", "VARCHAR(255) NOT NULL DEFAULT ''"),
    ("share_code", "VARCHAR(32) NOT NULL DEFAULT ''"),
    ("artist", "VARCHAR(100) NOT NULL DEFAULT ''"),
    ("album", "VARCHAR(128) NOT NULL DEFAULT ''"),
    ("lyrics", "TEXT NULL"),
    ("is_cover", "TINYINT NOT NULL DEFAULT 0"),
]
_DEFAULT_SENSITIVE_WORDS = ["违禁", "广告引流", "加微信", "代刷"]
_REPORT_HANDLE_DAYS_DEFAULT = 3
_COMMENT_FOLD_AFTER_DEFAULT = 3


def _live_schema(spec: dict[str, Any]) -> dict[str, Any]:
    schema = spec.get("schema")
    if not isinstance(schema, dict):
        schema = {}
        spec["schema"] = schema
    return schema


def _add_feature(spec: dict[str, Any], name: str) -> None:
    feats = spec.get("features")
    if not isinstance(feats, list):
        feats = []
        spec["features"] = feats
    if name not in feats:
        feats.append(name)


def _ensure_archive_field(archive: dict[str, Any], field: dict[str, Any]) -> None:
    fields = archive.get("fields")
    if not isinstance(fields, list):
        fields = []
        archive["fields"] = fields
    key = str(field.get("key") or "")
    if not key:
        return
    for f in fields:
        if isinstance(f, dict) and f.get("key") == key:
            return
    fields.append(field)


def _valid_ident(name: str | None) -> bool:
    t = (name or "").strip()
    return bool(t and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t))


def ensure_content_thicken_sql(
    sql: str,
    *,
    domain: str | None,
    item_table: str | None = None,
    category_table: str | None = None,
    ticket_table: str | None = None,
) -> str:
    """五内容域通识列；FORUM/BLOG/MEDIA/MUSIC 叠域皮列；非本组原样返回。"""
    from app.bake.sql.fragments import _CREATE_TABLE_RE, _inject_missing_columns

    if (domain or "") not in CONTENT_DOMAINS:
        return sql
    item = (item_table or "").strip()
    cat = (category_table or "").strip()
    ticket = (ticket_table or "").strip()
    if not _valid_ident(item):
        return sql
    doclib = (domain or "") == "DOM-DOCLIB"
    forum = (domain or "") == "DOM-FORUM"
    blog = (domain or "") == "DOM-BLOG"
    media = (domain or "") == "DOM-MEDIA"
    music = (domain or "") == "DOM-MUSIC"

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        tl = table.lower()
        if tl == item.lower():
            cols = list(_CONTENT_VIEW_COLS)
            if doclib:
                cols.extend(_CONTENT_DOCLIB_COLS)
            if forum:
                cols.extend(_FORUM_POST_COLS)
            if blog:
                cols.extend(_BLOG_POST_COLS)
            if media:
                cols.extend(_MEDIA_POST_COLS)
            if music:
                cols.extend(_MUSIC_POST_COLS)
            body = _inject_missing_columns(body, cols)
        elif forum and _valid_ident(cat) and tl == cat.lower():
            body = _inject_missing_columns(body, list(_FORUM_CATEGORY_COLS))
        elif forum and _valid_ident(ticket) and tl == ticket.lower():
            body = _inject_missing_columns(body, list(_FORUM_TICKET_COLS))
        elif tl == "item_comment" and (forum or blog):
            body = _inject_missing_columns(body, list(_ITEM_COMMENT_GOV_COLS))
        elif tl == "content_report" and forum:
            body = _inject_missing_columns(body, list(_REPORT_GOV_COLS))
        else:
            return m.group(0)
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(repl, sql)
    if blog:
        if "CREATE TABLE IF NOT EXISTS category_follow" not in out:
            out = out.rstrip() + "\n\n" + _CATEGORY_FOLLOW_DDL.strip() + "\n"
        if "CREATE TABLE IF NOT EXISTS blog_friend_link" not in out:
            out = out.rstrip() + "\n\n" + _BLOG_FRIEND_LINK_DDL.strip() + "\n"
    if media:
        if "CREATE TABLE IF NOT EXISTS category_follow" not in out:
            out = out.rstrip() + "\n\n" + _CATEGORY_FOLLOW_DDL.strip() + "\n"
        if "CREATE TABLE IF NOT EXISTS media_episode" not in out:
            out = out.rstrip() + "\n\n" + _MEDIA_EPISODE_DDL.strip() + "\n"
        if "CREATE TABLE IF NOT EXISTS media_play_progress" not in out:
            out = out.rstrip() + "\n\n" + _MEDIA_PLAY_PROGRESS_DDL.strip() + "\n"
    if music:
        if "CREATE TABLE IF NOT EXISTS media_play_progress" not in out:
            out = out.rstrip() + "\n\n" + _MEDIA_PLAY_PROGRESS_DDL.strip() + "\n"
    if doclib:
        for ddl, needle in (
            (_DOCLIB_CHAPTER_DDL, "doc_chapter"),
            (_DOCLIB_VERSION_DDL, "doc_version"),
            (_DOCLIB_FEEDBACK_DDL, "doc_feedback"),
            (_DOCLIB_AUDIT_DDL, "doc_download_request"),
            (_DOCLIB_TAG_DDL, "doc_tag"),
        ):
            if f"CREATE TABLE IF NOT EXISTS {needle}" not in out and needle not in out:
                out = out.rstrip() + "\n\n" + ddl.strip() + "\n"
    # C-08：互关浅表（评论仅粉丝可见）；FORUM/BLOG 均可有
    if forum or blog:
        if "CREATE TABLE IF NOT EXISTS user_follow" not in out:
            out = out.rstrip() + "\n\n" + _USER_FOLLOW_DDL.strip() + "\n"
    return out


def _nail_browse_history(spec: dict[str, Any], schema: dict[str, Any], thicken: dict[str, Any]) -> None:
    caps_list = list(spec.get("capabilities") or [])
    if "browse_history" in caps_list or "archive" not in caps_list:
        thicken["browseHistory"] = "browse_history" in caps_list
        return
    caps_list.append("browse_history")
    spec["capabilities"] = caps_list
    schema["capabilities"] = caps_list
    try:
        from app.bake.features.ux_scan import attach_ux_schema
        from app.bake.gate_contracts import merge_ux_gate

        attach_ux_schema(schema, caps_list)
        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_ux_gate(gate, caps_list)
    except Exception:
        pass
    thicken["browseHistory"] = True
    _add_feature(spec, "个人浏览历史")


def _apply_forum_ops(
    spec: dict[str, Any],
    schema: dict[str, Any],
    archive: dict[str, Any],
    thicken: dict[str, Any],
    labels: dict[str, Any],
) -> None:
    """C-02：仅 DOM-FORUM 域默认运营钉齐。"""
    # 精华 / 置顶（复用 pin_top；≠推荐引擎）
    _ensure_archive_field(
        archive, {"key": "pinTop", "label": "置顶", "type": "boolean"}
    )
    _ensure_archive_field(
        archive, {"key": "essence", "label": "精华", "type": "boolean"}
    )
    labels.setdefault("pinTopLabel", "置顶")
    labels.setdefault("pinTopHint", "置顶帖在列表优先展示，不是推荐引擎。")
    labels.setdefault("essenceLabel", "精华")
    labels.setdefault("essenceHint", "精华帖由管理员标记，列表优先展示。")
    thicken["pinTop"] = True
    thicken["essence"] = True
    _add_feature(spec, "精华帖置顶")

    # 锁定
    _ensure_archive_field(
        archive, {"key": "locked", "label": "锁定", "type": "boolean"}
    )
    labels.setdefault("lockedLabel", "锁定")
    labels.setdefault("lockedHint", "锁定后不能再跟帖回复。")
    labels.setdefault("lockedReplyBlocked", "该帖已锁定，暂时不能回复。")
    thicken["locked"] = True
    _add_feature(spec, "帖子锁定")

    # 草稿箱
    labels.setdefault("draftBoxPageTitle", "草稿箱")
    labels.setdefault("draftBoxPageLead", "先存草稿，写好再发布。")
    labels.setdefault("draftStatusLabel", "草稿")
    labels.setdefault("saveDraftLabel", "存草稿")
    labels.setdefault("publishFromDraftLabel", "发布草稿")
    thicken["draftBox"] = True
    _add_feature(spec, "帖子草稿箱")

    # 移版
    labels.setdefault("moveCategoryLabel", "移动版块")
    labels.setdefault("moveCategoryHint", "把帖子改到其他版块。")
    thicken["moveCategory"] = True
    _add_feature(spec, "帖子移动版块")

    # 每日发帖上限
    if not int(schema.get("forumDailyPostLimit") or 0):
        schema["forumDailyPostLimit"] = _FORUM_DAILY_POST_LIMIT_DEFAULT
    labels.setdefault("dailyPostLimitLabel", "每日发帖上限")
    labels.setdefault(
        "dailyPostLimitHint",
        f"每人每天最多发 {int(schema['forumDailyPostLimit'])} 帖（草稿不计入）。",
    )
    thicken["dailyPostLimit"] = True
    _add_feature(spec, "论坛每日发帖上限")

    # 审后可见（复用 publishReview 管道）
    archive["publishReview"] = True
    if not archive.get("userPublish"):
        archive["userPublish"] = True
    try:
        from app.bake.features.user_publish import _apply_publish_review_copy

        updated = _apply_publish_review_copy(dict(schema), archive)
        for k, v in (updated.get("labels") or {}).items():
            labels.setdefault(k, v)
        if isinstance(updated.get("seeds"), dict):
            seeds = schema.setdefault("seeds", {})
            if isinstance(seeds, dict):
                for k, v in updated["seeds"].items():
                    seeds.setdefault(k, v)
    except Exception:
        labels.setdefault(
            "publishTip",
            "提交后进入待审核，通过后才公开展示；驳回或下架可在「我的帖子」查看。",
        )
        labels.setdefault("publishSubmitLabel", "提交审核")
    thicken["publishReview"] = True
    _add_feature(spec, "发帖审后可见")

    # 版块公告
    labels.setdefault("sectionNoticeLabel", "版块公告")
    labels.setdefault("sectionNoticeHint", "进入该版块时展示的须知。")
    thicken["sectionNotice"] = True
    _add_feature(spec, "版块公告")


def _apply_forum_governance(
    spec: dict[str, Any],
    schema: dict[str, Any],
    thicken: dict[str, Any],
    labels: dict[str, Any],
) -> None:
    """C-03：FORUM 互动治理（楼中楼/@/禁言到期/举报通知/评论赞/敏感词/版主/折叠/审计/举报时效）。"""
    caps = list(spec.get("capabilities") or [])
    ents = schema.setdefault("entities", {})
    ticket = ents.get("ticket") if isinstance(ents.get("ticket"), dict) else {}
    if not isinstance(ticket, dict):
        ticket = {}
        ents["ticket"] = ticket

    # 楼中楼（复用 parent_ticket_id；仅一层）
    ticket["allowNestedReply"] = True
    labels.setdefault("nestedReplyLabel", "回复楼中楼")
    labels.setdefault("nestedReplyHint", "只能回复一层，不能再嵌套。")
    labels.setdefault("nestedReplyBlocked", "该回复下不能再盖楼。")
    thicken["nestedReply"] = True
    _add_feature(spec, "二级回复楼中楼")

    # @提醒
    labels.setdefault("mentionNotifyHint", "回复里写 @登录名，对方会收到站内信。")
    thicken["mentionNotify"] = True
    _add_feature(spec, "艾特提醒站内信")

    # 禁言到期（有 post_mute 时钉清扫）
    if "post_mute" in caps:
        labels.setdefault("muteExpireHint", "禁言到期后自动解除，可继续发言。")
        thicken["muteExpire"] = True
        _add_feature(spec, "禁言到期自动解除")

    # 举报结果通知 + 处理时效（有 content_report 时）
    if "content_report" in caps:
        labels.setdefault("reportResultNotifyTitle", "举报处理结果")
        labels.setdefault(
            "reportResultNotifyBody",
            "你提交的举报已处理，请查看处理说明。",
        )
        labels.setdefault("reportDeadlineLabel", "处理时限")
        labels.setdefault("reportOverdueLabel", "已超时")
        if not int(schema.get("reportHandleDays") or 0):
            schema["reportHandleDays"] = _REPORT_HANDLE_DAYS_DEFAULT
        thicken["reportResultNotify"] = True
        thicken["reportDeadline"] = True
        _add_feature(spec, "举报处理结果通知")
        _add_feature(spec, "论坛举报表处理时效")

    # 评论/跟帖点赞（浅计数）
    labels.setdefault("commentLikeLabel", "赞")
    labels.setdefault("commentLikedLabel", "已赞")
    thicken["commentLike"] = True
    _add_feature(spec, "评论点赞计数")

    # 敏感词
    if not isinstance(schema.get("sensitiveWords"), list) or not schema.get("sensitiveWords"):
        schema["sensitiveWords"] = list(_DEFAULT_SENSITIVE_WORDS)
    labels.setdefault("sensitiveWordBlocked", "内容含不宜发布的用语，请修改后再提交")
    labels.setdefault("sensitiveWordHint", "发布内容会经过站内词表检查。")
    thicken["sensitiveWords"] = True
    _add_feature(spec, "敏感词拦截提示")

    # 版主任命（复用 staff_post moderator）
    labels.setdefault("moderatorAppointLabel", "任命版主")
    labels.setdefault("moderatorAppointHint", "在用户管理里把岗位设为版主。")
    thicken["moderatorAppoint"] = True
    _add_feature(spec, "论坛版主任命")

    # 评论折叠
    if not int(schema.get("commentFoldAfter") or 0):
        schema["commentFoldAfter"] = _COMMENT_FOLD_AFTER_DEFAULT
    labels.setdefault("commentFoldMoreLabel", "展开更多回复")
    labels.setdefault("commentFoldLessLabel", "收起")
    thicken["commentFold"] = True
    _add_feature(spec, "评论折叠")

    # 精华/置顶操作日志
    labels.setdefault("pinEssenceAuditAction", "帖子运营标记")
    thicken["pinEssenceAudit"] = True
    _add_feature(spec, "帖子精华置顶操作日志")


def _apply_blog_skin(
    spec: dict[str, Any],
    schema: dict[str, Any],
    archive: dict[str, Any],
    thicken: dict[str, Any],
    labels: dict[str, Any],
) -> None:
    """C-04：仅 DOM-BLOG 域默认域皮（订阅≠推荐；定时走 DemoScheduleJobs；密码≠付费墙）。"""
    # 草稿箱（与 C-02 共用 draft 状态机）
    labels.setdefault("draftBoxPageTitle", "草稿箱")
    labels.setdefault("draftBoxPageLead", "先存草稿，写好再发布。")
    labels.setdefault("draftStatusLabel", "草稿")
    labels.setdefault("saveDraftLabel", "存草稿")
    labels.setdefault("publishFromDraftLabel", "发布草稿")
    thicken["draftBox"] = True
    if not archive.get("userPublish"):
        archive["userPublish"] = True
    _add_feature(spec, "博客草稿箱")

    # 专栏/分类订阅
    labels.setdefault("categoryFollowLabel", "订阅专栏")
    labels.setdefault("categoryUnfollowLabel", "取消订阅")
    labels.setdefault("categoryFollowHint", "订阅后，该专栏有新文章会站内信提醒。")
    labels.setdefault("categoryFollowerCountLabel", "订阅数")
    thicken["categoryFollow"] = True
    thicken["categoryFollowNotify"] = True
    thicken["categoryFollowerCount"] = True
    _add_feature(spec, "专栏分类订阅")

    # 定时发布 / 定时撤回
    _ensure_archive_field(
        archive, {"key": "publishAt", "label": "定时发布", "type": "datetime"}
    )
    _ensure_archive_field(
        archive, {"key": "unpublishAt", "label": "定时撤回", "type": "datetime"}
    )
    labels.setdefault("publishAtLabel", "定时发布")
    labels.setdefault("publishAtHint", "到点后自动公开；留空则立即按状态展示。")
    labels.setdefault("unpublishAtLabel", "定时撤回")
    labels.setdefault("unpublishAtHint", "到点后自动下架。")
    thicken["scheduledPublish"] = True
    thicken["scheduledUnpublish"] = True
    _add_feature(spec, "博客定时发布撤回")

    # 归档按年月
    labels.setdefault("archiveYearMonthLabel", "按年月归档")
    labels.setdefault("archiveYearMonthAllLabel", "全部月份")
    thicken["archiveYearMonth"] = True
    _add_feature(spec, "博客归档按年月")

    # 系列文
    _ensure_archive_field(
        archive, {"key": "seriesId", "label": "系列编号", "type": "number"}
    )
    _ensure_archive_field(
        archive, {"key": "seriesOrd", "label": "系列序号", "type": "number"}
    )
    labels.setdefault("seriesPrevLabel", "上一篇")
    labels.setdefault("seriesNextLabel", "下一篇")
    labels.setdefault("seriesHint", "同一系列编号的文章按序号串联。")
    thicken["seriesNav"] = True
    _add_feature(spec, "博客系列文")

    # 转载/原创
    _ensure_archive_field(
        archive,
        {
            "key": "originKind",
            "label": "原创声明",
            "type": "select",
            "options": [
                {"value": "original", "label": "原创"},
                {"value": "reprint", "label": "转载"},
            ],
        },
    )
    labels.setdefault("originKindLabel", "原创声明")
    labels.setdefault("originOriginalLabel", "原创")
    labels.setdefault("originReprintLabel", "转载")
    thicken["originKind"] = True
    _add_feature(spec, "转载原创声明")

    # 作者主页
    labels.setdefault("authorPageTitle", "作者主页")
    labels.setdefault("authorPageLead", "查看该作者发布的文章。")
    labels.setdefault("authorPageEntryLabel", "看作者")
    thicken["authorPage"] = True
    _add_feature(spec, "作者主页")

    # 评论通知作者
    labels.setdefault("commentAuthorNotifyTitle", "收到新评论")
    labels.setdefault("commentAuthorNotifyHint", "有人评论你的文章时会站内信提醒。")
    thicken["commentAuthorNotify"] = True
    _add_feature(spec, "博客评论站内信")

    # 密码访问
    _ensure_archive_field(
        archive, {"key": "accessPassword", "label": "访问口令", "type": "text"}
    )
    labels.setdefault("accessPasswordLabel", "访问口令")
    labels.setdefault("accessPasswordHint", "填写后访客需输入口令才能看正文（不是付费墙）。")
    labels.setdefault("accessPasswordPrompt", "请输入访问口令")
    labels.setdefault("accessPasswordUnlockLabel", "解锁")
    labels.setdefault("accessPasswordBlocked", "口令不正确")
    thicken["accessPassword"] = True
    _add_feature(spec, "博客文章密码访问")

    # 友情链接
    labels.setdefault("friendLinkPageTitle", "友情链接")
    labels.setdefault("friendLinkAdminTitle", "友情链接维护")
    labels.setdefault("friendLinkEmpty", "暂无友情链接")
    thicken["friendLinks"] = True
    _add_feature(spec, "博客友情链接")
    try:
        from app.bake.schema.menu_utils import ensure_menu

        menus = schema.setdefault("menus", {})
        admin = menus.setdefault("admin", [])
        ensure_menu(
            admin,
            "blog_friend_links",
            {"key": "blog_friend_links", "label": labels.get("friendLinkAdminTitle") or "友情链接维护"},
            before_key="categories",
        )
    except Exception:
        pass


def _apply_media_skin(
    spec: dict[str, Any],
    schema: dict[str, Any],
    archive: dict[str, Any],
    thicken: dict[str, Any],
    labels: dict[str, Any],
) -> None:
    """C-05：仅 DOM-MEDIA 域默认域皮（进度≠多端云同步；分享码只读链；弹幕/真支付不进）。"""
    # 专栏订阅 + 定时发撤（叠 C-04 机制）
    labels.setdefault("categoryFollowLabel", "订阅分类")
    labels.setdefault("categoryUnfollowLabel", "取消订阅")
    labels.setdefault("categoryFollowHint", "订阅后，该分类有新片或分集更新会站内信提醒。")
    labels.setdefault("categoryFollowerCountLabel", "订阅数")
    thicken["categoryFollow"] = True
    thicken["categoryFollowNotify"] = True
    thicken["categoryFollowerCount"] = True
    _add_feature(spec, "媒资分类订阅")

    _ensure_archive_field(
        archive, {"key": "publishAt", "label": "定时上架", "type": "datetime"}
    )
    _ensure_archive_field(
        archive, {"key": "unpublishAt", "label": "定时下架", "type": "datetime"}
    )
    labels.setdefault("publishAtLabel", "定时上架")
    labels.setdefault("publishAtHint", "到点后自动公开。")
    labels.setdefault("unpublishAtLabel", "定时下架")
    labels.setdefault("unpublishAtHint", "到点后自动下架。")
    thicken["scheduledPublish"] = True
    thicken["scheduledUnpublish"] = True
    _add_feature(spec, "媒资定时上下架")

    # 播放进度（按用户一条；完播标记）
    labels.setdefault("playProgressLabel", "播放进度")
    labels.setdefault("playProgressHint", "记住你看到哪，换设备不保证同步。")
    labels.setdefault("playProgressSaveLabel", "记下进度")
    labels.setdefault("episodeCompletedLabel", "已看完")
    labels.setdefault("episodeContinueLabel", "继续看")
    thicken["playProgress"] = True
    thicken["episodeCompleted"] = True
    _add_feature(spec, "播放进度记住")

    # 选集/分集
    labels.setdefault("episodeListTitle", "选集")
    labels.setdefault("episodeListEmpty", "暂无分集")
    labels.setdefault("episodeAdminTitle", "分集维护")
    labels.setdefault("episodeAddLabel", "新增分集")
    thicken["episodeList"] = True
    thicken["episodeUpdateNotify"] = True
    labels.setdefault("episodeUpdateNotifyTitle", "分集更新")
    labels.setdefault("episodeUpdateNotifyHint", "有新分集时，订阅该分类的用户会收到站内信。")
    _add_feature(spec, "影音选集分集")

    # 海报墙（强制 gallery）
    try:
        from app.bake.features.apply_thicken import _force_gallery

        _force_gallery(spec, schema)
    except Exception:
        caps = list(spec.get("capabilities") or [])
        if "gallery" not in caps:
            caps.append("gallery")
            spec["capabilities"] = caps
            schema["capabilities"] = caps
    labels.setdefault("posterWallTitle", "海报墙")
    labels.setdefault("posterWallLead", "按分类浏览封面海报。")
    thicken["posterWall"] = True
    thicken["gallery"] = True
    _add_feature(spec, "影音海报墙")

    # 播放次数排行（复用 pageHot；≠协同过滤）
    _ensure_archive_field(
        archive, {"key": "playCount", "label": "播放次数", "type": "number"}
    )
    labels.setdefault("playCountLabel", "播放次数")
    labels["hotRankPageLead"] = "按播放次数从高到低排列。"
    labels.setdefault("hotRankToggleLabel", "看热门")
    thicken["hotByPlay"] = True
    thicken["hotRank"] = True
    _add_feature(spec, "媒资播放次数排行")

    # 下架原因
    _ensure_archive_field(
        archive, {"key": "offShelfReason", "label": "下架原因", "type": "text"}
    )
    labels.setdefault("offShelfReasonLabel", "下架原因")
    labels.setdefault("offShelfReasonHint", "下架时可登记原因，便于复查。")
    thicken["offShelfReason"] = True
    _add_feature(spec, "媒资下架原因")

    # 片单分享码（只读链接口令；≠协作编辑）
    _ensure_archive_field(
        archive, {"key": "shareCode", "label": "分享码", "type": "text"}
    )
    labels.setdefault("shareCodeLabel", "分享码")
    labels.setdefault("shareCodeHint", "他人凭码可打开本片只读页，不是多人协作编辑。")
    labels.setdefault("shareCodeEntryLabel", "凭码打开")
    labels.setdefault("shareCodePrompt", "请输入分享码")
    labels.setdefault("shareCodeBlocked", "分享码无效")
    thicken["shareCode"] = True
    _add_feature(spec, "片单分享码")

    # 收藏夹分组（MEDIA 可叠）
    _apply_favorite_group_skin(spec, thicken, labels)


def _apply_favorite_group_skin(
    spec: dict[str, Any],
    thicken: dict[str, Any],
    labels: dict[str, Any],
) -> None:
    """C-06：收藏夹分组命名 + 歌单/片单公开私密（favorites 加深）。"""
    labels.setdefault("favoriteGroupLabel", "分组")
    labels.setdefault("favoriteGroupHint", "给收藏起个组名，方便整理歌单或片单。")
    labels.setdefault("favoriteGroupPlaceholder", "如：通勤、考试周")
    labels.setdefault("playlistPublicLabel", "公开歌单")
    labels.setdefault("playlistPrivateLabel", "仅自己可见")
    labels.setdefault("playlistVisibilityHint", "公开后他人可查看该分组收藏，不是多人协作编辑。")
    thicken["favoriteGroup"] = True
    thicken["playlistVisibility"] = True
    _add_feature(spec, "收藏夹分组与公开")


def _apply_music_skin(
    spec: dict[str, Any],
    schema: dict[str, Any],
    archive: dict[str, Any],
    thicken: dict[str, Any],
    labels: dict[str, Any],
) -> None:
    """C-06：仅 DOM-MUSIC 域默认域皮（音质≠真转码；版权结算不进）。"""
    # 歌手 / 专辑筛
    _ensure_archive_field(
        archive, {"key": "artist", "label": "歌手", "type": "text"}
    )
    _ensure_archive_field(
        archive, {"key": "album", "label": "专辑", "type": "text"}
    )
    labels.setdefault("artistLabel", "歌手")
    labels.setdefault("artistFilterPlaceholder", "按歌手筛选")
    labels.setdefault("albumLabel", "专辑")
    labels.setdefault("albumFilterPlaceholder", "按专辑筛选")
    thicken["artistAlbumFilter"] = True
    _add_feature(spec, "曲库歌手专辑筛选")

    # 歌词 / 翻唱
    _ensure_archive_field(
        archive, {"key": "lyrics", "label": "歌词", "type": "textarea"}
    )
    _ensure_archive_field(
        archive, {"key": "isCover", "label": "翻唱", "type": "boolean"}
    )
    labels.setdefault("lyricsLabel", "歌词")
    labels.setdefault("lyricsEmpty", "暂无歌词")
    labels.setdefault("coverMarkLabel", "翻唱")
    thicken["lyrics"] = True
    thicken["coverMark"] = True
    _add_feature(spec, "曲库歌词与翻唱")

    # 音质文案假切换（不真转码）
    labels.setdefault("audioQualityLabel", "音质")
    labels.setdefault("audioQualityHint", "仅界面文案切换，不会真转码音源。")
    labels.setdefault("audioQualityOptions", "标准,较高,无损")
    thicken["audioQualitySwitch"] = True
    _add_feature(spec, "曲库音质文案切换")

    # 叠 C-05：进度 / 播放榜 / 下架原因 / 分享码
    labels.setdefault("playProgressLabel", "播放进度")
    labels.setdefault("playProgressHint", "记住你听到哪，换设备不保证同步。")
    labels.setdefault("playProgressSaveLabel", "记下进度")
    labels.setdefault("episodeCompletedLabel", "已听完")
    labels.setdefault("episodeContinueLabel", "继续听")
    thicken["playProgress"] = True
    thicken["episodeCompleted"] = True
    _add_feature(spec, "播放进度记住")

    _ensure_archive_field(
        archive, {"key": "playCount", "label": "播放次数", "type": "number"}
    )
    labels.setdefault("playCountLabel", "播放次数")
    labels["hotRankPageLead"] = "按播放次数从高到低排列。"
    labels.setdefault("hotRankToggleLabel", "看热门")
    thicken["hotByPlay"] = True
    thicken["hotRank"] = True
    _add_feature(spec, "媒资播放次数排行")

    _ensure_archive_field(
        archive, {"key": "offShelfReason", "label": "下架原因", "type": "text"}
    )
    labels.setdefault("offShelfReasonLabel", "下架原因")
    labels.setdefault("offShelfReasonHint", "下架时可登记原因，便于复查。")
    thicken["offShelfReason"] = True
    _add_feature(spec, "媒资下架原因")

    _ensure_archive_field(
        archive, {"key": "shareCode", "label": "分享码", "type": "text"}
    )
    labels.setdefault("shareCodeLabel", "分享码")
    labels.setdefault("shareCodeHint", "他人凭码可打开本曲只读页，不是多人协作编辑。")
    labels.setdefault("shareCodeEntryLabel", "凭码打开")
    labels.setdefault("shareCodePrompt", "请输入分享码")
    labels.setdefault("shareCodeBlocked", "分享码无效")
    thicken["shareCode"] = True
    _add_feature(spec, "歌单分享码")

    _apply_favorite_group_skin(spec, thicken, labels)


def _apply_doclib_skin(
    spec: dict[str, Any],
    schema: dict[str, Any],
    archive: dict[str, Any],
    thicken: dict[str, Any],
    labels: dict[str, Any],
) -> None:
    """C-07：仅 DOM-DOCLIB 域默认域皮（预览≠转码云；积分下载归 C-08）。"""
    # 预览入口（外链或相对路径，不转码）
    _ensure_archive_field(
        archive, {"key": "previewUrl", "label": "在线预览地址", "type": "text"}
    )
    labels.setdefault("previewLabel", "在线预览")
    labels.setdefault("previewEmpty", "暂无预览地址")
    labels.setdefault("previewHint", "打开链接预览，本系统不负责转码。")
    thicken["docPreview"] = True
    _add_feature(spec, "文库在线预览")

    # 试读说明
    _ensure_archive_field(
        archive, {"key": "trialReadNote", "label": "试读说明", "type": "textarea"}
    )
    labels.setdefault("trialReadLabel", "试读说明")
    labels.setdefault("trialReadEmpty", "暂无试读说明")
    thicken["trialRead"] = True
    _add_feature(spec, "文库试读说明")

    # 下载权限角色（逗号分隔，空=登录即可）
    _ensure_archive_field(
        archive, {"key": "downloadRoles", "label": "可下载角色", "type": "text"}
    )
    labels.setdefault("downloadRolesLabel", "可下载角色")
    labels.setdefault("downloadRolesHint", "多个角色用逗号分隔，留空表示登录即可下载。")
    labels.setdefault("downloadDenied", "当前身份不能下载这份资料")
    thicken["downloadRoles"] = True
    _add_feature(spec, "文库下载角色")

    # 水印开关（前端叠加文案，非真 PDF 水印引擎）
    _ensure_archive_field(
        archive, {"key": "watermarkOn", "label": "预览水印", "type": "boolean"}
    )
    labels.setdefault("watermarkLabel", "预览水印")
    labels.setdefault("watermarkHint", "预览页叠加账号水印提示，不是 PDF 引擎级水印。")
    thicken["watermark"] = True
    _add_feature(spec, "文库预览水印")

    # 日下载限额 + 审核开关（schema 级默认）
    if not int(schema.get("dailyDownloadLimit") or 0):
        schema["dailyDownloadLimit"] = 20
    labels.setdefault("dailyDownloadLimitLabel", "每日下载上限")
    labels.setdefault("downloadQuotaExceeded", "今日下载次数已达上限，请明天再试")
    thicken["downloadQuota"] = True
    _add_feature(spec, "文库下载限额")

    _ensure_archive_field(
        archive,
        {"key": "needsDownloadAudit", "label": "下载需审核", "type": "boolean"},
    )
    labels.setdefault("downloadAuditLabel", "下载需审核")
    labels.setdefault("downloadAuditPending", "下载申请已提交，请等待审核")
    labels.setdefault("downloadAuditDenied", "下载申请未通过")
    thicken["downloadAudit"] = True
    _add_feature(spec, "文库下载审核")

    # 章节目录 / 版本 / 标签云 / 纠错侵权
    labels.setdefault("chapterLabel", "章节目录")
    labels.setdefault("chapterEmpty", "暂无章节")
    labels.setdefault("versionLabel", "版本记录")
    labels.setdefault("versionEmpty", "暂无版本记录")
    labels.setdefault("tagCloudLabel", "标签")
    labels.setdefault("tagCloudEmpty", "暂无标签")
    labels.setdefault("correctionLabel", "纠错反馈")
    labels.setdefault("correctionSubmit", "提交纠错")
    labels.setdefault("correctionDone", "已收到纠错，感谢反馈")
    labels.setdefault("infringementLabel", "侵权投诉")
    labels.setdefault("infringementSubmit", "提交投诉")
    labels.setdefault("infringementDone", "投诉已登记，管理员将处理")
    labels.setdefault("downloadLogLabel", "我的下载记录")
    labels.setdefault("downloadLogEmpty", "还没有下载记录")
    labels.setdefault("adminDownloadRequestLabel", "下载审核")
    labels.setdefault("adminFeedbackLabel", "纠错与投诉")
    thicken["docChapter"] = True
    thicken["docVersion"] = True
    thicken["docTagCloud"] = True
    thicken["docFeedback"] = True
    thicken["downloadLog"] = True
    _add_feature(spec, "文库章节版本标签")
    _add_feature(spec, "文库纠错与侵权投诉")
    _add_feature(spec, "文库下载记录")


def _apply_blog_comment_governance(
    spec: dict[str, Any],
    schema: dict[str, Any],
    thicken: dict[str, Any],
    labels: dict[str, Any],
) -> None:
    """C-03：BLOG 在已挂 item_comment 时叠楼中楼/折叠/点赞/敏感词。"""
    caps = list(spec.get("capabilities") or [])
    if "item_comment" not in caps:
        return
    labels.setdefault("nestedReplyLabel", "回复")
    labels.setdefault("nestedReplyHint", "只能回复一层。")
    thicken["nestedReply"] = True
    labels.setdefault("commentLikeLabel", "赞")
    labels.setdefault("commentLikedLabel", "已赞")
    thicken["commentLike"] = True
    if not int(schema.get("commentFoldAfter") or 0):
        schema["commentFoldAfter"] = _COMMENT_FOLD_AFTER_DEFAULT
    labels.setdefault("commentFoldMoreLabel", "展开更多回复")
    labels.setdefault("commentFoldLessLabel", "收起")
    thicken["commentFold"] = True
    if not isinstance(schema.get("sensitiveWords"), list) or not schema.get("sensitiveWords"):
        schema["sensitiveWords"] = list(_DEFAULT_SENSITIVE_WORDS)
    labels.setdefault("sensitiveWordBlocked", "内容含不宜发布的用语，请修改后再提交")
    thicken["sensitiveWords"] = True
    _add_feature(spec, "博客评论楼中楼")


def _apply_capability_islands(
    spec: dict[str, Any],
    schema: dict[str, Any],
    archive: dict[str, Any],
    thicken: dict[str, Any],
    labels: dict[str, Any],
) -> None:
    """C-08：仅当已挂对应 cap 时加深；禁止因「常见」域默认硬挂 points/wallet。"""
    domain = str(spec.get("domain") or "")
    caps = set(spec.get("capabilities") or [])
    has_points = "points" in caps
    has_wallet = "wallet" in caps
    has_report = "content_report" in caps
    has_comment = "item_comment" in caps
    archive_ent = archive if isinstance(archive, dict) else {}
    has_user_publish = bool(archive_ent.get("userPublish")) or "userPublish" in caps

    # —— 文库积分/点券下载（须 points 或 wallet）——
    if domain == "DOM-DOCLIB" and (has_points or has_wallet):
        _ensure_archive_field(
            archive,
            {"key": "downloadCostPoints", "label": "下载所需积分", "type": "number"},
        )
        labels.setdefault("downloadCostPointsLabel", "下载所需积分")
        labels.setdefault("downloadCostHint", "大于 0 时下载会先扣积分；0 表示免费。")
        labels.setdefault("downloadPointsShortage", "积分不足，无法下载")
        labels.setdefault("downloadPointsDebited", "已扣积分并记入台账")
        thicken["docPointsDownload"] = True
        thicken["docPaidDownload"] = True
        _add_feature(spec, "文库积分下载")
        _add_feature(spec, "文库付费点券下载")

    # —— 精华奖分 / 签到涨分 / 等级规则页（须 points；论坛为主）——
    if has_points and domain == "DOM-FORUM":
        if not int(schema.get("essencePointsReward") or 0):
            schema["essencePointsReward"] = _ESSENCE_POINTS_REWARD_DEFAULT
        labels.setdefault("essencePointsRewardLabel", "精华奖励积分")
        labels.setdefault("essencePointsRewardHint", "管理员标为精华时给作者记入积分。")
        thicken["essencePointsReward"] = True
        _add_feature(spec, "精华帖奖励积分")

        if not int(schema.get("pointsCheckInAmount") or 0):
            schema["pointsCheckInAmount"] = _POINTS_CHECK_IN_AMOUNT_DEFAULT
        schema["pointsCheckInEnabled"] = True
        labels.setdefault("pointsCheckInLabel", "每日登录奖励")
        labels.setdefault(
            "pointsCheckInHint",
            "当天首次登录自动入账积分，同一天只发一次。",
        )
        thicken["pointsCheckIn"] = True
        _add_feature(spec, "论坛每日签到涨积分")

        labels.setdefault("pointsRulesPageTitle", "积分规则")
        labels.setdefault(
            "pointsRulesPageLead",
            "说明如何获得与使用积分；具体分值以当前规则为准。",
        )
        labels.setdefault(
            "pointsRulesBody",
            "登录奖励、精华奖励与资料下载扣分会记入积分流水。本页仅说明规则，不是支付收银台。",
        )
        thicken["pointsRulesPage"] = True
        _add_feature(spec, "论坛用户等级积分规则页")
        try:
            from app.bake.schema.menu_utils import ensure_menu

            menus = schema.setdefault("menus", {})
            user = menus.setdefault("user", [])
            ensure_menu(
                user,
                "points_rules",
                {
                    "key": "points_rules",
                    "label": labels.get("pointsRulesPageTitle") or "积分规则",
                },
                before_key="points_ledger",
            )
        except Exception:
            pass

    # —— 举报原因字典 + 评论举报（须 content_report）——
    if has_report:
        if not isinstance(schema.get("reportReasons"), list) or not schema.get("reportReasons"):
            schema["reportReasons"] = list(_DEFAULT_REPORT_REASONS)
        labels.setdefault("reportReasonLabel", "举报原因")
        labels.setdefault("reportReasonRequired", "请选择举报原因")
        labels.setdefault("reportReasonOtherPlaceholder", "补充说明（选填）")
        thicken["reportReasonDict"] = True
        _add_feature(spec, "内容举报原因字典")
        if has_comment or domain in ("DOM-FORUM", "DOM-BLOG"):
            labels.setdefault("commentReportLabel", "举报评论")
            labels.setdefault("commentReportDone", "已提交评论举报")
            thicken["commentReport"] = True
            _add_feature(spec, "评论举报")

    # —— 评论仅粉丝可见（浅互关；有 item_comment 时）——
    if has_comment and domain in ("DOM-FORUM", "DOM-BLOG"):
        labels.setdefault("followersOnlyCommentLabel", "仅粉丝可见")
        labels.setdefault("followersOnlyCommentHint", "开启后只有互关粉丝能看到这条评论。")
        labels.setdefault("followersOnlyCommentHidden", "该评论仅对粉丝可见")
        labels.setdefault("followUserLabel", "关注作者")
        labels.setdefault("unfollowUserLabel", "取消关注")
        thicken["followersOnlyComment"] = True
        _add_feature(spec, "评论仅粉丝可见")

    # —— 投稿审过自动上架通知（须 userPublish）——
    if has_user_publish and domain in ("DOM-BLOG", "DOM-MEDIA", "DOM-FORUM"):
        labels.setdefault("publishApproveNotifyTitle", "投稿已通过")
        labels.setdefault(
            "publishApproveNotifyBody",
            "你的投稿已审核通过并上架，可在列表中查看。",
        )
        thicken["publishApproveNotify"] = True
        _add_feature(spec, "投稿审过上架通知")


def apply_content_thicken_to_spec(
    spec: dict[str, Any], proposal_text: str = ""
) -> dict[str, Any]:
    """按域默认加厚内容组 schema（只增不减；非本组原样返回）。"""
    del proposal_text  # 通识/域皮不扫词；C-08 读已合并的 capabilities
    domain = str(spec.get("domain") or "")
    if domain not in CONTENT_DOMAINS:
        return spec
    caps = list(spec.get("capabilities") or [])
    if "archive" not in caps:
        return spec

    schema = _live_schema(spec)
    labels = schema.setdefault("labels", {})
    ents = schema.setdefault("entities", {})
    archive = ents.get("archive") if isinstance(ents.get("archive"), dict) else {}
    if not isinstance(archive, dict):
        archive = {}
        ents["archive"] = archive
    thicken = (
        schema.get("contentThicken")
        if isinstance(schema.get("contentThicken"), dict)
        else {}
    )
    schema["contentThicken"] = thicken
    archive["contentThicken"] = True
    thicken["core"] = True
    _add_feature(spec, "内容组加厚")

    # —— C-01：阅读数 ——
    _ensure_archive_field(
        archive,
        {"key": "viewCount", "label": "阅读数", "type": "number"},
    )
    labels.setdefault("viewCountLabel", "阅读数")
    thicken["viewCount"] = True
    _add_feature(spec, "帖子文章阅读数")

    # —— C-01：热门排行（计数排序，≠协同过滤）——
    labels.setdefault("hotRankPageTitle", "热门排行")
    labels.setdefault("hotRankPageLead", "按阅读次数从高到低排列。")
    labels.setdefault("hotRankToggleLabel", "看热门")
    labels.setdefault("hotRankBackLabel", "全部")
    thicken["hotRank"] = True
    if domain == "DOM-DOCLIB":
        labels["hotRankPageLead"] = "按下载次数从高到低排列。"
        labels.setdefault("downloadCountLabel", "下载次数")
        thicken["hotByDownload"] = True
        _ensure_archive_field(
            archive,
            {"key": "downloadCount", "label": "下载次数", "type": "number"},
        )
    _add_feature(spec, "热门排行")

    # —— C-01：个人足迹 ——
    if domain in _BROWSE_HISTORY_DOMAINS:
        _nail_browse_history(spec, schema, thicken)

    # —— C-01：标题关键词 / 前缀联想 ——
    if domain in _TITLE_SEARCH_DOMAINS:
        search = schema.setdefault("search", {})
        search["suggestEnabled"] = True
        labels.setdefault("searchSuggestHint", "输入标题可联想")
        labels.setdefault("titleSearchPlaceholder", "按标题关键词搜索")
        thicken["titleSearch"] = True
        _add_feature(spec, "标题关键词搜索")

    # —— C-02：FORUM 运营 ——
    if domain == "DOM-FORUM":
        _apply_forum_ops(spec, schema, archive, thicken, labels)
        _apply_forum_governance(spec, schema, thicken, labels)

    # —— C-03：BLOG 评论治理叠；C-04：BLOG 域皮 ——
    if domain == "DOM-BLOG":
        _apply_blog_comment_governance(spec, schema, thicken, labels)
        _apply_blog_skin(spec, schema, archive, thicken, labels)

    # —— C-05：MEDIA 域皮 ——
    if domain == "DOM-MEDIA":
        _apply_media_skin(spec, schema, archive, thicken, labels)

    # —— C-06：MUSIC 域皮 ——
    if domain == "DOM-MUSIC":
        _apply_music_skin(spec, schema, archive, thicken, labels)

    # —— C-07：DOCLIB 域皮 ——
    if domain == "DOM-DOCLIB":
        _apply_doclib_skin(spec, schema, archive, thicken, labels)

    # —— C-08：能力岛（仅已挂 cap）——
    _apply_capability_islands(spec, schema, archive, thicken, labels)

    # —— C-09：扫尾叠（作者主页 FORUM、草稿自动保存）——
    _apply_c09_sweep(spec, schema, thicken, labels, domain)

    return spec


def _apply_c09_sweep(
    spec: dict[str, Any],
    schema: dict[str, Any],
    thicken: dict[str, Any],
    labels: dict[str, Any],
    domain: str,
) -> None:
    """C-09：论坛叠作者主页；有草稿箱时加深自动保存（真写库）。"""
    del schema  # 本扫尾不改 schema 结构键
    if domain == "DOM-FORUM":
        labels.setdefault("authorPageTitle", "作者主页")
        labels.setdefault("authorPageLead", "查看该作者发布的帖子。")
        labels.setdefault("authorPageEntryLabel", "看作者")
        thicken["authorPage"] = True
        _add_feature(spec, "作者主页论坛叠")

    if thicken.get("draftBox") and domain in ("DOM-FORUM", "DOM-BLOG"):
        labels.setdefault("draftAutoSaveHint", "编辑时会自动保存草稿，可稍后在「我的」里继续。")
        labels.setdefault("draftAutoSavedLabel", "草稿已自动保存")
        thicken["draftAutoSave"] = True
        _add_feature(spec, "帖子草稿自动保存")
