"""条下评论 item_comment：扫词开；≠ guestbook；MEDIA/MUSIC/BLOG。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES
from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_sql import domain_sql
from app.bake.features.guestbook import GUESTBOOK_CAP, scan_guestbook
from app.bake.features.item_comment import (
    ITEM_COMMENT_CAP,
    merge_item_comment_capabilities,
    scan_item_comment,
)
from tests.helpers.normalize import normalize_sql

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "skeletons" / "baseline"


class ItemCommentTests(unittest.TestCase):
    def test_capability_registered(self) -> None:
        self.assertEqual(CAPABILITIES[ITEM_COMMENT_CAP]["status"], "implemented")
        for dom in ("DOM-MEDIA", "DOM-MUSIC", "DOM-BLOG"):
            self.assertNotIn(ITEM_COMMENT_CAP, DOMAIN_CAPABILITIES.get(dom) or [], dom)

    def test_scan_comment_not_guestbook(self) -> None:
        self.assertTrue(scan_item_comment("支持用户评论与收藏。"))
        self.assertTrue(scan_item_comment("片下评论区可发表影评。"))
        self.assertTrue(scan_item_comment("视频详情页下方可互动点评。"))
        self.assertTrue(scan_item_comment("文章底部开放读后评论。"))
        self.assertFalse(scan_item_comment("仅浏览播放与收藏。"))
        self.assertTrue(scan_guestbook("门户留言板与管理员回复。"))
        self.assertFalse(scan_item_comment("门户留言板与管理员回复。"))
        self.assertFalse(scan_guestbook("片下评论区可发表影评。"))

    def test_merge_domain_gate(self) -> None:
        media_caps = list(DOMAIN_CAPABILITIES["DOM-MEDIA"])
        bare = merge_item_comment_capabilities(
            media_caps, "浏览播放收藏。", domain="DOM-MEDIA"
        )
        self.assertNotIn(ITEM_COMMENT_CAP, bare)
        yes = merge_item_comment_capabilities(
            media_caps, "浏览播放；支持用户评论。", domain="DOM-MEDIA"
        )
        self.assertIn(ITEM_COMMENT_CAP, yes)

        lib = merge_item_comment_capabilities(
            list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
            "图书评论？",
            domain="DOM-LIBRARY",
        )
        self.assertNotIn(ITEM_COMMENT_CAP, lib)

        shop = merge_item_comment_capabilities(
            list(DOMAIN_CAPABILITIES["DOM-SHOP"]),
            "商品评论与评价。",
            domain="DOM-SHOP",
        )
        self.assertNotIn(ITEM_COMMENT_CAP, shop)

    def test_attach_accept_sql_fe_be(self) -> None:
        plain = attach_accept(
            {
                "domain": "DOM-MEDIA",
                "title": "影视点播",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-MEDIA"]),
                "archetype": "ARCH-CONTENT",
            },
            "校园影视点播浏览收藏。",
        )
        self.assertNotIn(ITEM_COMMENT_CAP, plain.get("capabilities") or [])
        self.assertIn(GUESTBOOK_CAP, plain.get("capabilities") or [])

        rich = attach_accept(
            {
                "domain": "DOM-MEDIA",
                "title": "影视点播",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-MEDIA"]),
                "archetype": "ARCH-CONTENT",
            },
            "校园影视点播；支持片下评论与收藏。",
        )
        caps = rich.get("capabilities") or []
        self.assertIn(ITEM_COMMENT_CAP, caps)
        menus = (rich.get("schema") or {}).get("menus", {}).get("admin") or []
        self.assertTrue(any(m.get("key") == "item_comments" for m in menus))
        labels = (rich.get("schema") or {}).get("labels") or {}
        self.assertEqual(labels.get("itemCommentSectionTitle"), "用户评论")
        gate = rich.get("gate") or {}
        self.assertIn("item_comment", (gate.get("flow_api") or {}))

        sql = domain_sql(
            "DOM-MEDIA",
            "thesis_media",
            capabilities=caps,
            proposal_text="校园影视点播；支持片下评论与收藏。",
        )
        n = normalize_sql(sql)
        self.assertIn("item_comment", n)
        self.assertIn("sys_guestbook", n)

        store = BASELINE / "backend/src/main/java/com/thesis/service/ItemCommentStore.java"
        ctrl = BASELINE / "backend/src/main/java/com/thesis/controller/ItemCommentController.java"
        admin = BASELINE / "frontend/src/views/admin/ItemCommentAdmin.vue"
        browse = BASELINE / "frontend/src/views/user/ArchiveBrowse.vue"
        self.assertTrue(store.is_file(), store)
        self.assertTrue(ctrl.is_file(), ctrl)
        self.assertTrue(admin.is_file(), admin)
        browse_txt = browse.read_text(encoding="utf-8")
        self.assertIn("item_comment", browse_txt)
        self.assertIn("/api/item-comments", browse_txt)
        self.assertIn("item-comments", browse_txt)

        overlay_mb = (
            ROOT
            / "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/service/ItemCommentStore.java"
        )
        overlay_jpa = (
            ROOT
            / "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/service/ItemCommentStore.java"
        )
        self.assertTrue(overlay_mb.is_file(), overlay_mb)
        self.assertTrue(overlay_jpa.is_file(), overlay_jpa)


if __name__ == "__main__":
    unittest.main()
