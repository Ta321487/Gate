"""内容组 content_thicken：C-00～C-09（脚手架起；通识/域皮后续批次补钉）。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_sql import domain_sql
from app.bake.features.content_thicken import CONTENT_DOMAINS, ensure_content_thicken_sql

REPO = Path(__file__).resolve().parents[2]
FE = REPO / "skeletons" / "baseline" / "frontend" / "src"
BE = REPO / "skeletons" / "baseline" / "backend" / "src" / "main" / "java" / "com" / "thesis"


def _spec(
    domain: str,
    title: str,
    body: str = "",
    *,
    archetype: str = "ARCH-CONTENT",
    extra_caps: list[str] | None = None,
) -> dict:
    caps = list(DOMAIN_CAPABILITIES[domain])
    for c in extra_caps or []:
        if c not in caps:
            caps.append(c)
    return attach_accept(
        {
            "domain": domain,
            "title": title,
            "capabilities": caps,
            "features": [],
            "archetype": archetype,
        },
        body,
    )


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class ContentThickenFeatureTests(unittest.TestCase):
    def test_content_domains_constant(self) -> None:
        self.assertEqual(
            CONTENT_DOMAINS,
            frozenset(
                {
                    "DOM-MEDIA",
                    "DOM-MUSIC",
                    "DOM-FORUM",
                    "DOM-BLOG",
                    "DOM-DOCLIB",
                }
            ),
        )

    def test_trade_domains_untouched(self) -> None:
        for domain, title in (
            ("DOM-SHOP", "校园二手商城系统"),
            ("DOM-FOOD", "校园点餐配送系统"),
            ("DOM-CINEMA", "影院在线选座购票系统"),
        ):
            out = _spec(domain, title, "", archetype="ARCH-TRADE")
            schema = out.get("schema") or {}
            self.assertFalse(schema.get("contentThicken"))
            archive = (schema.get("entities") or {}).get("archive") or {}
            self.assertFalse(archive.get("contentThicken"))

    def test_reserve_domains_untouched(self) -> None:
        for domain, title in (
            ("DOM-HOSPITAL", "医院挂号预约系统"),
            ("DOM-PARKING", "停车场预约管理系统"),
        ):
            out = _spec(domain, title, "", archetype="ARCH-RESERVE")
            schema = out.get("schema") or {}
            self.assertFalse(schema.get("contentThicken"))

    def test_interact_domains_untouched(self) -> None:
        for domain, title in (
            ("DOM-DATING", "校园婚恋交友系统"),
            ("DOM-MUTUAL-TOPIC", "话题互选匹配系统"),
        ):
            out = _spec(domain, title, "", archetype="ARCH-CRUD")
            schema = out.get("schema") or {}
            self.assertFalse(schema.get("contentThicken"))

    def test_c00_scaffold_on_five_content_domains(self) -> None:
        cases = (
            ("DOM-MEDIA", "点播课课程视频库管理系统"),
            ("DOM-MUSIC", "曲库点歌台管理系统"),
            ("DOM-FORUM", "校园表白墙树洞管理系统"),
            ("DOM-BLOG", "校园资讯院刊发布管理系统"),
            ("DOM-DOCLIB", "资料文库下载台管理系统"),
        )
        for domain, title in cases:
            out = _spec(domain, title, "")
            schema = out.get("schema") or {}
            thicken = schema.get("contentThicken") or {}
            archive = (schema.get("entities") or {}).get("archive") or {}
            self.assertTrue(thicken.get("core"), domain)
            self.assertTrue(archive.get("contentThicken"), domain)
            self.assertFalse(schema.get("tradeThicken"), domain)
            self.assertFalse(schema.get("reserveThicken"), domain)
            feats = out.get("features") or []
            self.assertIn("内容组加厚", feats)

    def test_c01_view_count_and_hot_rank_five_domains(self) -> None:
        for domain, title in (
            ("DOM-MEDIA", "点播课课程视频库管理系统"),
            ("DOM-MUSIC", "曲库点歌台管理系统"),
            ("DOM-FORUM", "校园表白墙树洞管理系统"),
            ("DOM-BLOG", "校园资讯院刊发布管理系统"),
            ("DOM-DOCLIB", "资料文库下载台管理系统"),
        ):
            out = _spec(domain, title, "")
            schema = out.get("schema") or {}
            thicken = schema.get("contentThicken") or {}
            labels = schema.get("labels") or {}
            self.assertTrue(thicken.get("viewCount"), domain)
            self.assertTrue(thicken.get("hotRank"), domain)
            self.assertIn("viewCountLabel", labels)
            self.assertIn("hotRankPageTitle", labels)
            self.assertIn("hotRankPageLead", labels)
            self.assertIn("hotRankToggleLabel", labels)
            self.assertIn("hotRankBackLabel", labels)

    def test_c01_doclib_hot_by_download(self) -> None:
        out = _spec("DOM-DOCLIB", "资料文库下载台管理系统", "")
        thicken = (out.get("schema") or {}).get("contentThicken") or {}
        labels = (out.get("schema") or {}).get("labels") or {}
        self.assertTrue(thicken.get("hotByDownload"))
        self.assertIn("downloadCountLabel", labels)
        forum = _spec("DOM-FORUM", "校园表白墙树洞管理系统", "")
        self.assertFalse(
            ((forum.get("schema") or {}).get("contentThicken") or {}).get("hotByDownload")
        )

    def test_c01_browse_history_media_music_blog(self) -> None:
        for domain, title in (
            ("DOM-MEDIA", "点播课课程视频库管理系统"),
            ("DOM-MUSIC", "曲库点歌台管理系统"),
            ("DOM-BLOG", "校园资讯院刊发布管理系统"),
        ):
            out = _spec(domain, title, "")
            caps = out.get("capabilities") or []
            thicken = (out.get("schema") or {}).get("contentThicken") or {}
            labels = (out.get("schema") or {}).get("labels") or {}
            self.assertIn("browse_history", caps, domain)
            self.assertTrue(thicken.get("browseHistory"), domain)
            self.assertIn("browseHistoryPageTitle", labels)
            self.assertIn("browseHistoryPageLead", labels)
        forum = _spec("DOM-FORUM", "校园表白墙树洞管理系统", "")
        self.assertNotIn("browse_history", forum.get("capabilities") or [])

    def test_c01_title_search_content_domains(self) -> None:
        for domain, title in (
            ("DOM-FORUM", "校园表白墙树洞管理系统"),
            ("DOM-BLOG", "校园资讯院刊发布管理系统"),
            ("DOM-MEDIA", "点播课课程视频库管理系统"),
        ):
            out = _spec(domain, title, "")
            schema = out.get("schema") or {}
            thicken = schema.get("contentThicken") or {}
            labels = schema.get("labels") or {}
            search = schema.get("search") or {}
            self.assertTrue(thicken.get("titleSearch"), domain)
            self.assertTrue(search.get("suggestEnabled"), domain)
            self.assertIn("titleSearchPlaceholder", labels)
            self.assertIn("searchSuggestHint", labels)

    def test_ensure_sql_noop_outside_content(self) -> None:
        base = "CREATE TABLE IF NOT EXISTS item (id INT PRIMARY KEY);\n"
        out = ensure_content_thicken_sql(base, domain="DOM-SHOP", item_table="item")
        self.assertEqual(out, base)

    def test_ensure_sql_injects_view_count(self) -> None:
        base = (
            "CREATE TABLE IF NOT EXISTS media (\n"
            "  id BIGINT PRIMARY KEY,\n"
            "  title VARCHAR(128) NOT NULL\n"
            ");\n"
        )
        out = ensure_content_thicken_sql(base, domain="DOM-MEDIA", item_table="media")
        self.assertIn("view_count", out)

    def test_ensure_sql_injects_download_count_doclib(self) -> None:
        base = (
            "CREATE TABLE IF NOT EXISTS doc_item (\n"
            "  id BIGINT PRIMARY KEY,\n"
            "  title VARCHAR(128) NOT NULL\n"
            ");\n"
        )
        out = ensure_content_thicken_sql(base, domain="DOM-DOCLIB", item_table="doc_item")
        self.assertIn("view_count", out)
        self.assertIn("download_count", out)

    def test_domain_sql_has_view_count_for_forum(self) -> None:
        sql = domain_sql("DOM-FORUM", "forum_db", "")
        self.assertIn("view_count", sql)

    def test_c01_skeleton_page_hot_three_stores(self) -> None:
        stores = (
            BE / "capability" / "ArchiveStore.java",
            REPO
            / "skeletons"
            / "overlays"
            / "persistence-mybatis"
            / "backend"
            / "src"
            / "main"
            / "java"
            / "com"
            / "thesis"
            / "capability"
            / "ArchiveStore.java",
            REPO
            / "skeletons"
            / "overlays"
            / "persistence-jpa"
            / "backend"
            / "src"
            / "main"
            / "java"
            / "com"
            / "thesis"
            / "capability"
            / "ArchiveStore.java",
        )
        for path in stores:
            text = _read(path)
            self.assertIn("pageHot", text, str(path))
            self.assertIn("download_count", text, str(path))

        ctrl = _read(BE / "controller" / "ArchiveController.java")
        self.assertIn('/hot"', ctrl)
        self.assertIn("pageHot", ctrl)

    def test_c01_frontend_reads_labels(self) -> None:
        browse = _read(FE / "views" / "user" / "ArchiveBrowse.vue")
        admin = _read(FE / "views" / "admin" / "ArchiveAdmin.vue")
        hist = _read(FE / "views" / "user" / "BrowseHistory.vue")
        for needle in (
            "viewCountLabel",
            "hotRankPageTitle",
            "hotRankPageLead",
            "hotRankToggleLabel",
            "hotRankBackLabel",
            "titleSearchPlaceholder",
            "searchSuggestHint",
            "/api/archive/hot",
        ):
            self.assertTrue(
                needle in browse or needle in admin,
                f"FE 缺 {needle}",
            )
        self.assertIn("browseHistoryPageTitle", hist)
        self.assertIn("browseHistoryPageLead", hist)

    def test_c02_forum_ops_schema_and_sql(self) -> None:
        out = _spec("DOM-FORUM", "校园表白墙树洞管理系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("contentThicken") or {}
        labels = schema.get("labels") or {}
        archive = (schema.get("entities") or {}).get("archive") or {}
        for key in (
            "pinTop",
            "essence",
            "locked",
            "draftBox",
            "moveCategory",
            "dailyPostLimit",
            "publishReview",
            "sectionNotice",
        ):
            self.assertTrue(thicken.get(key), key)
        self.assertTrue(archive.get("publishReview"))
        self.assertEqual(int(schema.get("forumDailyPostLimit") or 0), 10)
        for lab in (
            "pinTopLabel",
            "essenceLabel",
            "lockedLabel",
            "draftBoxPageTitle",
            "saveDraftLabel",
            "publishFromDraftLabel",
            "moveCategoryLabel",
            "dailyPostLimitHint",
            "sectionNoticeLabel",
            "lockedReplyBlocked",
        ):
            self.assertIn(lab, labels)
        feats = out.get("features") or []
        for f in (
            "精华帖置顶",
            "帖子锁定",
            "帖子草稿箱",
            "帖子移动版块",
            "论坛每日发帖上限",
            "发帖审后可见",
            "版块公告",
        ):
            self.assertIn(f, feats)
        sql = domain_sql("DOM-FORUM", "forum_db", "")
        for col in ("pin_top", "essence", "locked", "section_notice"):
            self.assertIn(col, sql)

    def test_c02_skeleton_stores_and_api(self) -> None:
        stores = (
            BE / "capability" / "ArchiveStore.java",
            REPO
            / "skeletons"
            / "overlays"
            / "persistence-mybatis"
            / "backend"
            / "src"
            / "main"
            / "java"
            / "com"
            / "thesis"
            / "capability"
            / "ArchiveStore.java",
            REPO
            / "skeletons"
            / "overlays"
            / "persistence-jpa"
            / "backend"
            / "src"
            / "main"
            / "java"
            / "com"
            / "thesis"
            / "capability"
            / "ArchiveStore.java",
        )
        for path in stores:
            text = _read(path)
            for needle in (
                "forumDailyPostLimit",
                "saveUserDraft",
                "publishDraft",
                "assertNotLocked",
                "section_notice",
                "essence",
                "locked",
            ):
                self.assertIn(needle, text, f"{path} 缺 {needle}")

        ctrl = _read(BE / "controller" / "ArchiveController.java")
        self.assertIn("publish-draft", ctrl)
        self.assertIn("saveUserDraft", ctrl)
        self.assertIn("pageMine", ctrl)

        cat = _read(BE / "controller" / "CategoryController.java")
        self.assertIn("sectionNotice", cat)

        ticket = _read(BE / "capability" / "TicketApplyOps.java")
        self.assertIn("assertNotLocked", ticket)

    def test_c02_frontend_forum_ops(self) -> None:
        browse = _read(FE / "views" / "user" / "ArchiveBrowse.vue")
        mine = _read(FE / "views" / "user" / "MyArchive.vue")
        cats = _read(FE / "views" / "admin" / "CategoriesAdmin.vue")
        admin = _read(FE / "views" / "admin" / "ArchiveAdmin.vue")
        for needle in (
            "saveDraftLabel",
            "draftBoxOn",
            "essenceLabel",
            "lockedLabel",
            "activeSectionNotice",
            "lockedReplyBlocked",
        ):
            self.assertIn(needle, browse, needle)
        for needle in (
            "publish-draft",
            "draftBoxPageTitle",
            "publishFromDraftLabel",
            "statusFilter",
        ):
            self.assertIn(needle, mine, needle)
        self.assertIn("sectionNotice", cats)
        self.assertIn("sectionNoticeLabel", cats)
        self.assertIn("forumOpsOn", admin)
        self.assertIn("essenceLabel", admin)

    def test_c03_forum_governance_schema(self) -> None:
        out = _spec("DOM-FORUM", "校园表白墙树洞管理系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("contentThicken") or {}
        labels = schema.get("labels") or {}
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        for key in (
            "nestedReply",
            "mentionNotify",
            "muteExpire",
            "reportResultNotify",
            "reportDeadline",
            "commentLike",
            "sensitiveWords",
            "moderatorAppoint",
            "commentFold",
            "pinEssenceAudit",
        ):
            self.assertTrue(thicken.get(key), key)
        self.assertTrue(ticket.get("allowNestedReply"))
        self.assertEqual(int(schema.get("reportHandleDays") or 0), 3)
        self.assertEqual(int(schema.get("commentFoldAfter") or 0), 3)
        self.assertTrue(isinstance(schema.get("sensitiveWords"), list))
        self.assertTrue(len(schema.get("sensitiveWords") or []) > 0)
        for lab in (
            "nestedReplyLabel",
            "mentionNotifyHint",
            "reportResultNotifyTitle",
            "reportOverdueLabel",
            "commentLikeLabel",
            "sensitiveWordBlocked",
            "moderatorAppointLabel",
            "commentFoldMoreLabel",
        ):
            self.assertIn(lab, labels)
        sql = domain_sql("DOM-FORUM", "forum_db", "")
        self.assertIn("parent_ticket_id", sql)
        self.assertIn("handle_deadline_at", sql)

    def test_c03_skeleton_governance_hooks(self) -> None:
        sens = _read(BE / "service" / "SensitiveWordGate.java")
        mention = _read(BE / "service" / "MentionNotify.java")
        self.assertIn("assertClean", sens)
        self.assertIn("notifyFromText", mention)
        user = _read(BE / "service" / "UserStore.java")
        self.assertIn("clearExpiredPostMutes", user)
        fav = _read(BE / "capability" / "FavoriteStore.java")
        self.assertIn("configureReportHandleDays", fav)
        self.assertIn("handle_deadline_at", fav)
        self.assertIn("举报处理结果", fav)
        apply = _read(BE / "capability" / "TicketApplyOps.java")
        self.assertIn("SensitiveWordGate", apply)
        self.assertIn("MentionNotify", apply)
        patch = _read(BE / "capability" / "TicketPatchOps.java")
        self.assertIn("不能再盖楼", patch)
        comment = _read(BE / "service" / "ItemCommentStore.java")
        self.assertIn("parent_id", comment)
        self.assertIn("toggleLike", comment)
        policy = _read(BE / "config" / "AppPolicy.java")
        self.assertIn("CONTENT_SENSITIVE_FILTER", policy)
        self.assertIn("CONTENT_MENTION_NOTIFY", policy)
        self.assertIn("REPORT_HANDLE_DAYS", policy)
        binder = _read(BE / "config" / "DomainRuntimeBinder.java")
        self.assertIn("SensitiveWordGate", binder)
        self.assertIn("MentionNotify", binder)
        jobs = _read(BE / "config" / "DemoScheduleJobs.java")
        self.assertIn("clearExpiredPostMutes", jobs)

    def test_c03_frontend_nested_fold(self) -> None:
        browse = _read(FE / "views" / "user" / "ArchiveBrowse.vue")
        for needle in (
            "nestedReplyOn",
            "parentTicketId",
            "commentFoldOn",
            "openNestedReply",
            "mentionNotifyHint",
            "sensitiveWordHint",
            "threadRoots",
        ):
            self.assertIn(needle, browse, needle)

    def test_c04_blog_skin_schema(self) -> None:
        out = _spec("DOM-BLOG", "校园资讯院刊发布管理系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("contentThicken") or {}
        labels = schema.get("labels") or {}
        archive = (schema.get("entities") or {}).get("archive") or {}
        for key in (
            "draftBox",
            "categoryFollow",
            "categoryFollowNotify",
            "categoryFollowerCount",
            "scheduledPublish",
            "scheduledUnpublish",
            "archiveYearMonth",
            "seriesNav",
            "originKind",
            "authorPage",
            "commentAuthorNotify",
            "accessPassword",
            "friendLinks",
        ):
            self.assertTrue(thicken.get(key), key)
        field_keys = {f.get("key") for f in (archive.get("fields") or []) if isinstance(f, dict)}
        for fk in ("publishAt", "unpublishAt", "seriesId", "seriesOrd", "originKind", "accessPassword"):
            self.assertIn(fk, field_keys, fk)
        for lab in (
            "categoryFollowLabel",
            "archiveYearMonthLabel",
            "seriesPrevLabel",
            "originKindLabel",
            "authorPageEntryLabel",
            "commentAuthorNotifyHint",
            "accessPasswordPrompt",
            "friendLinkAdminTitle",
            "draftBoxPageTitle",
        ):
            self.assertIn(lab, labels)
        menus = ((schema.get("menus") or {}).get("admin") or [])
        self.assertTrue(any(m.get("key") == "blog_friend_links" for m in menus if isinstance(m, dict)))
        forum = _spec("DOM-FORUM", "校园表白墙树洞管理系统", "")
        fth = ((forum.get("schema") or {}).get("contentThicken") or {})
        self.assertFalse(fth.get("categoryFollow"))
        self.assertFalse(fth.get("friendLinks"))
        sql = domain_sql("DOM-BLOG", "blog_db", "")
        for needle in (
            "publish_at",
            "unpublish_at",
            "series_id",
            "origin_kind",
            "access_password",
            "category_follow",
            "blog_friend_link",
        ):
            self.assertIn(needle, sql)

    def test_c04_skeleton_stores_and_api(self) -> None:
        stores = (
            BE / "capability" / "ArchiveStore.java",
            REPO
            / "skeletons"
            / "overlays"
            / "persistence-mybatis"
            / "backend"
            / "src"
            / "main"
            / "java"
            / "com"
            / "thesis"
            / "capability"
            / "ArchiveStore.java",
            REPO
            / "skeletons"
            / "overlays"
            / "persistence-jpa"
            / "backend"
            / "src"
            / "main"
            / "java"
            / "com"
            / "thesis"
            / "capability"
            / "ArchiveStore.java",
        )
        for path in stores:
            text = _read(path)
            for needle in (
                "applyPublishSchedule",
                "pageByYearMonth",
                "pageByAuthor",
                "seriesNeighbors",
                "checkAccessPassword",
                "notifyCategoryFollowersIfPublic",
            ):
                self.assertIn(needle, text, f"{path} 缺 {needle}")

        follow = _read(BE / "service" / "CategoryFollowStore.java")
        self.assertIn("notifyFollowers", follow)
        self.assertIn("toggle", follow)
        links = _read(BE / "service" / "BlogFriendLinkStore.java")
        self.assertIn("listPublic", links)
        self.assertIn("save", links)
        ctrl = _read(BE / "controller" / "ArchiveController.java")
        for needle in ("by-author", "series-neighbors", "/unlock", "originKind", "accessPassword"):
            self.assertIn(needle, ctrl)
        self.assertTrue((BE / "controller" / "CategoryFollowController.java").is_file())
        self.assertTrue((BE / "controller" / "BlogFriendLinkController.java").is_file())
        comment = _read(BE / "service" / "ItemCommentStore.java")
        self.assertIn("configureAuthorNotify", comment)
        policy = _read(BE / "config" / "AppPolicy.java")
        self.assertIn("CONTENT_CATEGORY_FOLLOW", policy)
        self.assertIn("CONTENT_FRIEND_LINKS", policy)
        binder = _read(BE / "config" / "DomainRuntimeBinder.java")
        self.assertIn("CategoryFollowStore", binder)
        self.assertIn("BlogFriendLinkStore", binder)
        rt = _read(REPO / "backend" / "app" / "bake" / "runtime_policy.py")
        self.assertIn("CONTENT_CATEGORY_FOLLOW", rt)
        self.assertIn("friendLinks", rt)

    def test_c04_frontend_blog_ops(self) -> None:
        browse = _read(FE / "views" / "user" / "ArchiveBrowse.vue")
        for needle in (
            "categoryFollowOn",
            "archiveYearMonthOn",
            "seriesNavOn",
            "authorPageOn",
            "accessPasswordOn",
            "friendLinksOn",
            "originKindOn",
            "unlockDetail",
            "openAuthorPage",
            "loadFriendLinks",
            "toggleCategoryFollow",
        ):
            self.assertIn(needle, browse, needle)
        mine = _read(FE / "views" / "user" / "MyArchive.vue")
        self.assertIn("draftBoxOn", mine)
        self.assertIn("publish-draft", mine)
        cats = _read(FE / "views" / "admin" / "CategoriesAdmin.vue")
        self.assertIn("followerCountOn", cats)
        self.assertIn("category-follow/count", cats)
        friends = _read(FE / "views" / "admin" / "BlogFriendLinksAdmin.vue")
        self.assertIn("blog-friend-links", friends)
        router = _read(FE / "router" / "index.js")
        self.assertIn("withBlogFriendLinkRoutes", router)
        menus = _read(FE / "utils" / "menuRoutes.js")
        self.assertIn("blog_friend_links", menus)

    def test_c05_media_skin_schema(self) -> None:
        out = _spec("DOM-MEDIA", "校园影视点播片库管理系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("contentThicken") or {}
        labels = schema.get("labels") or {}
        for key in (
            "playProgress",
            "episodeCompleted",
            "episodeList",
            "episodeUpdateNotify",
            "posterWall",
            "hotByPlay",
            "offShelfReason",
            "shareCode",
            "scheduledPublish",
            "categoryFollow",
        ):
            self.assertTrue(thicken.get(key), key)
        self.assertIn("gallery", out.get("capabilities") or [])
        for lab in (
            "playProgressSaveLabel",
            "episodeListTitle",
            "posterWallTitle",
            "playCountLabel",
            "offShelfReasonLabel",
            "shareCodePrompt",
            "categoryFollowLabel",
            "publishAtLabel",
            "episodeUpdateNotifyHint",
        ):
            self.assertIn(lab, labels)
        blog = _spec("DOM-BLOG", "校园资讯院刊发布管理系统", "")
        self.assertFalse(
            ((blog.get("schema") or {}).get("contentThicken") or {}).get("episodeList")
        )
        sql = domain_sql("DOM-MEDIA", "media_db", "")
        for needle in (
            "play_count",
            "off_shelf_reason",
            "share_code",
            "publish_at",
            "media_episode",
            "media_play_progress",
            "category_follow",
        ):
            self.assertIn(needle, sql)

    def test_c05_skeleton_stores_and_api(self) -> None:
        stores = (
            BE / "capability" / "ArchiveStore.java",
            REPO
            / "skeletons"
            / "overlays"
            / "persistence-mybatis"
            / "backend"
            / "src"
            / "main"
            / "java"
            / "com"
            / "thesis"
            / "capability"
            / "ArchiveStore.java",
            REPO
            / "skeletons"
            / "overlays"
            / "persistence-jpa"
            / "backend"
            / "src"
            / "main"
            / "java"
            / "com"
            / "thesis"
            / "capability"
            / "ArchiveStore.java",
        )
        for path in stores:
            text = _read(path)
            for needle in ("bumpPlayCount", "getByShareCode", "play_count", "off_shelf_reason"):
                self.assertIn(needle, text, f"{path} 缺 {needle}")
        self.assertIn("playCount", _read(BE / "capability" / "ArchiveStore.java"))
        ep = _read(BE / "service" / "MediaEpisodeStore.java")
        self.assertIn("notifyFollowersOfNewEpisode", ep)
        prog = _read(BE / "service" / "MediaPlayProgressStore.java")
        self.assertIn("position_sec", prog)
        self.assertTrue((BE / "controller" / "MediaEpisodeController.java").is_file())
        self.assertTrue((BE / "controller" / "MediaPlayProgressController.java").is_file())
        ctrl = _read(BE / "controller" / "ArchiveController.java")
        self.assertIn("by-share-code", ctrl)
        self.assertIn("offShelfReason", ctrl)
        policy = _read(BE / "config" / "AppPolicy.java")
        self.assertIn("CONTENT_PLAY_PROGRESS", policy)
        self.assertIn("CONTENT_MEDIA_EPISODE", policy)
        binder = _read(BE / "config" / "DomainRuntimeBinder.java")
        self.assertIn("MediaPlayProgressStore", binder)
        self.assertIn("MediaEpisodeStore", binder)
        rt = _read(REPO / "backend" / "app" / "bake" / "runtime_policy.py")
        self.assertIn("CONTENT_PLAY_PROGRESS", rt)
        self.assertIn("playProgress", rt)

    def test_c05_frontend_media_ops(self) -> None:
        browse = _read(FE / "views" / "user" / "ArchiveBrowse.vue")
        for needle in (
            "playProgressOn",
            "episodeListOn",
            "posterWallOn",
            "hotByPlayOn",
            "shareCodeOn",
            "saveProgress",
            "openByShareCode",
            "loadEpisodes",
            "playCount",
        ):
            self.assertIn(needle, browse, needle)
        admin = _read(FE / "views" / "admin" / "ArchiveAdmin.vue")
        for needle in (
            "offShelfReasonOn",
            "episodeListOn",
            "episodeAdminTitle",
            "shareCodeHint",
            "offShelfReason",
        ):
            self.assertIn(needle, admin, needle)

    def test_c06_music_skin_schema(self) -> None:
        out = _spec("DOM-MUSIC", "校园曲库点播歌单管理系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("contentThicken") or {}
        labels = schema.get("labels") or {}
        for key in (
            "artistAlbumFilter",
            "lyrics",
            "coverMark",
            "audioQualitySwitch",
            "playProgress",
            "hotByPlay",
            "offShelfReason",
            "shareCode",
            "favoriteGroup",
            "playlistVisibility",
        ):
            self.assertTrue(thicken.get(key), key)
        self.assertFalse(thicken.get("episodeList"))
        for lab in (
            "artistFilterPlaceholder",
            "albumFilterPlaceholder",
            "lyricsLabel",
            "coverMarkLabel",
            "audioQualityHint",
            "playProgressSaveLabel",
            "playCountLabel",
            "offShelfReasonLabel",
            "shareCodePrompt",
            "favoriteGroupLabel",
            "playlistPublicLabel",
        ):
            self.assertIn(lab, labels)
        media = _spec("DOM-MEDIA", "校园影视点播片库管理系统", "")
        mth = (media.get("schema") or {}).get("contentThicken") or {}
        self.assertTrue(mth.get("favoriteGroup"))
        self.assertTrue(mth.get("episodeList"))
        sql = domain_sql("DOM-MUSIC", "music_db", "")
        for needle in (
            "play_count",
            "off_shelf_reason",
            "share_code",
            "artist",
            "album",
            "lyrics",
            "is_cover",
            "media_play_progress",
        ):
            self.assertIn(needle, sql)
        self.assertNotIn("media_episode", sql)

    def test_c06_skeleton_stores_and_api(self) -> None:
        stores = (
            BE / "capability" / "ArchiveStore.java",
            REPO
            / "skeletons"
            / "overlays"
            / "persistence-mybatis"
            / "backend"
            / "src"
            / "main"
            / "java"
            / "com"
            / "thesis"
            / "capability"
            / "ArchiveStore.java",
            REPO
            / "skeletons"
            / "overlays"
            / "persistence-jpa"
            / "backend"
            / "src"
            / "main"
            / "java"
            / "com"
            / "thesis"
            / "capability"
            / "ArchiveStore.java",
        )
        for path in stores:
            text = _read(path)
            for needle in ("artist LIKE", "album LIKE", '"lyrics"', "is_cover"):
                self.assertIn(needle, text, f"{path} 缺 {needle}")
        fav = _read(BE / "capability" / "FavoriteStore.java")
        for needle in ("configureGroups", "updateMeta", "pagePublic", "group_name", "is_public"):
            self.assertIn(needle, fav, needle)
        ctrl = _read(BE / "controller" / "FavoriteController.java")
        self.assertIn("/api/favorites/public", ctrl)
        self.assertIn("updateMeta", ctrl)
        arch = _read(BE / "controller" / "ArchiveController.java")
        self.assertIn("String artist", arch)
        self.assertIn("String album", arch)
        policy = _read(BE / "config" / "AppPolicy.java")
        self.assertIn("CONTENT_FAVORITE_GROUP", policy)
        binder = _read(BE / "config" / "DomainRuntimeBinder.java")
        self.assertIn("configureGroups", binder)
        rt = _read(REPO / "backend" / "app" / "bake" / "runtime_policy.py")
        self.assertIn("CONTENT_FAVORITE_GROUP", rt)
        self.assertIn("favoriteGroup", rt)

    def test_c06_frontend_music_ops(self) -> None:
        browse = _read(FE / "views" / "user" / "ArchiveBrowse.vue")
        for needle in (
            "artistAlbumFilterOn",
            "artistFilter",
            "albumFilter",
            "lyricsOn",
            "coverMarkOn",
            "audioQualityOn",
            "loadTrackProgress",
            "playProgressOn",
            "hotByPlayOn",
            "shareCodeOn",
        ):
            self.assertIn(needle, browse, needle)
        fav = _read(FE / "views" / "user" / "MyFavorites.vue")
        for needle in (
            "favoriteGroupOn",
            "saveMeta",
            "playlistPublicLabel",
            "groupFilter",
            "/api/favorites",
        ):
            self.assertIn(needle, fav, needle)

    def test_c07_doclib_skin_schema(self) -> None:
        out = _spec("DOM-DOCLIB", "资料文库下载台管理系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("contentThicken") or {}
        labels = schema.get("labels") or {}
        for key in (
            "docPreview",
            "trialRead",
            "downloadRoles",
            "watermark",
            "downloadQuota",
            "downloadAudit",
            "docChapter",
            "docVersion",
            "docTagCloud",
            "docFeedback",
            "downloadLog",
        ):
            self.assertTrue(thicken.get(key), key)
        self.assertEqual(int(schema.get("dailyDownloadLimit") or 0), 20)
        for lab in (
            "previewLabel",
            "previewHint",
            "trialReadLabel",
            "downloadRolesHint",
            "downloadDenied",
            "watermarkHint",
            "downloadQuotaExceeded",
            "downloadAuditPending",
            "chapterLabel",
            "versionLabel",
            "tagCloudLabel",
            "correctionSubmit",
            "infringementSubmit",
            "downloadLogEmpty",
        ):
            self.assertIn(lab, labels)
        music = _spec("DOM-MUSIC", "校园曲库点播歌单管理系统", "")
        mth = (music.get("schema") or {}).get("contentThicken") or {}
        self.assertFalse(mth.get("docChapter"))
        sql = domain_sql("DOM-DOCLIB", "doclib_db", "")
        for needle in (
            "preview_url",
            "download_roles",
            "trial_read_note",
            "watermark_on",
            "needs_download_audit",
            "doc_chapter",
            "doc_version",
            "doc_feedback",
            "doc_download_request",
            "doc_tag",
            "doc_item_tag",
        ):
            self.assertIn(needle, sql)

    def test_c07_skeleton_stores_and_api(self) -> None:
        stores = (
            BE / "service" / "DoclibStore.java",
            REPO
            / "skeletons"
            / "overlays"
            / "persistence-mybatis"
            / "backend"
            / "src"
            / "main"
            / "java"
            / "com"
            / "thesis"
            / "service"
            / "DoclibStore.java",
            REPO
            / "skeletons"
            / "overlays"
            / "persistence-jpa"
            / "backend"
            / "src"
            / "main"
            / "java"
            / "com"
            / "thesis"
            / "service"
            / "DoclibStore.java",
        )
        for path in stores:
            text = _read(path)
            for needle in (
                "configureThicken",
                "listChapters",
                "addVersion",
                "submitFeedback",
                "tagCloud",
                "pageDownloadRequests",
                "assertQuota",
                "assertDownloadRoles",
                "preview_url",
                "doc_chapter",
            ):
                self.assertIn(needle, text, f"{path} 缺 {needle}")
        ctrl = _read(BE / "controller" / "DoclibController.java")
        for needle in (
            "/tags/cloud",
            "/chapters",
            "/versions",
            "/feedback",
            "/download-requests",
            "roleOf",
        ):
            self.assertIn(needle, ctrl, needle)
        policy = _read(BE / "config" / "AppPolicy.java")
        for needle in (
            "CONTENT_DOCLIB_CHAPTER",
            "CONTENT_DOCLIB_FEEDBACK",
            "CONTENT_DOCLIB_TAG_CLOUD",
            "CONTENT_DOCLIB_DOWNLOAD_GATE",
            "DOCLIB_DAILY_DOWNLOAD_LIMIT",
        ):
            self.assertIn(needle, policy, needle)
        binder = _read(BE / "config" / "DomainRuntimeBinder.java")
        self.assertIn("configureThicken", binder)
        rt = _read(REPO / "backend" / "app" / "bake" / "runtime_policy.py")
        self.assertIn("CONTENT_DOCLIB_CHAPTER", rt)
        self.assertIn("docChapter", rt)
        self.assertIn("DOCLIB_DAILY_DOWNLOAD_LIMIT", rt)

    def test_c07_frontend_doclib_ops(self) -> None:
        browse = _read(FE / "views" / "DocBrowse.vue")
        for needle in (
            "previewOn",
            "openPreview",
            "watermarkOn",
            "chapterOn",
            "tagCloudOn",
            "feedbackOn",
            "trialReadOn",
            "/api/doclib/items",
            "/api/doclib/tags/cloud",
            "correction",
            "infringement",
        ):
            self.assertIn(needle, browse, needle)
        admin = _read(FE / "views" / "admin" / "DocFilesAdmin.vue")
        for needle in (
            "previewUrl",
            "downloadRoles",
            "watermarkOn",
            "needsDownloadAudit",
            "dailyDownloadLimit",
            "addChapter",
            "addVersion",
            "tagsText",
        ):
            self.assertIn(needle, admin, needle)
        logs = _read(FE / "views" / "admin" / "DocLogsAdmin.vue")
        for needle in (
            "download-requests",
            "admin/feedback",
            "auditOn",
            "feedbackOn",
            "handleReq",
            "handleFb",
        ):
            self.assertIn(needle, logs, needle)
        mine = _read(FE / "views" / "DocMine.vue")
        self.assertIn("downloadLogEmpty", mine)
        self.assertIn("/api/doclib/mine", mine)

    # —— C-08：能力岛（仅 cap 已挂；积分靠开题扫词，禁止域默认硬挂）——
    def test_c08_capability_islands_gated(self) -> None:
        bare_doc = _spec("DOM-DOCLIB", "资料文库下载台管理系统", "")
        bare_th = (bare_doc.get("schema") or {}).get("contentThicken") or {}
        self.assertFalse(bare_th.get("docPointsDownload"))
        self.assertFalse(bare_th.get("docPaidDownload"))
        self.assertNotIn("points", bare_doc.get("capabilities") or [])

        with_pts = _spec(
            "DOM-DOCLIB",
            "资料文库下载台管理系统",
            "支持会员积分下载资料，下载前扣积分。",
        )
        th = (with_pts.get("schema") or {}).get("contentThicken") or {}
        labels = (with_pts.get("schema") or {}).get("labels") or {}
        self.assertIn("points", with_pts.get("capabilities") or [])
        self.assertTrue(th.get("docPointsDownload"))
        self.assertTrue(th.get("docPaidDownload"))
        self.assertIn("downloadCostPointsLabel", labels)

        bare_forum = _spec("DOM-FORUM", "校园论坛交流管理系统", "")
        bf = (bare_forum.get("schema") or {}).get("contentThicken") or {}
        self.assertFalse(bf.get("essencePointsReward"))
        self.assertFalse(bf.get("pointsCheckIn"))
        self.assertFalse(bf.get("pointsRulesPage"))
        self.assertTrue(bf.get("reportReasonDict"))
        self.assertTrue(bf.get("commentReport"))
        self.assertFalse(bf.get("followersOnlyComment"))

        forum_pts = _spec(
            "DOM-FORUM",
            "校园论坛交流管理系统",
            "会员积分与签到积分，精华帖奖励积分。",
        )
        fp = (forum_pts.get("schema") or {}).get("contentThicken") or {}
        fl = (forum_pts.get("schema") or {}).get("labels") or {}
        self.assertIn("points", forum_pts.get("capabilities") or [])
        self.assertTrue(fp.get("essencePointsReward"))
        self.assertTrue(fp.get("pointsCheckIn"))
        self.assertTrue(fp.get("pointsRulesPage"))
        self.assertEqual(int((forum_pts.get("schema") or {}).get("essencePointsReward") or 0), 5)
        self.assertIn("pointsRulesPageTitle", fl)
        menus = ((forum_pts.get("schema") or {}).get("menus") or {}).get("user") or []
        self.assertTrue(any(m.get("key") == "points_rules" for m in menus if isinstance(m, dict)))

        blog = _spec("DOM-BLOG", "个人博客专栏管理系统", "")
        bt = (blog.get("schema") or {}).get("contentThicken") or {}
        # BLOG 壳默认 userPublish → 投稿审过通知
        self.assertTrue(bt.get("publishApproveNotify"))
        self.assertFalse(bt.get("followersOnlyComment"))

        blog_cmt = _spec(
            "DOM-BLOG",
            "个人博客专栏管理系统",
            "文章下方支持用户评论与评论区互动。",
        )
        bc = (blog_cmt.get("schema") or {}).get("contentThicken") or {}
        self.assertIn("item_comment", blog_cmt.get("capabilities") or [])
        self.assertTrue(bc.get("followersOnlyComment"))
        self.assertIn(
            "followersOnlyCommentLabel",
            (blog_cmt.get("schema") or {}).get("labels") or {},
        )

        music = _spec(
            "DOM-MUSIC",
            "校园曲库点播歌单管理系统",
            "会员积分兑换曲目。",
        )
        mt = (music.get("schema") or {}).get("contentThicken") or {}
        self.assertIn("points", music.get("capabilities") or [])
        self.assertFalse(mt.get("essencePointsReward"))
        self.assertFalse(mt.get("docPointsDownload"))

    def test_c08_skeleton_stores_and_api(self) -> None:
        loyalty = _read(BE / "capability" / "LoyaltyStore.java")
        for needle in ("spendPoints", "awardPoints", "checkInOnLogin", "pointsCheckInEnabled"):
            self.assertIn(needle, loyalty, needle)
        doclib = _read(BE / "service" / "DoclibStore.java")
        self.assertIn("configurePointsDownload", doclib)
        self.assertIn("spendPoints", doclib)
        self.assertIn("downloadCostPoints", doclib)
        archive = _read(BE / "capability" / "ArchiveStore.java")
        self.assertIn("configureContentIslands", archive)
        self.assertIn("essencePointsRewardOn", archive)
        self.assertIn("publishApproveNotifyOn", archive)
        fav = _read(BE / "capability" / "FavoriteStore.java")
        self.assertIn("configureCommentReport", fav)
        self.assertIn("未开放评论举报", fav)
        ic = _read(BE / "service" / "ItemCommentStore.java")
        for needle in ("configureFollowersOnly", "followersOnly", "pageByItem", "UserFollowStore"):
            self.assertIn(needle, ic, needle)
        uf = _read(BE / "service" / "UserFollowStore.java")
        self.assertIn("isFollowing", uf)
        self.assertIn("follow", uf)
        ctrl = _read(BE / "controller" / "UserFollowController.java")
        self.assertIn("/api/user-follow", ctrl)
        icc = _read(BE / "controller" / "ItemCommentController.java")
        self.assertIn("followersOnly", icc)
        self.assertIn("pageByItem(itemId, p, s, viewer)", icc)
        policy = _read(BE / "config" / "AppPolicy.java")
        for needle in (
            "CONTENT_DOCLIB_POINTS_DOWNLOAD",
            "CONTENT_ESSENCE_POINTS_REWARD",
            "POINTS_CHECK_IN_ENABLED",
            "CONTENT_REPORT_REASON_DICT",
            "CONTENT_COMMENT_REPORT",
            "CONTENT_FOLLOWERS_ONLY_COMMENT",
            "CONTENT_PUBLISH_APPROVE_NOTIFY",
        ):
            self.assertIn(needle, policy, needle)
        binder = _read(BE / "config" / "DomainRuntimeBinder.java")
        self.assertIn("configureContentIslands", binder)
        self.assertIn("configureCommentReport", binder)
        self.assertIn("configureFollowersOnly", binder)
        self.assertIn("UserFollowStore.configure", binder)
        rt = _read(REPO / "backend" / "app" / "bake" / "runtime_policy.py")
        self.assertIn("CONTENT_DOCLIB_POINTS_DOWNLOAD", rt)
        self.assertIn("docPointsDownload", rt)
        self.assertIn("followersOnlyComment", rt)
        for overlay in ("persistence-jpa", "persistence-mybatis"):
            root = (
                REPO
                / "skeletons"
                / "overlays"
                / overlay
                / "backend"
                / "src"
                / "main"
                / "java"
                / "com"
                / "thesis"
            )
            self.assertIn("spendPoints", _read(root / "capability" / "LoyaltyStore.java"))
            self.assertIn("configureCommentReport", _read(root / "capability" / "FavoriteStore.java"))
            self.assertIn("configureContentIslands", _read(root / "capability" / "ArchiveStore.java"))
            self.assertIn("configureFollowersOnly", _read(root / "service" / "ItemCommentStore.java"))

    def test_c09_sweep_forum_author_and_draft_autosave(self) -> None:
        forum = _spec("DOM-FORUM", "校园论坛交流管理系统", "")
        ft = (forum.get("schema") or {}).get("contentThicken") or {}
        fl = (forum.get("schema") or {}).get("labels") or {}
        self.assertTrue(ft.get("authorPage"))
        self.assertTrue(ft.get("draftBox"))
        self.assertTrue(ft.get("draftAutoSave"))
        self.assertIn("authorPageEntryLabel", fl)
        self.assertIn("draftAutoSaveHint", fl)
        blog = _spec("DOM-BLOG", "个人博客专栏管理系统", "")
        bt = (blog.get("schema") or {}).get("contentThicken") or {}
        self.assertTrue(bt.get("draftAutoSave"))
        self.assertTrue(bt.get("authorPage"))
        music = _spec("DOM-MUSIC", "校园曲库点播歌单管理系统", "")
        mt = (music.get("schema") or {}).get("contentThicken") or {}
        self.assertFalse(mt.get("draftAutoSave"))
        store = _read(BE / "capability" / "ArchiveStore.java")
        self.assertIn("updateUserDraft", store)
        ctrl = _read(BE / "controller" / "ArchiveController.java")
        self.assertIn("updateUserDraft", ctrl)
        browse = _read(FE / "views" / "user" / "ArchiveBrowse.vue")
        for needle in (
            "draftAutoSaveOn",
            "silentAutoSaveDraft",
            "publishDraftId",
            "draftAutoSaveHint",
            "authorPageOn",
        ):
            self.assertIn(needle, browse, needle)
        for overlay in ("persistence-jpa", "persistence-mybatis"):
            ov = (
                REPO
                / "skeletons"
                / "overlays"
                / overlay
                / "backend"
                / "src"
                / "main"
                / "java"
                / "com"
                / "thesis"
                / "capability"
                / "ArchiveStore.java"
            )
            self.assertIn("updateUserDraft", _read(ov))

    def test_c08_frontend_islands(self) -> None:
        browse = _read(FE / "views" / "DocBrowse.vue")
        self.assertIn("pointsDownloadOn", browse)
        self.assertIn("downloadCostPoints", browse)
        admin = _read(FE / "views" / "admin" / "DocFilesAdmin.vue")
        self.assertIn("downloadCostPoints", admin)
        self.assertIn("pointsDownloadOn", admin)
        ab = _read(FE / "views" / "user" / "ArchiveBrowse.vue")
        for needle in (
            "reportReasonDictOn",
            "commentReportOn",
            "followersOnlyCommentOn",
            "itemCommentFollowersOnly",
            "toggleFollowUser",
            "/api/user-follow",
            "reportReasonCode",
        ):
            self.assertIn(needle, ab, needle)
        rules = _read(FE / "views" / "user" / "PointsRules.vue")
        self.assertIn("pointsRulesPageTitle", rules)
        router = _read(FE / "router" / "index.js")
        self.assertIn("points-rules", router)
        self.assertIn("PointsRules.vue", router)
        menus = _read(FE / "utils" / "menuRoutes.js")
        self.assertIn("points_rules", menus)


if __name__ == "__main__":
    unittest.main()
