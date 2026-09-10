"""能力扩岛 E-12：帖子禁言 post_mute（论坛行业默认；博客仍扫词）。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES
from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.features.post_mute import (
    POST_MUTE_CAP,
    merge_post_mute_capabilities,
    scan_post_mute,
)

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "skeletons" / "baseline"


class PostMuteE12Tests(unittest.TestCase):
    def test_capability_registered_forum_default(self) -> None:
        self.assertEqual(CAPABILITIES[POST_MUTE_CAP]["status"], "implemented")
        self.assertIn(POST_MUTE_CAP, DOMAIN_CAPABILITIES.get("DOM-FORUM") or [])
        for dom in ("DOM-BLOG", "DOM-LIBRARY", "DOM-SHOP"):
            self.assertNotIn(POST_MUTE_CAP, DOMAIN_CAPABILITIES.get(dom) or [], dom)

    def test_scan_terms(self) -> None:
        self.assertTrue(scan_post_mute("支持禁言与禁言处罚。"))
        self.assertTrue(scan_post_mute("管理员可禁止发帖。"))
        self.assertFalse(scan_post_mute("发帖回帖与点赞举报。"))
        self.assertFalse(scan_post_mute("停用账号与启用状态。"))

    def test_merge_forum_default_blog_scan(self) -> None:
        bare = ["archive", "ticket_flow", "content", "org_users"]
        self.assertIn(
            POST_MUTE_CAP,
            merge_post_mute_capabilities(bare, "论坛发帖回帖审帖。", domain="DOM-FORUM"),
        )

        blog = list(DOMAIN_CAPABILITIES.get("DOM-BLOG") or bare)
        self.assertNotIn(
            POST_MUTE_CAP,
            merge_post_mute_capabilities(blog, "博客发帖回帖。", domain="DOM-BLOG"),
        )
        self.assertIn(
            POST_MUTE_CAP,
            merge_post_mute_capabilities(
                blog, "博客系统支持禁止发帖。", domain="DOM-BLOG"
            ),
        )

        lib = list(DOMAIN_CAPABILITIES["DOM-LIBRARY"])
        blocked = merge_post_mute_capabilities(lib, "禁言。", domain="DOM-LIBRARY")
        self.assertNotIn(POST_MUTE_CAP, blocked)

    def test_attach_accept_yml_and_labels(self) -> None:
        plain = attach_accept(
            {
                "domain": "DOM-FORUM",
                "title": "校园论坛",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-FORUM"]),
                "archetype": "ARCH-CONTENT",
            },
            "发帖回帖收藏私信。",
        )
        self.assertIn(POST_MUTE_CAP, plain.get("capabilities") or [])

        rich = attach_accept(
            {
                "domain": "DOM-FORUM",
                "title": "校园论坛",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-FORUM"]),
                "archetype": "ARCH-CONTENT",
            },
            "发帖回帖；支持禁言与禁言处罚。",
        )
        caps = rich.get("capabilities") or []
        self.assertIn(POST_MUTE_CAP, caps)
        labels = (rich.get("schema") or {}).get("labels") or {}
        self.assertEqual(labels.get("postMuteVerb"), "禁言")
        yml = _patch_thesis_yml("thesis:\n  domain: DOM-FORUM\n", "DOM-FORUM", rich)
        self.assertIn("post-mute-enabled: true", yml)

        plain_yml = _patch_thesis_yml("thesis:\n  domain: DOM-FORUM\n", "DOM-FORUM", plain)
        self.assertIn("post-mute-enabled: true", plain_yml)

    def test_baseline_sources_wired(self) -> None:
        user_store = (BASELINE / "backend/src/main/java/com/thesis/service/UserStore.java").read_text(
            encoding="utf-8"
        )
        self.assertIn("assertNotPostMuted", user_store)
        self.assertIn("setPostMuteUntil", user_store)
        self.assertIn("configurePostMute", user_store)

        admin = (
            BASELINE / "backend/src/main/java/com/thesis/controller/UsersAdminController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("post-mute", admin)

        archive = (
            BASELINE / "backend/src/main/java/com/thesis/capability/ArchiveStore.java"
        ).read_text(encoding="utf-8")
        self.assertIn("assertNotPostMuted", archive)

        ticket = (
            BASELINE / "backend/src/main/java/com/thesis/capability/TicketStore.java"
        ).read_text(encoding="utf-8")
        self.assertIn("assertNotPostMuted", ticket)

        fav = (
            BASELINE / "backend/src/main/java/com/thesis/capability/FavoriteStore.java"
        ).read_text(encoding="utf-8")
        self.assertIn("takedown_mute", fav)

        users_vue = (BASELINE / "frontend/src/views/admin/UsersAdmin.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn("post_mute", users_vue)
        self.assertIn("post-mute", users_vue)

        reports_vue = (
            BASELINE / "frontend/src/views/admin/ContentReportsAdmin.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("takedown_mute", reports_vue)
        self.assertIn("post_mute", reports_vue)

        binder = (
            BASELINE / "backend/src/main/java/com/thesis/config/DomainRuntimeBinder.java"
        ).read_text(encoding="utf-8")
        self.assertIn("post-mute-enabled", binder)
        self.assertIn("configurePostMute", binder)


if __name__ == "__main__":
    unittest.main()
