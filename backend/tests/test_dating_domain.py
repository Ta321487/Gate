"""DOM-DATING：婚恋交友域注册与开题能力交叉。"""

from __future__ import annotations

import unittest

from app.bake.catalog import match_text
from app.bake.domain_schema import attach_accept, build_domain_schema
from app.bake.features.favorites import merge_favorites_capabilities
from app.bake.features.guestbook import merge_guestbook_capabilities
from app.bake.scene_scan import scene_dating, scene_for


class DatingDomainTests(unittest.TestCase):
    def test_match_prefers_dating_on_matchmaking(self) -> None:
        r = match_text("社区相亲交友管理系统", "红娘审核牵线意向，浏览会员资料。")
        self.assertEqual(r.domain, "DOM-DATING")
        self.assertEqual(r.archetype, "ARCH-FLOW")

    def test_scene_campus_vs_community(self) -> None:
        self.assertEqual(scene_dating("校园交友联谊"), "campus")
        self.assertEqual(scene_for("DOM-DATING", "相亲平台", "红娘牵线"), "community")
        schema = build_domain_schema(
            "校园交友系统",
            "DOM-DATING",
            proposal_text="大学生同学资料与学工牵线审核",
        )
        keys = {f["key"] for f in schema.get("profileFields") or []}
        self.assertIn("studentNo", keys)
        self.assertEqual(schema["labels"]["authEyebrow"], "校园交友")

    def test_favorites_only_when_proposal_mentions(self) -> None:
        base = ["archive", "ticket_flow", "content", "org_users"]
        plain = merge_favorites_capabilities(base, "", domain="DOM-DATING")
        self.assertNotIn("favorites", plain)
        with_fav = merge_favorites_capabilities(
            base, "支持我的收藏与收藏功能", domain="DOM-DATING"
        )
        self.assertIn("favorites", with_fav)

    def test_guestbook_when_proposal_mentions(self) -> None:
        base = ["archive", "ticket_flow", "content", "org_users"]
        plain = merge_guestbook_capabilities(base, "", domain="DOM-DATING")
        self.assertNotIn("guestbook", plain)
        with_gb = merge_guestbook_capabilities(
            base, "门户留言板咨询红娘", domain="DOM-DATING"
        )
        self.assertIn("guestbook", with_gb)

    def test_dm_default_on_dating(self) -> None:
        from app.bake.domains import DOMAIN_CAPABILITIES
        from app.bake.features.dm import merge_dm_capabilities

        self.assertIn("dm", DOMAIN_CAPABILITIES["DOM-DATING"])
        caps = merge_dm_capabilities(
            ["archive", "ticket_flow", "content", "org_users"],
            "",
            domain="DOM-DATING",
        )
        self.assertIn("dm", caps)

    def test_attach_accept_keeps_domain(self) -> None:
        schema = build_domain_schema("婚恋交友", "DOM-DATING")
        spec = {
            "domain": "DOM-DATING",
            "archetype": "ARCH-FLOW",
            "archetypes": ["ARCH-FLOW"],
            "schema": schema,
            "capabilities": ["archive", "ticket_flow", "content", "org_users"],
            "features": [],
            "gate": {},
        }
        out = attach_accept(
            spec,
            "会员资料牵线审核，并提供我的收藏与在线留言。",
        )
        self.assertEqual(out["domain"], "DOM-DATING")
        self.assertIn("favorites", out["capabilities"])
        self.assertIn("guestbook", out["capabilities"])


if __name__ == "__main__":
    unittest.main()
