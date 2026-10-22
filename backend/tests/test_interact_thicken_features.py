"""互动/匹配组 interact_thicken：I-00～I-12（脚手架起；半截/域皮后续批次补钉）。"""

from __future__ import annotations

from tests._vue_src import vue_src

import unittest
from pathlib import Path

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_sql import domain_sql
from app.bake.features.interact_thicken import (
    INTERACT_DOMAINS,
    ensure_interact_thicken_sql,
)

REPO = Path(__file__).resolve().parents[2]
FE = REPO / "skeletons" / "baseline" / "frontend" / "src"
BE = REPO / "skeletons" / "baseline" / "backend" / "src" / "main" / "java" / "com" / "thesis"

_INTERACT_CASES: tuple[tuple[str, str, str], ...] = (
    ("DOM-DATING", "校园婚恋交友管理系统", "ARCH-FLOW"),
    ("DOM-MUTUAL-TUTOR", "导师学生双选管理系统", "ARCH-FLOW"),
    ("DOM-MUTUAL-TOPIC", "毕业设计选题双选系统", "ARCH-FLOW"),
    ("DOM-MUTUAL-TEAM", "竞赛组队匹配管理系统", "ARCH-FLOW"),
    ("DOM-CARPOOL", "校园拼车同行管理系统", "ARCH-FLOW"),
    ("DOM-TIMEBANK", "社区时间银行管理系统", "ARCH-FLOW"),
    ("DOM-EXAM", "在线考试刷题管理系统", "ARCH-CRUD"),
    ("DOM-SURVEY", "校园问卷调查管理系统", "ARCH-CRUD"),
    ("DOM-VOTE", "十佳评选投票管理系统", "ARCH-CRUD"),
)


def _spec(
    domain: str,
    title: str,
    body: str = "",
    *,
    archetype: str = "ARCH-FLOW",
) -> dict:
    return attach_accept(
        {
            "domain": domain,
            "title": title,
            "capabilities": list(DOMAIN_CAPABILITIES[domain]),
            "features": [],
            "archetype": archetype,
        },
        body,
    )


def _browse_src() -> str:
    """ArchiveBrowse 拆出 setup.js 后：模板在 .vue、逻辑在 .setup.js，断言须两处合读。"""
    base = FE / "views" / "user"
    return (base / "ArchiveBrowse.vue").read_text(encoding="utf-8") + (
        base / "ArchiveBrowse.setup.js"
    ).read_text(encoding="utf-8")


