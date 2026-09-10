"""能力扩岛 E-03：点赞 post_like（扫词）；举报 content_report（论坛行业默认）。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES
from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.favorites import (
    CONTENT_REPORT_CAP,
    POST_LIKE_CAP,
    merge_content_report_capabilities,
    merge_post_like_capabilities,
    scan_content_report,
    scan_post_like,
)
from tests.helpers.normalize import normalize_sql

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "skeletons" / "baseline"


class PostLikeReportE03Tests(unittest.TestCase):
    def test_capability_registered(self) -> None:
        self.assertEqual(CAPABILITIES[POST_LIKE_CAP]["status"], "implemented")
        self.assertEqual(CAPABILITIES[CONTENT_REPORT_CAP]["status"], "implemented")
        self.assertIn(CONTENT_REPORT_CAP, DOMAIN_CAPABILITIES.get("DOM-FORUM") or [])
        self.assertNotIn(POST_LIKE_CAP, DOMAIN_CAPABILITIES.get("DOM-FORUM") or [])
        for dom in ("DOM-DATING", "DOM-BLOG"):
            caps = DOMAIN_CAPABILITIES.get(dom) or []
            self.assertNotIn(POST_LIKE_CAP, caps, dom)
            self.assertNotIn(CONTENT_REPORT_CAP, caps, dom)

    def test_scan_terms(self) -> None:
        self.assertTrue(scan_post_like("论坛支持点赞与回帖。"))
        self.assertFalse(scan_post_like("论坛发帖回帖审核。"))
        self.assertTrue(scan_content_report("支持用户举报不良帖子。"))
        self.assertFalse(scan_content_report("论坛发帖回帖。"))

    def test_merge_like_scan_report_forum_default(self) -> None:
        bare = ["archive", "ticket_flow", "content", "org_users"]
        no = merge_post_like_capabilities(bare, "发帖回帖审帖。", domain="DOM-FORUM")
        self.assertNotIn(POST_LIKE_CAP, no)
        yes = merge_post_like_capabilities(
            bare, "发帖回帖；支持点赞。", domain="DOM-FORUM"
        )
        self.assertIn(POST_LIKE_CAP, yes)

        self.assertIn(
            CONTENT_REPORT_CAP,
            merge_content_report_capabilities(bare, "发帖回帖。", domain="DOM-FORUM"),
        )

        dating = list(DOMAIN_CAPABILITIES["DOM-DATING"])
        no_r = merge_content_report_capabilities(
            dating, "资料配对私信。", domain="DOM-DATING"
        )
        self.assertNotIn(CONTENT_REPORT_CAP, no_r)
        yes_r = merge_content_report_capabilities(
            dating, "资料配对；支持用户举报。", domain="DOM-DATING"
        )
        self.assertIn(CONTENT_REPORT_CAP, yes_r)

        lib = merge_post_like_capabilities(
            list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
            "图书点赞？",
            domain="DOM-LIBRARY",
        )
        self.assertNotIn(POST_LIKE_CAP, lib)

    def test_attach_accept_sql_yml_fe_be(self) -> None:
        plain = attach_accept(
            {
                "domain": "DOM-FORUM",
                "title": "校园论坛",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-FORUM"]),
                "archetype": "ARCH-CONTENT",
            },
            "校园论坛发帖回帖审帖。",
        )
        self.assertNotIn(POST_LIKE_CAP, plain.get("capabilities") or [])
        self.assertIn(CONTENT_REPORT_CAP, plain.get("capabilities") or [])
        menus0 = (plain.get("schema") or {}).get("menus", {}).get("admin") or []
        self.assertTrue(any(m.get("key") == "content_reports" for m in menus0))

        rich = attach_accept(
            {
                "domain": "DOM-FORUM",
                "title": "校园论坛",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-FORUM"]),
                "archetype": "ARCH-CONTENT",
            },
            "校园论坛发帖回帖；支持点赞与用户举报不良信息。",
        )
        caps = rich.get("capabilities") or []
        self.assertIn(POST_LIKE_CAP, caps)
        self.assertIn(CONTENT_REPORT_CAP, caps)
        labels = (rich.get("schema") or {}).get("labels") or {}
        self.assertEqual(labels.get("likeVerb"), "点赞")
        menus = (rich.get("schema") or {}).get("menus", {}).get("admin") or []
        self.assertTrue(any(m.get("key") == "content_reports" for m in menus))

        yml = _patch_thesis_yml("thesis:\n  domain: DOM-FORUM\n", "DOM-FORUM", rich)
        self.assertIn("post-like-enabled: true", yml)
        self.assertIn("content-report-enabled: true", yml)

        sql = domain_sql(
            "DOM-FORUM",
            "thesis_forum",
            capabilities=caps,
            proposal_text="校园论坛发帖回帖；支持点赞与用户举报不良信息。",
        )
        n = normalize_sql(sql)
        self.assertIn("user_post_like", n)
        self.assertIn("content_report", n)

    def test_baseline_files_exist(self) -> None:
        store = (
            BASELINE
            / "backend/src/main/java/com/thesis/capability/FavoriteStore.java"
        )
        ctrl = (
            BASELINE
            / "backend/src/main/java/com/thesis/controller/FavoriteController.java"
        )
        fe = BASELINE / "frontend/src/views/user/ArchiveBrowse.vue"
        admin = BASELINE / "frontend/src/views/admin/ContentReportsAdmin.vue"
        self.assertTrue(store.is_file())
        text = store.read_text(encoding="utf-8")
        self.assertIn("toggleLike", text)
        self.assertIn("submitReport", text)
        self.assertIn("resolveReport", text)
        ctext = ctrl.read_text(encoding="utf-8")
        self.assertIn("/api/likes/", ctext)
        self.assertIn("/api/content-reports", ctext)
        ftext = fe.read_text(encoding="utf-8")
        self.assertIn("post_like", ftext)
        self.assertIn("content_report", ftext)
        self.assertIn("toggleLike", ftext)
        self.assertTrue(admin.is_file())
        rtext = (BASELINE / "frontend/src/router/index.js").read_text(encoding="utf-8")
        self.assertIn("withContentReportRoutes", rtext)
        self.assertIn("ContentReportsAdmin", rtext)

    def test_unmounted_like_sql_has_no_like_table(self) -> None:
        plain = attach_accept(
            {
                "domain": "DOM-FORUM",
                "title": "校园论坛",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-FORUM"]),
                "archetype": "ARCH-CONTENT",
            },
            "校园论坛发帖回帖审帖。",
        )
        caps = plain.get("capabilities") or []
        sql = domain_sql(
            "DOM-FORUM",
            "thesis_forum",
            capabilities=caps,
            proposal_text="校园论坛发帖回帖审帖。",
        )
        n = normalize_sql(sql)
        self.assertNotIn("user_post_like", n)
        self.assertIn("content_report", n)

    def test_gate_merged_when_scanned(self) -> None:
        rich = attach_accept(
            {
                "domain": "DOM-FORUM",
                "title": "校园论坛",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-FORUM"]),
                "archetype": "ARCH-CONTENT",
            },
            "校园论坛发帖回帖；支持点赞与用户举报不良信息。",
        )
        gate = rich.get("gate") or {}
        flow = gate.get("flow_api") or {}
        self.assertIn("post_like", flow)
        self.assertIn("content_report", flow)
        segs = {r.get("seg") for r in (gate.get("routes") or []) if isinstance(r, dict)}
        self.assertIn("content-reports", segs)

    def test_baseline_reply_report_and_takedown(self) -> None:
        store = (
            BASELINE
            / "backend/src/main/java/com/thesis/capability/TicketStore.java"
        ).read_text(encoding="utf-8")
        self.assertIn("hideForReport", store)
        fav = (
            BASELINE
            / "backend/src/main/java/com/thesis/capability/FavoriteStore.java"
        ).read_text(encoding="utf-8")
        self.assertIn("hideForReport", fav)
        self.assertIn("ticket", fav)
        fe = (
            BASELINE / "frontend/src/views/user/ArchiveBrowse.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("openReport(r, 'ticket')", fe)
        self.assertIn("reportTargetType", fe)


if __name__ == "__main__":
    unittest.main()
