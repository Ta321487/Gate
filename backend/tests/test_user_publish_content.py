"""内容壳 userPublish：BLOG/MEDIA 扫词开投稿；MUSIC 须点名用户上传。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_sql import domain_sql
from app.bake.features.user_publish import scan_user_publish
from app.bake.schema.builders_content import _blog_schema, _media_schema, _music_schema
from tests.helpers.normalize import normalize_sql


class UserPublishContentTests(unittest.TestCase):
    def test_scan_terms(self) -> None:
        self.assertTrue(scan_user_publish("支持读者投稿与收藏。", domain="DOM-BLOG"))
        self.assertTrue(scan_user_publish("用户投稿上传片源。", domain="DOM-MEDIA"))
        self.assertFalse(scan_user_publish("仅浏览收藏。", domain="DOM-BLOG"))
        self.assertFalse(scan_user_publish("读者投稿。", domain="DOM-MUSIC"))
        self.assertTrue(scan_user_publish("支持用户上传曲目。", domain="DOM-MUSIC"))

    def test_builders_default_off(self) -> None:
        for builder, dom in (
            (_blog_schema, "DOM-BLOG"),
            (_media_schema, "DOM-MEDIA"),
            (_music_schema, "DOM-MUSIC"),
        ):
            sch = builder("基于 Spring Boot 的测试系统", "仅浏览与收藏，不做投稿。")
            arch = (sch.get("entities") or {}).get("archive") or {}
            self.assertFalse(arch.get("userPublish"), dom)
            menus = (sch.get("menus") or {}).get("user") or []
            self.assertFalse(any(m.get("key") == "my_archive" for m in menus), dom)

    def test_blog_media_on_music_strict(self) -> None:
        blog = _blog_schema("博客系统", "读者可在线投稿发布文章，管理员可下架。")
        self.assertTrue(((blog.get("entities") or {}).get("archive") or {}).get("userPublish"))
        self.assertTrue(
            any(
                m.get("key") == "my_archive"
                for m in ((blog.get("menus") or {}).get("user") or [])
            )
        )
        self.assertEqual((blog.get("labels") or {}).get("publishCtaLabel"), "投稿")

        media = _media_schema("影视点播", "支持用户投稿上传播放链接。")
        self.assertTrue(((media.get("entities") or {}).get("archive") or {}).get("userPublish"))

        music_off = _music_schema("曲库", "浏览点播与收藏，征稿由管理员维护。")
        self.assertFalse(
            ((music_off.get("entities") or {}).get("archive") or {}).get("userPublish")
        )
        music_on = _music_schema("曲库", "支持用户上传曲目试听链接。")
        self.assertTrue(
            ((music_on.get("entities") or {}).get("archive") or {}).get("userPublish")
        )

    def test_attach_accept_sql_gate(self) -> None:
        plain = attach_accept(
            {
                "domain": "DOM-BLOG",
                "title": "博客",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-BLOG"]),
                "archetype": "ARCH-CONTENT",
            },
            "专栏浏览与收藏。",
        )
        arch0 = ((plain.get("schema") or {}).get("entities") or {}).get("archive") or {}
        self.assertFalse(arch0.get("userPublish"))

        rich = attach_accept(
            {
                "domain": "DOM-BLOG",
                "title": "博客",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-BLOG"]),
                "archetype": "ARCH-CONTENT",
            },
            "专栏浏览；支持读者投稿与条下评论。",
        )
        arch = ((rich.get("schema") or {}).get("entities") or {}).get("archive") or {}
        self.assertTrue(arch.get("userPublish"))
        flow = (rich.get("gate") or {}).get("flow_api") or {}
        self.assertIn("publish", flow)
        routes = (rich.get("gate") or {}).get("routes") or []
        self.assertTrue(any(r.get("seg") == "my-archive" for r in routes if isinstance(r, dict)))

        sql = domain_sql(
            "DOM-BLOG",
            "thesis_blog",
            capabilities=list(rich.get("capabilities") or []),
            proposal_text="专栏浏览；支持读者投稿与条下评论。",
            title="博客",
        )
        self.assertIn("owner_username", normalize_sql(sql))


if __name__ == "__main__":
    unittest.main()