class InteractThickenFeatureTests(unittest.TestCase):
    def test_interact_domains_constant(self) -> None:
        self.assertEqual(
            INTERACT_DOMAINS,
            frozenset(
                {
                    "DOM-DATING",
                    "DOM-MUTUAL-TUTOR",
                    "DOM-MUTUAL-TOPIC",
                    "DOM-MUTUAL-TEAM",
                    "DOM-CARPOOL",
                    "DOM-TIMEBANK",
                    "DOM-EXAM",
                    "DOM-SURVEY",
                    "DOM-VOTE",
                }
            ),
        )

    def test_content_domains_untouched(self) -> None:
        for domain, title in (
            ("DOM-MEDIA", "点播课课程视频库管理系统"),
            ("DOM-FORUM", "校园表白墙树洞管理系统"),
            ("DOM-BLOG", "校园资讯院刊发布管理系统"),
        ):
            out = _spec(domain, title, "", archetype="ARCH-CONTENT")
            schema = out.get("schema") or {}
            self.assertFalse(schema.get("interactThicken"), domain)

    def test_trade_domains_untouched(self) -> None:
        for domain, title in (
            ("DOM-SHOP", "校园二手商城系统"),
            ("DOM-FOOD", "校园点餐配送系统"),
        ):
            out = _spec(domain, title, "", archetype="ARCH-TRADE")
            schema = out.get("schema") or {}
            self.assertFalse(schema.get("interactThicken"), domain)

    def test_reserve_domains_untouched(self) -> None:
        for domain, title in (
            ("DOM-HOSPITAL", "医院挂号预约系统"),
            ("DOM-MEETING", "会议室预约管理系统"),
        ):
            out = _spec(domain, title, "", archetype="ARCH-RESERVE")
            schema = out.get("schema") or {}
            self.assertFalse(schema.get("interactThicken"), domain)

    def test_i00_scaffold_on_nine_interact_domains(self) -> None:
        for domain, title, arch in _INTERACT_CASES:
            out = _spec(domain, title, "", archetype=arch)
            schema = out.get("schema") or {}
            thicken = schema.get("interactThicken") or {}
            self.assertTrue(thicken.get("core"), domain)
            self.assertFalse(schema.get("contentThicken"), domain)
            self.assertFalse(schema.get("tradeThicken"), domain)
            self.assertFalse(schema.get("reserveThicken"), domain)
            feats = out.get("features") or []
            self.assertIn("互动组加厚", feats)

    def test_i00_ensure_sql_noop_on_foreign_domain(self) -> None:
        base = "CREATE TABLE IF NOT EXISTS item (\n  id BIGINT PRIMARY KEY\n);\n"
        out = ensure_interact_thicken_sql(base, domain="DOM-SHOP", item_table="item")
        self.assertEqual(out, base)

    def test_i00_ensure_sql_noop_on_non_mutual_interact(self) -> None:
        """无 CREATE 块的互动域 ensure 仍原样；VOTE/SURVEY/EXAM 有专属 ensure。"""
        base = "CREATE TABLE IF NOT EXISTS item (\n  id BIGINT PRIMARY KEY\n);\n"
        out = ensure_interact_thicken_sql(
            base, domain="DOM-VOTE", item_table="item"
        )
        self.assertEqual(out, base)

    def test_i00_domain_sql_still_builds_for_interact(self) -> None:
        """挂 ensure 后互动域 SQL 仍可生成（冒烟）。"""
        sql = domain_sql("DOM-EXAM", "exam_db", "")
        self.assertIn("CREATE TABLE", sql)

    def test_i01_dating_favorites_heart_list(self) -> None:
        out = _spec("DOM-DATING", "校园婚恋交友管理系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("interactThicken") or {}
        labels = schema.get("labels") or {}
        caps = out.get("capabilities") or []
        self.assertIn("favorites", caps)
        self.assertTrue(thicken.get("datingFavorites"))
        self.assertEqual(labels.get("favoritesPageTitle"), "心动列表")
        self.assertEqual(labels.get("favoritesVerb"), "心动")
        self.assertIn("心动列表", out.get("features") or [])
        menus = (schema.get("menus") or {}).get("user") or []
        self.assertTrue(any(m.get("key") == "favorites" for m in menus if isinstance(m, dict)))
        browse = _browse_src()
        self.assertIn("datingFavorites", browse)
        self.assertIn("favoritesVerb", browse)
        fav = (FE / "views" / "user" / "MyFavorites.vue").read_text(encoding="utf-8")
        self.assertIn("favoritesEmptyTitle", fav)
        self.assertIn("favoritesCancelLabel", fav)

    def test_i01_carpool_timebank_allow_rating(self) -> None:
        for domain, title, flag, feat in (
            ("DOM-CARPOOL", "校园拼车同行管理系统", "carpoolRating", "拼车评价"),
            ("DOM-TIMEBANK", "社区时间银行管理系统", "timebankRating", "时间银行服务评价"),
        ):
            out = _spec(domain, title, "")
            schema = out.get("schema") or {}
            ticket = (schema.get("entities") or {}).get("ticket") or {}
            thicken = schema.get("interactThicken") or {}
            labels = schema.get("labels") or {}
            self.assertTrue(ticket.get("allowRating"), domain)
            self.assertTrue(thicken.get(flag), domain)
            self.assertIn(feat, out.get("features") or [])
            self.assertTrue(labels.get("rateInviteHint"), domain)
        tb = _spec("DOM-TIMEBANK", "社区时间银行管理系统", "")
        tsch = tb.get("schema") or {}
        self.assertTrue((tsch.get("interactThicken") or {}).get("timebankStarReputation"))
        self.assertEqual(
            (tsch.get("labels") or {}).get("timebankStarReputationLabel"),
            "星级信誉",
        )
        dash = (FE / "views" / "admin" / "TicketDashboard.vue").read_text(encoding="utf-8")
        self.assertIn("avgRatingLabel", dash)
        self.assertIn("timebankStarReputation", dash)
        mine = vue_src(FE / "views" / "user" / "MyTickets.vue")
        self.assertIn("rateInviteHint", mine)
        self.assertIn("allowRating", mine)

    def test_i01_mutual_deadline_countdown(self) -> None:
        for domain, title in (
            ("DOM-MUTUAL-TUTOR", "导师学生双选管理系统"),
            ("DOM-MUTUAL-TOPIC", "毕业设计选题双选系统"),
            ("DOM-MUTUAL-TEAM", "竞赛组队匹配管理系统"),
        ):
            out = _spec(domain, title, "")
            schema = out.get("schema") or {}
            thicken = schema.get("interactThicken") or {}
            labels = schema.get("labels") or {}
            archive = (schema.get("entities") or {}).get("archive") or {}
            fields = archive.get("fields") or []
            keys = {f.get("key") for f in fields if isinstance(f, dict)}
            self.assertIn("applyDeadlineAt", keys, domain)
            self.assertTrue(thicken.get("mutualDeadlineCountdown"), domain)
            self.assertEqual(labels.get("applyDeadlineLabel"), "志愿截止")
            self.assertIn("mutualDeadlineCountdownLabel", labels)
        base = "CREATE TABLE IF NOT EXISTS tutor (\n  id BIGINT PRIMARY KEY\n);\n"
        sql = ensure_interact_thicken_sql(
            base, domain="DOM-MUTUAL-TUTOR", item_table="tutor"
        )
        self.assertIn("apply_deadline_at", sql)
        baked = domain_sql("DOM-MUTUAL-TUTOR", "mutual_db", "")
        self.assertIn("apply_deadline_at", baked)
        browse = _browse_src()
        self.assertIn("mutualDeadlineCountdown", browse)
        self.assertIn("mutualDeadlineText", browse)
        mine = vue_src(FE / "views" / "user" / "MyTickets.vue")
        self.assertIn("mutualDeadlineCountdownOn", mine)
        self.assertIn("mutualDeadlineText", mine)

    def test_i01_exam_objective_grade_contract(self) -> None:
        out = _spec("DOM-EXAM", "在线考试刷题管理系统", "", archetype="ARCH-CRUD")
        schema = out.get("schema") or {}
        thicken = schema.get("interactThicken") or {}
        labels = schema.get("labels") or {}
        self.assertTrue(thicken.get("examObjectiveGradeContract"))
        self.assertIn("examObjectiveGradeHint", labels)
        self.assertIn("examObjectiveGradedLead", labels)
        self.assertIn("客观题自动判分口径", out.get("features") or [])
        take = (FE / "views" / "ExamTake.vue").read_text(encoding="utf-8")
        self.assertIn("examObjectiveGradedLead", take)
        self.assertIn("examObjectiveGradeHint", take)
        for label, root in (
            ("baseline", BE / "service" / "ExamStore.java"),
            (
                "mybatis",
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
                / "ExamStore.java",
            ),
            (
                "jpa",
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
                / "ExamStore.java",
            ),
        ):
            text = root.read_text(encoding="utf-8")
            # 批次号注释已按「学生包去工厂腔」清除，断言只看判分实现本身
            self.assertIn("scoreAnswer", text, label)
            self.assertIn("equalsIgnoreCase", text, label)

    def test_i02_dating_skin_flags_and_sql(self) -> None:
        out = _spec("DOM-DATING", "校园婚恋交友管理系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("interactThicken") or {}
        labels = schema.get("labels") or {}
        archive = (schema.get("entities") or {}).get("archive") or {}
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        for flag in (
            "datingProfileCompleteness",
            "datingUserFollow",
            "datingMeetIntent",
            "datingRejectReason",
            "datingIdealFilter",
            "datingBlacklist",
            "datingAlbumAudit",
            "datingActivityEntry",
        ):
            self.assertTrue(thicken.get(flag), flag)
        self.assertTrue(archive.get("userPublish"))
        self.assertTrue(archive.get("publishReview"))
        self.assertTrue(schema.get("applyBlacklist"))
        self.assertTrue(ticket.get("allowApplyBlacklist"))
        self.assertIn("gallery", out.get("capabilities") or [])
        for key in (
            "profileCompletenessLabel",
            "datingCompletenessHint",
            "followUserLabel",
            "meetIntentLabel",
            "rejectReasonLabel",
            "datingFilterCityPlaceholder",
            "applyBlacklistTitle",
            "albumAuditHiddenHint",
            "datingActivityEntryHint",
        ):
            self.assertTrue(labels.get(key), key)
        # 举报时限仅 content_report 已挂时
        self.assertFalse(thicken.get("datingReportDeadline"))
        with_report = _spec(
            "DOM-DATING",
            "校园婚恋交友管理系统",
            "用户可举报不当资料并由管理员按时处理",
        )
        # 扫词未必挂上 content_report；显式补 cap 验证加深枝
        caps = list(with_report.get("capabilities") or [])
        if "content_report" not in caps:
            caps.append("content_report")
            with_report["capabilities"] = caps
            from app.bake.features.interact_thicken import apply_interact_thicken_to_spec

            with_report = apply_interact_thicken_to_spec(with_report, "")
        wsch = with_report.get("schema") or {}
        self.assertTrue((wsch.get("interactThicken") or {}).get("datingReportDeadline"))
        self.assertGreater(int(wsch.get("reportHandleDays") or 0), 0)

        sql = domain_sql(
            "DOM-DATING",
            "dating_db",
            "",
            capabilities=list(out.get("capabilities") or []),
        )
        for col in (
            "owner_username",
            "reject_reason",
            "age_years",
            "ideal_city",
            "album_audit_status",
            "meet_intent",
            "user_follow",
        ):
            self.assertIn(col, sql, col)
        # 图集列由 gallery cap → ensure_gallery_sql，不在 interact ensure 里硬补
        self.assertIn("gallery", out.get("capabilities") or [])
        self.assertIn("gallery_json", sql)

        browse = _browse_src()
        for needle in (
            "datingUserFollowOn",
            "datingMeetIntentOn",
            "datingIdealFilterOn",
            "datingActivityEntryOn",
            "meetIntent",
            "datingCityFilter",
        ):
            self.assertIn(needle, browse, needle)
        profile = (FE / "views" / "Profile.vue").read_text(encoding="utf-8")
        self.assertIn("datingCompletenessOn", profile)
        self.assertIn("datingCompletenessHint", profile)
        admin = vue_src((FE / "views" / "admin" / "ArchiveAdmin.vue"))
        self.assertIn("datingRejectReasonOn", admin)
        self.assertIn("albumAudit", admin)
        mine = (FE / "views" / "user" / "MyArchive.vue").read_text(encoding="utf-8")
        self.assertIn("rejectReasonOf", mine)
        reports = (FE / "views" / "admin" / "ContentReportsAdmin.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn("reportDeadlineOn", reports)
        tickets = vue_src(FE / "views" / "user" / "MyTickets.vue")
        self.assertIn("meetIntentLabel", tickets)

        for label, root in (
            ("baseline", BE / "capability" / "ArchiveStore.java"),
            (
                "mybatis",
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
            ),
            (
                "jpa",
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
            ),
        ):
            text = root.read_text(encoding="utf-8")
            self.assertIn("rejectPublishItem(long id, String reason)", text, label)
            self.assertIn("setAlbumAuditStatus", text, label)
            self.assertIn("age_years", text, label)

        patch = (BE / "capability" / "TicketPatchOps.java").read_text(encoding="utf-8")
        self.assertIn("meetIntent", patch)
        self.assertIn("meet_intent", patch)

    def test_i03_mutual_tongshi_flags_sql_and_skeleton(self) -> None:
        for domain, title in (
            ("DOM-MUTUAL-TUTOR", "导师学生双选管理系统"),
            ("DOM-MUTUAL-TOPIC", "毕业设计选题双选系统"),
            ("DOM-MUTUAL-TEAM", "竞赛组队匹配管理系统"),
        ):
            out = _spec(domain, title, "")
            schema = out.get("schema") or {}
            thicken = schema.get("interactThicken") or {}
            labels = schema.get("labels") or {}
            ticket = (schema.get("entities") or {}).get("ticket") or {}
            archive = (schema.get("entities") or {}).get("archive") or {}
            for flag in (
                "mutualAdjustLog",
                "mutualEditBeforeDeadline",
                "mutualIntroPack",
                "mutualBlindPhase",
                "mutualWishMutex",
                "mutualResultPublicity",
                "mutualAdjustCap",
                "mutualPeerTimeoutReject",
                "mutualWishLock",
                "mutualResultExportNotify",
                "mutualInterviewEntry",
            ):
                self.assertTrue(thicken.get(flag), f"{domain}:{flag}")
            self.assertTrue(ticket.get("forceOnePerArchive"), domain)
            self.assertTrue(ticket.get("allowWishEditBeforeDeadline"), domain)
            self.assertTrue(ticket.get("blindPhaseUntilDeadline"), domain)
            self.assertTrue(ticket.get("allowPeerTimeoutReject"), domain)
            self.assertGreater(int(ticket.get("maxAdjustWishes") or 0), 0, domain)
            keys = {f.get("key") for f in (archive.get("fields") or []) if isinstance(f, dict)}
            self.assertIn("introPackUrl", keys, domain)
            menus = (schema.get("menus") or {}).get("user") or []
            self.assertTrue(
                any(isinstance(m, dict) and m.get("key") == "mutual_results" for m in menus),
                domain,
            )
            for key in (
                "mutualAdjustLogTitle",
                "mutualEditWishLabel",
                "introPackLabel",
                "mutualBlindPhaseHint",
                "onePerArchiveDenyMessage",
                "mutualResultTitle",
                "mutualAdjustCapDeny",
                "mutualPeerTimeoutHint",
                "mutualWishLockLabel",
                "mutualResultExportLabel",
                "mutualInterviewEntryHint",
            ):
                self.assertTrue(labels.get(key), f"{domain}:{key}")

        sql = domain_sql("DOM-MUTUAL-TUTOR", "mutual_db", "")
        self.assertIn("intro_pack_url", sql)
        self.assertIn("apply_deadline_at", sql)

        browse = _browse_src()
        for needle in (
            "mutualIntroPackOn",
            "introPackLabel",
            "mutualInterviewEntryOn",
            "mutualInterviewEntryHint",
        ):
            self.assertIn(needle, browse, needle)
        mine = vue_src(FE / "views" / "user" / "MyTickets.vue")
        for needle in (
            "mutualEditBeforeDeadlineOn",
            "canEditWish",
            "edit-wish",
            "mutualWishLockOn",
            "mutualWishLockLabel",
        ):
            self.assertIn(needle, mine, needle)
        peer = (FE / "views" / "user" / "PeerTickets.vue").read_text(encoding="utf-8")
        self.assertIn("mutualBlindPhaseOn", peer)
        self.assertIn("blindMasked", peer)
        results = (FE / "views" / "user" / "MutualResults.vue").read_text(encoding="utf-8")
        self.assertIn("mutual-match-result", results)
        self.assertIn("mutualResultTitle", results)
        records = (FE / "views" / "admin" / "TicketRecordsAdmin.vue").read_text(
            encoding="utf-8"
        )
        for needle in (
            "mutualAdjustLogOn",
            "adjust-log",
            "mutualResultExportNotifyOn",
            "mutual-result-notify",
        ):
            self.assertIn(needle, records, needle)
        routes = (FE / "utils" / "menuRoutes.js").read_text(encoding="utf-8")
        self.assertIn("mutual_results", routes)

        derive = (BE / "capability" / "TicketDeriveOps.java").read_text(encoding="utf-8")
        for needle in (
            "editWishBeforeDeadline",
            "autoRejectStalePeerPending",
            "mutualMatchResult",
            "pageAdjustLog",
            "maybeAppendAdminAdjust",
            "applyBlindRedaction",
        ):
            self.assertIn(needle, derive, needle)
        ctrl = (BE / "controller" / "TicketController.java").read_text(encoding="utf-8")
        for needle in (
            "edit-wish",
            "mutual-match-result",
            "adjust-log",
            "mutual-result-notify",
        ):
            self.assertIn(needle, ctrl, needle)
        jobs = (BE / "config" / "DemoScheduleJobs.java").read_text(encoding="utf-8")
        self.assertIn("autoRejectStalePeerPending", jobs)

        for label, root in (
            ("baseline", BE / "capability" / "TicketStore.java"),
            (
                "mybatis",
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
                / "TicketStore.java",
            ),
            (
                "jpa",
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
                / "TicketStore.java",
            ),
        ):
            text = root.read_text(encoding="utf-8")
            self.assertIn("editWishBeforeDeadline", text, label)
            self.assertIn("autoRejectStalePeerPending", text, label)
            self.assertIn("pageAdjustLog", text, label)

        for label, root in (
            ("baseline", BE / "capability" / "ArchiveStore.java"),
            (
                "mybatis",
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
            ),
            (
                "jpa",
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
            ),
        ):
            text = root.read_text(encoding="utf-8")
            self.assertIn("intro_pack_url", text, label)
            self.assertIn("introPackUrl", text, label)

    def test_i04_mutual_tutor_team_skin(self) -> None:
        tutor = _spec("DOM-MUTUAL-TUTOR", "导师学生双选管理系统", "")
        tsch = tutor.get("schema") or {}
        tth = tsch.get("interactThicken") or {}
        tlab = tsch.get("labels") or {}
        tticket = (tsch.get("entities") or {}).get("ticket") or {}
        self.assertTrue(tth.get("mutualTutorQuotaBar"))
        self.assertTrue(tth.get("tutorMutualRating"))
        self.assertTrue(tticket.get("allowRating"))
        self.assertEqual(tlab.get("ratingLabel"), "师生互评")
        self.assertIn("tutorQuotaBarLabel", tlab)
        self.assertIn("导师学生名额占用进度条", tutor.get("features") or [])
        self.assertIn("双选导师学生互评", tutor.get("features") or [])

        team = _spec("DOM-MUTUAL-TEAM", "竞赛组队匹配管理系统", "")
        sch = team.get("schema") or {}
        th = sch.get("interactThicken") or {}
        lab = sch.get("labels") or {}
        ticket = (sch.get("entities") or {}).get("ticket") or {}
        archive = (sch.get("entities") or {}).get("archive") or {}
        for flag in (
            "mutualTeamSkillTags",
            "mutualTeamInvite",
            "mutualTeamFullClose",
            "mutualTeamRemarkRequired",
            "mutualTeamExitNeedOwner",
            "mutualTeamSkillMatch",
        ):
            self.assertTrue(th.get(flag), flag)
        self.assertTrue(ticket.get("requireRemark"))
        keys = {f.get("key") for f in (archive.get("fields") or []) if isinstance(f, dict)}
        self.assertIn("skillTags", keys)
        self.assertIn("stage", keys)
        for key in (
            "skillTagsLabel",
            "teamInviteLabel",
            "teamExitRequestLabel",
            "teamSkillMatchLabel",
            "teamFullStageHint",
        ):
            self.assertTrue(lab.get(key), key)

        sql_tutor = domain_sql("DOM-MUTUAL-TUTOR", "mutual_db", "")
        self.assertIn("quota_cap", sql_tutor)
        sql_team = domain_sql("DOM-MUTUAL-TEAM", "mutual_db", "")
        self.assertIn("skill_tags", sql_team)
        self.assertIn("exit_request", sql_team)

        browse = _browse_src()
        for needle in (
            "tutorQuotaBarOn",
            "teamSkillTagsOn",
            "teamInviteOn",
            "teamSkillMatchOn",
            "filteredList",
            "team-invite",
        ):
            self.assertIn(needle, browse, needle)
        mine = vue_src(FE / "views" / "user" / "MyTickets.vue")
        self.assertIn("canRequestTeamExit", mine)
        self.assertIn("request-exit", mine)
        peer = (FE / "views" / "user" / "PeerTickets.vue").read_text(encoding="utf-8")
        self.assertIn("exit-inbox", peer)
        self.assertIn("peer-exit-respond", peer)
        self.assertIn("teamExitNeedOwnerOn", peer)

        derive = (BE / "capability" / "TicketDeriveOps.java").read_text(encoding="utf-8")
        for needle in (
            "sendTeamInvite",
            "requestTeamExit",
            "peerExitRespond",
            "pageExitInbox",
        ):
            self.assertIn(needle, derive, needle)
        for label, root in (
            ("baseline", BE / "capability" / "ArchiveStore.java"),
            (
                "mybatis",
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
            ),
            (
                "jpa",
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
            ),
        ):
            text = root.read_text(encoding="utf-8")
            self.assertIn("招募中", text, label)
            self.assertIn("已满员", text, label)
            self.assertIn("skill_tags", text, label)
            self.assertIn("quota_cap", text, label)

    def test_i05_carpool_skin(self) -> None:
        spec = _spec("DOM-CARPOOL", "高校校园拼车行程与同行意向对接系统", "")
        sch = spec.get("schema") or {}
        th = sch.get("interactThicken") or {}
        lab = sch.get("labels") or {}
        archive = (sch.get("entities") or {}).get("archive") or {}
        for flag in (
            "carpoolFullClose",
            "carpoolSeatRemain",
            "carpoolCampusDict",
            "carpoolViaPoints",
            "carpoolShareNote",
            "carpoolPrefNote",
            "carpoolLuggage",
            "carpoolAaCalc",
            "carpoolDepartRemind",
            "carpoolSeatLock",
            "carpoolCancelPenalty",
            "carpoolPhoneMaskAfterRate",
            "carpoolDupTripCheck",
            "carpoolRating",
        ):
            self.assertTrue(th.get(flag), flag)
        keys = {f.get("key") for f in (archive.get("fields") or []) if isinstance(f, dict)}
        for key in (
            "stage",
            "startCampus",
            "endCampus",
            "viaPoints",
            "shareNote",
            "prefNote",
            "luggageCount",
            "fareTotalYuan",
            "remindBeforeMinutes",
        ):
            self.assertIn(key, keys, key)
        for key in (
            "carpoolFullStageHint",
            "carpoolSeatRemainLabel",
            "carpoolCampusOptions",
            "viaPointsLabel",
            "shareNoteLabel",
            "prefNoteLabel",
            "luggageCountLabel",
            "fareTotalLabel",
            "carpoolAaLabel",
            "carpoolDepartRemindLeadLabel",
            "carpoolSeatLockedLabel",
            "carpoolCancelPenaltyLabel",
            "carpoolPhoneMaskedHint",
            "carpoolDupTripDeny",
        ):
            self.assertTrue(lab.get(key), key)
        self.assertIn("意向人数满自动关闭行程", spec.get("features") or [])
        self.assertIn("拼车费用AA计算器", spec.get("features") or [])

        sql = domain_sql(
            "DOM-CARPOOL",
            "t_carpool",
            title="高校校园拼车行程与同行意向对接系统",
            proposal_text="拼车行程同行意向对接",
        )
        for col in (
            "start_campus",
            "end_campus",
            "via_points",
            "share_note",
            "pref_note",
            "luggage_count",
            "fare_total_yuan",
            "remind_before_minutes",
            "depart_reminded_at",
            "seat_locked",
            "no_show",
        ):
            self.assertIn(col, sql, col)

        browse = _browse_src()
        for needle in (
            "carpoolSeatRemainOn",
            "carpoolCampusDictOn",
            "carpoolViaPointsOn",
            "carpoolAaCalcOn",
            "carpoolDepartRemindOn",
            "aaPerPerson",
            "publishStartCampus",
            "carpoolDupTripDeny",
        ):
            self.assertIn(needle, browse, needle)
        mine = vue_src(FE / "views" / "user" / "MyTickets.vue")
        for needle in (
            "canCancelLockedSeat",
            "carpoolSeatLockOn",
            "carpoolCancelPenaltyOn",
            "carpoolPhoneMaskAfterRateOn",
            "carpoolNoShowCountLabel",
        ):
            self.assertIn(needle, mine, needle)
        admin = vue_src((FE / "views" / "admin" / "ArchiveAdmin.vue"))
        self.assertIn("carpoolCampusDictOn", admin)
        self.assertIn("carpoolCampusOptions", admin)

        derive = (BE / "capability" / "TicketDeriveOps.java").read_text(encoding="utf-8")
        self.assertIn("seat_locked", derive)
        store = (BE / "capability" / "TicketStore.java").read_text(encoding="utf-8")
        self.assertIn("listApprovedUsernamesForItem", store)
        self.assertIn("lockedCancel", store)
        for label, root in (
            ("baseline", BE / "capability" / "ArchiveStore.java"),
            (
                "mybatis",
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
            ),
            (
                "jpa",
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
            ),
        ):
            text = root.read_text(encoding="utf-8")
            self.assertIn("remindDepartSweep", text, label)
            self.assertIn("assertNoDuplicateCarpoolTrip", text, label)
            self.assertIn("start_campus", text, label)
            self.assertIn("fare_total_yuan", text, label)

    def test_i06_timebank_skin(self) -> None:
        spec = _spec("DOM-TIMEBANK", "社区时间银行管理系统", "")
        sch = spec.get("schema") or {}
        th = sch.get("interactThicken") or {}
        lab = sch.get("labels") or {}
        archive = (sch.get("entities") or {}).get("archive") or {}
        ticket = (sch.get("entities") or {}).get("ticket") or {}
        for flag in (
            "timebankRank",
            "timebankLedgerExport",
            "timebankSkillCert",
            "timebankCatalog",
            "timebankCreditScore",
            "timebankPublishReview",
            "timebankFreeze",
            "timebankSkillAttach",
            "timebankAppeal",
            "timebankTransfer",
            "timebankClearRule",
        ):
            self.assertTrue(th.get(flag), flag)
        self.assertTrue(archive.get("userPublish"))
        self.assertTrue(archive.get("publishReview"))
        self.assertTrue(ticket.get("requireAttach"))
        for key in (
            "tbRankTitle",
            "tbLedgerExportLabel",
            "tbSkillTagsLabel",
            "tbSkillCertifiedLabel",
            "tbCatalogTitle",
            "tbCreditScoreLabel",
            "tbPublishReviewHint",
            "tbFrozenHoursLabel",
            "tbSkillAttachHint",
            "tbAppealTitle",
            "tbTransferLabel",
            "tbClearRuleTitle",
        ):
            self.assertTrue(lab.get(key), key)
        feats = spec.get("features") or []
        for feat in (
            "时间银行时长排行榜",
            "兑换记录对账导出",
            "时间银行技能标签认证勾选",
            "时间银行兑换商品目录",
            "时间银行信用分（爽约扣分）",
            "时间银行发布须审",
            "时间银行时长冻结（纠纷）",
            "时间银行技能证明附件",
            "时间银行申诉单",
            "时间银行时长转让",
            "时间银行时长清零规则说明",
        ):
            self.assertIn(feat, feats, feat)
        menus = sch.get("menus") or {}
        user_keys = {m.get("key") for m in (menus.get("user") or []) if isinstance(m, dict)}
        admin_keys = {m.get("key") for m in (menus.get("admin") or []) if isinstance(m, dict)}
        for key in ("tb_rank", "tb_catalog", "tb_appeal"):
            self.assertIn(key, user_keys, key)
        for key in ("tb_catalog_admin", "tb_appeal_admin"):
            self.assertIn(key, admin_keys, key)

        sql = domain_sql(
            "DOM-TIMEBANK",
            "t_timebank",
            title="社区时间银行管理系统",
            proposal_text="时间银行时长账户核销",
        )
        for needle in (
            "skill_certified",
            "credit_score",
            "frozen_hours",
            "CREATE TABLE IF NOT EXISTS tb_catalog",
            "CREATE TABLE IF NOT EXISTS tb_appeal",
            "CREATE TABLE IF NOT EXISTS tb_clear_rule",
        ):
            self.assertIn(needle, sql, needle)

        routes = (FE / "utils" / "menuRoutes.js").read_text(encoding="utf-8")
        for needle in (
            "tb_rank",
            "tb_catalog",
            "tb_appeal",
            "tb_catalog_admin",
            "tb_appeal_admin",
        ):
            self.assertIn(needle, routes, needle)
        for rel in (
            "views/TimebankRank.vue",
            "views/TimebankCatalog.vue",
            "views/TimebankAppeal.vue",
            "views/admin/TimebankCatalogAdmin.vue",
            "views/admin/TimebankAppealsAdmin.vue",
            "views/TimebankAccount.vue",
            "views/admin/TimebankAccountsAdmin.vue",
        ):
            text = (FE / rel).read_text(encoding="utf-8")
            self.assertTrue(text.strip(), rel)

        account = (FE / "views" / "TimebankAccount.vue").read_text(encoding="utf-8")
        for needle in (
            "timebankTransfer",
            "timebankClearRule",
            "timebankCreditScore",
            "timebankFreeze",
            "/api/timebank/transfer",
            "/api/timebank/clear-rule",
        ):
            self.assertIn(needle, account, needle)
        ledger_admin = (FE / "views" / "admin" / "TimebankLedgerAdmin.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn("timebankLedgerExport", ledger_admin)
        self.assertIn("tbLedgerExportLabel", ledger_admin)
        self.assertIn("/api/timebank/admin/ledger/export", ledger_admin)
        ctrl = (BE / "controller" / "TimebankController.java").read_text(encoding="utf-8")
        for needle in (
            "rankByHours",
            "exportLedgerCsv",
            "listCatalog",
            "submitAppeal",
            "adjustFreeze",
            "transfer",
            "getClearRule",
        ):
            self.assertIn(needle, ctrl, needle)
        for label, root in (
            ("baseline", BE / "service" / "TimebankStore.java"),
            (
                "mybatis",
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
                / "TimebankStore.java",
            ),
            (
                "jpa",
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
                / "TimebankStore.java",
            ),
        ):
            text = root.read_text(encoding="utf-8")
            self.assertIn("rankByHours", text, label)
            self.assertIn("exportLedgerCsv", text, label)
            self.assertIn("penalizeCredit", text, label)
            self.assertIn("adjustFreeze", text, label)
            self.assertIn("transfer", text, label)
            self.assertIn("submitAppeal", text, label)
            self.assertIn("getClearRule", text, label)
            self.assertIn("skill_certified", text, label)
            self.assertIn("frozen_hours", text, label)
        for label, root in (
            ("baseline", BE / "capability" / "TicketStore.java"),
            (
                "mybatis",
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
                / "TicketStore.java",
            ),
            (
                "jpa",
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
                / "TicketStore.java",
            ),
        ):
            text = root.read_text(encoding="utf-8")
            self.assertIn("penalizeCredit", text, label)

    def test_i07_exam_rules(self) -> None:
        spec = _spec(
            "DOM-EXAM",
            "在线考试刷题管理系统",
            "",
            archetype="ARCH-CRUD",
        )
        sch = spec.get("schema") or {}
        th = sch.get("interactThicken") or {}
        lab = sch.get("labels") or {}
        for flag in (
            "examPracticeNoScore",
            "examBlurWarn",
            "examExplainAfterScore",
            "examShuffle",
            "examAnswerProgress",
            "examPassScore",
            "examPartialMulti",
            "examLockAfterSubmit",
            "examLateEnter",
            "examEntryCode",
            "examObjectiveGradeContract",
        ):
            self.assertTrue(th.get(flag), flag)
        opts = sch.get("examOpts") or {}
        self.assertTrue(opts.get("practice"), "practice")
        self.assertTrue(opts.get("explain"), "explain")
        for key in (
            "examPracticeNoScoreHint",
            "examBlurWarnLead",
            "examExplainAfterScoreLabel",
            "examShuffleQuestionsLabel",
            "examProgressLabel",
            "examPassScoreLabel",
            "examPartialMultiLabel",
            "examLockAfterSubmitLabel",
            "examLateEnterDeny",
            "examEntryCodeLabel",
        ):
            self.assertTrue(lab.get(key), key)
        feats = spec.get("features") or []
        for feat in (
            "练习模式不计分 / 不计次数",
            "考试防切屏提示（文案+失焦计数）",
            "成绩公布后可看解析开关",
            "试卷题目/选项乱序",
            "交卷前答题进度条",
            "考试及格线可配",
            "多选题部分得分规则",
            "考试交卷后不可修改开关",
            "考试迟到禁止进入（开考后 N 分）",
            "考试监考口令（入场码）",
        ):
            self.assertIn(feat, feats, feat)
        menus = sch.get("menus") or {}
        user_keys = {m.get("key") for m in (menus.get("user") or []) if isinstance(m, dict)}
        self.assertIn("exam_practice", user_keys)

        sql = domain_sql(
            "DOM-EXAM",
            "t_exam",
            title="在线考试刷题管理系统",
            proposal_text="在线考试刷题练习",
        )
        for needle in (
            "shuffle_questions",
            "shuffle_options",
            "explain_after_score",
            "partial_multi",
            "lock_after_submit",
            "open_at",
            "late_enter_min",
            "entry_code",
            "blur_count",
        ):
            self.assertIn(needle, sql, needle)

        take = (FE / "views" / "ExamTake.vue").read_text(encoding="utf-8")
        for needle in (
            "examAnswerProgress",
            "examBlurWarn",
            "/api/exam/attempts/",
            "blur",
            "progressPct",
            "practiceNoScoreHint",
        ):
            self.assertIn(needle, take, needle)
        papers = (FE / "views" / "ExamPapers.vue").read_text(encoding="utf-8")
        self.assertIn("entryCode", papers)
        self.assertIn("hasEntryCode", papers)
        admin = (FE / "views" / "admin" / "ExamPapersAdmin.vue").read_text(encoding="utf-8")
        for needle in (
            "shuffleQuestions",
            "partialMulti",
            "lockAfterSubmit",
            "lateEnterMin",
            "entryCode",
            "explainAfterScore",
            "passScore",
        ):
            self.assertIn(needle, admin, needle)
        ctrl = (BE / "controller" / "ExamController.java").read_text(encoding="utf-8")
        self.assertIn("entryCode", ctrl)
        self.assertIn("recordBlur", ctrl)
        for label, root in (
            ("baseline", BE / "service" / "ExamStore.java"),
            (
                "mybatis",
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
                / "ExamStore.java",
            ),
            (
                "jpa",
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
                / "ExamStore.java",
            ),
        ):
            text = root.read_text(encoding="utf-8")
            self.assertIn("recordBlur", text, label)
            self.assertIn("entryCode", text, label)
            self.assertIn("partialMulti", text, label)
            self.assertIn("lockAfterSubmit", text, label)
            self.assertIn("shuffleQuestions", text, label)
            self.assertIn("selfCheckScore", text, label)

    def test_i08_exam_bank_and_scores(self) -> None:
        spec = _spec(
            "DOM-EXAM",
            "在线考试刷题管理系统",
            "",
            archetype="ARCH-CRUD",
        )
        sch = spec.get("schema") or {}
        th = sch.get("interactThicken") or {}
        lab = sch.get("labels") or {}
        opts = sch.get("examOpts") or {}
        self.assertTrue(opts.get("wrongbook"), "wrongbook forced for I-08 export")
        for flag in (
            "examCertificate",
            "examWrongbookExport",
            "examQuestionImport",
            "examRandomDraw",
            "examMarkRubric",
            "examScoreImport",
            "examDifficulty",
        ):
            self.assertTrue(th.get(flag), flag)
        for key in (
            "examCertificateTitle",
            "examCertificatePrintLabel",
            "examWrongbookExportLabel",
            "examQuestionImportLabel",
            "examRandomDrawLabel",
            "examMarkRubricLabel",
            "examScoreImportLabel",
            "examDifficultyLabel",
        ):
            self.assertTrue(lab.get(key), key)
        feats = spec.get("features") or []
        for feat in (
            "考试及格证书页（固定模板 PDF）",
            "错题本导出",
            "考试题目导入 Word/Excel",
            "考试多卷随机抽题",
            "考试主观题评分细则字段",
            "考试成绩导入模板",
            "考试试卷难度标签",
        ):
            self.assertIn(feat, feats, feat)

        sql = domain_sql(
            "DOM-EXAM",
            "t_exam",
            title="在线考试刷题管理系统",
            proposal_text="在线考试刷题练习错题本",
        )
        self.assertIn("mark_rubric", sql)
        self.assertIn("difficulty", sql)
        self.assertIn("exam_wrongbook", sql)

        cert = (FE / "views" / "ExamCertificate.vue").read_text(encoding="utf-8")
        self.assertIn("/api/exam/attempts/", cert)
        self.assertIn("certificate", cert)
        self.assertIn("printCert", cert)
        wrong = (FE / "views" / "ExamWrongbook.vue").read_text(encoding="utf-8")
        self.assertIn("wrongbook/export", wrong)
        attempts = (FE / "views" / "ExamAttempts.vue").read_text(encoding="utf-8")
        self.assertIn("exam/certificate/", attempts)
        qadmin = (FE / "views" / "admin" / "ExamQuestionsAdmin.vue").read_text(encoding="utf-8")
        self.assertIn("markRubric", qadmin)
        self.assertIn("questions/import", qadmin)
        padmin = (FE / "views" / "admin" / "ExamPapersAdmin.vue").read_text(encoding="utf-8")
        self.assertIn("difficulty", padmin)
        self.assertIn("random-draw", padmin)
        self.assertIn("scores/import", padmin)
        madmin = (FE / "views" / "admin" / "ExamMarkAdmin.vue").read_text(encoding="utf-8")
        self.assertIn("markRubric", madmin)
        router = (FE / "router" / "index.js").read_text(encoding="utf-8")
        self.assertIn("exam/certificate/:id", router)
        ctrl = (BE / "controller" / "ExamController.java").read_text(encoding="utf-8")
        for needle in (
            "wrongbook/export",
            "questions/import",
            "random-draw",
            "scores/import",
            "certificate",
        ):
            self.assertIn(needle, ctrl, needle)
        for label, root in (
            ("baseline", BE / "service" / "ExamStore.java"),
            (
                "mybatis",
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
                / "ExamStore.java",
            ),
            (
                "jpa",
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
                / "ExamStore.java",
            ),
        ):
            text = root.read_text(encoding="utf-8")
            self.assertIn("exportWrongbookCsv", text, label)
            self.assertIn("importQuestionsCsv", text, label)
            self.assertIn("randomDrawToPaper", text, label)
            self.assertIn("importScoresCsv", text, label)
            self.assertIn("certificatePayload", text, label)
            self.assertIn("markRubric", text, label)
            self.assertIn("difficulty", text, label)

    def test_i09_survey_thicken(self) -> None:
        spec = _spec(
            "DOM-SURVEY",
            "校园问卷调查管理系统",
            "",
            archetype="ARCH-CRUD",
        )
        sch = spec.get("schema") or {}
        th = sch.get("interactThicken") or {}
        lab = sch.get("labels") or {}
        for flag in (
            "surveySchedule",
            "surveyAnonymous",
            "surveySkip",
            "surveyAnswerProgress",
            "surveyOnceOnly",
            "surveyRequired",
            "surveyMatrix",
            "surveyResultCharts",
            "surveyCloseRemind",
            "surveyDraft",
            "surveyShowIf",
            "surveyTargetOrg",
            "surveyThanks",
            "surveyRecycleCard",
        ):
            self.assertTrue(th.get(flag), flag)
        for key in (
            "surveyOpenAtLabel",
            "surveyAnonymousLabel",
            "surveySkipWhenLabel",
            "surveyProgressLabel",
            "surveyOnceOnlyLabel",
            "surveyRequiredLabel",
            "surveyMatrixLabel",
            "surveyChartTitle",
            "surveyRemindHoursLabel",
            "surveyDraftSaveLabel",
            "surveyShowWhenQidLabel",
            "surveyTargetOrgLabel",
            "surveyThanksTitle",
            "surveyRecycleCardLabel",
        ):
            self.assertTrue(lab.get(key), key)
        feats = spec.get("features") or []
        for feat in (
            "问卷开放/截止自动上下架",
            "问卷匿名填写开关",
            "问卷逻辑跳题（简单若选A则跳）",
            "交卷前答题进度条",
            "问卷每人限填一次",
            "问卷必答题标记与校验",
            "问卷矩阵题（简单表格题）",
            "问卷结果图表（柱/饼）",
            "问卷截止前提醒站内信",
            "问卷填写进度保存草稿",
            "问卷逻辑显示（显隐，非跳题）",
            "问卷投放对象按组织",
            "问卷填写后感谢页",
            "问卷回收率工作台卡片",
        ):
            self.assertIn(feat, feats, feat)

        sql = domain_sql(
            "DOM-SURVEY",
            "t_survey",
            title="校园问卷调查管理系统",
            proposal_text="问卷调查匿名跳题草稿",
        )
        self.assertIn("open_at", sql)
        self.assertIn("anonymous", sql)
        self.assertIn("skip_when_label", sql)
        self.assertIn("matrix_rows", sql)
        self.assertIn("survey_draft", sql)
        self.assertIn("survey_draft_answer", sql)
        self.assertNotIn("answers_json", sql)
        self.assertIn("survey_audience", sql)

        fill = (FE / "views" / "SurveyFill.vue").read_text(encoding="utf-8")
        self.assertIn("surveyAnswerProgress", fill)
        self.assertIn("saveDraft", fill)
        self.assertIn("matrix", fill)
        thanks = (FE / "views" / "SurveyThanks.vue").read_text(encoding="utf-8")
        self.assertIn("surveyThanksTitle", thanks)
        fadmin = (FE / "views" / "admin" / "SurveyFormsAdmin.vue").read_text(encoding="utf-8")
        self.assertIn("surveySchedule", fadmin)
        self.assertIn("skipWhenLabel", fadmin)
        self.assertIn("required", fadmin)
        sadmin = (FE / "views" / "admin" / "SurveyStatsAdmin.vue").read_text(encoding="utf-8")
        self.assertIn("echarts", sadmin)
        self.assertIn("surveyResultCharts", sadmin)
        dash = (FE / "views" / "admin" / "TicketDashboard.vue").read_text(encoding="utf-8")
        self.assertIn("surveyRecycleCards", dash)
        router = (FE / "router" / "index.js").read_text(encoding="utf-8")
        self.assertIn("survey/thanks/:id", router)
        ctrl = (BE / "controller" / "SurveyController.java").read_text(encoding="utf-8")
        for needle in (
            "listOpenForms",
            "updateFormSettings",
            "loadDraft",
            "saveDraft",
            "recycleCards",
            "/draft",
        ):
            self.assertIn(needle, ctrl, needle)
        jobs = (BE / "config" / "DemoScheduleJobs.java").read_text(encoding="utf-8")
        self.assertIn("scheduleOpenCloseSweep", jobs)
        self.assertIn("remindCloseSweep", jobs)
        for label, root in (
            ("baseline", BE / "service" / "SurveyStore.java"),
            (
                "mybatis",
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
                / "SurveyStore.java",
            ),
            (
                "jpa",
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
                / "SurveyStore.java",
            ),
        ):
            text = root.read_text(encoding="utf-8")
            self.assertIn("scheduleOpenCloseSweep", text, label)
            self.assertIn("remindCloseSweep", text, label)
            self.assertIn("saveDraft", text, label)
            self.assertIn("recycleCards", text, label)
            self.assertIn("updateFormSettings", text, label)
            self.assertIn("matrix", text, label)

    def test_i10_vote_thicken(self) -> None:
        spec = _spec(
            "DOM-VOTE",
            "校园投票评选管理系统",
            "",
            archetype="ARCH-CRUD",
        )
        sch = spec.get("schema") or {}
        th = sch.get("interactThicken") or {}
        lab = sch.get("labels") or {}
        for flag in (
            "voteResultExport",
            "voteIpHint",
            "votePoster",
            "voteCandidateIntro",
            "votePollRefresh",
            "voteDailyLimit",
            "voteAnonymous",
            "voteResultDelay",
            "voteSlogan",
            "voteRequireRealName",
            "voteAbstain",
            "voteTop3",
        ):
            self.assertTrue(th.get(flag), flag)
        for key in (
            "voteExportLabel",
            "votePosterTitle",
            "voteIntroLabel",
            "votePollSecondsLabel",
            "voteDailyLimitLabel",
            "voteAnonymousLabel",
            "voteResultPublishAtLabel",
            "voteSloganLabel",
            "voteRequireRealNameLabel",
            "voteAbstainLabel",
            "voteTop3Hint",
        ):
            self.assertTrue(lab.get(key), key)
        feats = spec.get("features") or []
        for feat in (
            "投票结果导出",
            "投票防刷：同 IP 提示（仅提示）",
            "十佳结果海报页（静态生成）",
            "投票候选人图文简介",
            "投票票数定时刷新（轮询）",
            "投票每人每天限票",
            "投票匿名开关",
            "投票结果对学生延迟公布",
            "投票候选人拉票文案字段",
            "投票禁刷：实名后可投",
            "投票弃权选项",
            "投票实时榜置顶前三",
        ):
            self.assertIn(feat, feats, feat)

        sql = domain_sql(
            "DOM-VOTE",
            "t_vote",
            title="校园投票评选管理系统",
            proposal_text="投票评选匿名限票",
        )
        self.assertIn("anonymous", sql)
        self.assertIn("daily_vote_limit", sql)
        self.assertIn("results_publish_at", sql)
        self.assertIn("allow_abstain", sql)
        self.assertIn("require_real_name", sql)
        self.assertIn("poll_seconds", sql)
        self.assertIn("slogan", sql)
        self.assertIn("client_ip", sql)
        self.assertIn("abstain", sql)

        cast = (FE / "views" / "VoteCast.vue").read_text(encoding="utf-8")
        self.assertIn("allowAbstain", cast)
        self.assertIn("pollSeconds", cast)
        self.assertIn("top3", cast)
        self.assertIn("vote/poster", cast)
        poster = (FE / "views" / "VotePoster.vue").read_text(encoding="utf-8")
        self.assertIn("votePosterTitle", poster)
        self.assertIn("top10", poster)
        radmin = (FE / "views" / "admin" / "VoteResultsAdmin.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn("exportCsv", radmin)
        self.assertIn("voteAnonymousLabel", radmin)
        self.assertIn("/settings", radmin)
        cadmin = (FE / "views" / "admin" / "VoteCandidatesAdmin.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn("slogan", cadmin)
        router = (FE / "router" / "index.js").read_text(encoding="utf-8")
        self.assertIn("vote/poster/:id", router)
        ctrl = (BE / "controller" / "VoteController.java").read_text(encoding="utf-8")
        for needle in (
            "exportResults",
            "updateSettings",
            "clientIp",
            "abstain",
            "/export",
            "/settings",
        ):
            self.assertIn(needle, ctrl, needle)
        for label, root in (
            ("baseline", BE / "service" / "VoteStore.java"),
            (
                "mybatis",
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
                / "VoteStore.java",
            ),
            (
                "jpa",
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
                / "VoteStore.java",
            ),
        ):
            text = root.read_text(encoding="utf-8")
            self.assertIn("exportResultsCsv", text, label)
            self.assertIn("updateCampaignSettings", text, label)
            self.assertIn("allowAbstain", text, label)
            self.assertIn("requireRealName", text, label)
            self.assertIn("ipHint", text, label)
            self.assertIn("slogan", text, label)

    def test_i11_cap_islands_when_hung(self) -> None:
        """I-11：仅已挂 favorites / dm / allowRating / content_report 时加深。"""
        dating = _spec("DOM-DATING", "校园婚恋交友管理系统", "")
        dsch = dating.get("schema") or {}
        dth = dsch.get("interactThicken") or {}
        dlab = dsch.get("labels") or {}
        self.assertIn("favorites", dating.get("capabilities") or [])
        self.assertIn("dm", dating.get("capabilities") or [])
        self.assertTrue(dth.get("favoritesIsland"))
        self.assertTrue(dth.get("dmIsland"))
        self.assertTrue(dlab.get("favShareHint"))
        self.assertTrue(dlab.get("dmPageLead"))
        self.assertIn("收藏岛加深（已挂 favorites）", dating.get("features") or [])
        self.assertIn("私信岛加深（已挂 dm）", dating.get("features") or [])
        # 未挂 content_report → 无举报时限岛
        self.assertFalse(dth.get("reportDeadlineIsland"))
        self.assertFalse(dth.get("datingReportDeadline"))

        with_report = _spec(
            "DOM-DATING",
            "校园婚恋交友管理系统",
            "用户可举报不良资料",
        )
        # attach_accept 未必扫 content_report；显式挂上验证 I-11 钩子
        caps = list(with_report.get("capabilities") or [])
        if "content_report" not in caps:
            caps.append("content_report")
            with_report["capabilities"] = caps
            from app.bake.features.interact_thicken import apply_interact_thicken_to_spec

            with_report = apply_interact_thicken_to_spec(with_report, "")
        wr_th = (with_report.get("schema") or {}).get("interactThicken") or {}
        self.assertTrue(wr_th.get("datingReportDeadline"))
        self.assertTrue(wr_th.get("reportDeadlineIsland"))

        carpool = _spec("DOM-CARPOOL", "校园拼车同行管理系统", "")
        csch = carpool.get("schema") or {}
        cth = csch.get("interactThicken") or {}
        clab = csch.get("labels") or {}
        self.assertTrue((csch.get("entities") or {}).get("ticket", {}).get("allowRating"))
        self.assertTrue(cth.get("ratingIsland"))
        self.assertTrue(clab.get("ratingAdminLead"))
        self.assertTrue(clab.get("ratingFilterRatedLabel"))
        self.assertIn("单据评价岛加深（已开 allowRating）", carpool.get("features") or [])
        # 拼车默认无 favorites → 不硬开收藏岛
        self.assertNotIn("favorites", carpool.get("capabilities") or [])
        self.assertFalse(cth.get("favoritesIsland"))

        fav = (FE / "views" / "user" / "MyFavorites.vue").read_text(encoding="utf-8")
        self.assertIn("favShareHint", fav)
        self.assertIn("exportList", fav)
        dm = (FE / "views" / "user" / "Dm.vue").read_text(encoding="utf-8")
        self.assertIn("dmPageLead", dm)
        records = (FE / "views" / "admin" / "TicketRecordsAdmin.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn("ratingFilterRatedLabel", records)
        self.assertIn("ratingAdminLead", records)
        reports = (FE / "views" / "admin" / "ContentReportsAdmin.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn("reportDeadlineIsland", reports)
        self.assertIn("reportDeadlineHint", reports)
