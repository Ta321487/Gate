"""泳道 E · C-11：活动报名 ∩ 投票评选（ACTIVITY + vote）。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import resolve_accept
from app.bake.catalog import match_text
from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.vote import VOTE_CAP, scan_vote_signup_composite

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples" / "投票预设开题"


class VoteSignupC11Tests(unittest.TestCase):
    def test_composite_scan(self) -> None:
        self.assertTrue(scan_vote_signup_composite("社团活动报名与优秀个人投票评选"))
        self.assertFalse(scan_vote_signup_composite("校园十佳大学生投票评选"))
        self.assertFalse(scan_vote_signup_composite("社团活动报名审核占名额"))

    def test_match_composite_prefers_activity(self) -> None:
        got = match_text(
            "基于 Spring Boot 的高校社团活动报名与优秀个人投票评选系统的设计与实现。"
            "主要功能：活动报名审核占名额；候选人投票与结果公示。"
        )
        self.assertEqual(got.domain, "DOM-ACTIVITY", f"hits={got.hits[:16]}")
        self.assertNotEqual(got.domain, "DOM-VOTE")

    def test_neighbors(self) -> None:
        cases = [
            ("校园十佳大学生投票评选选票计票", "DOM-VOTE"),
            ("社团活动报名审核占名额", "DOM-ACTIVITY"),
            ("社团活动报名与十佳投票评选", "DOM-ACTIVITY"),
        ]
        for phrase, want in cases:
            with self.subTest(phrase=phrase):
                got = match_text(f"基于 Spring Boot 的{phrase}系统的设计与实现")
                self.assertEqual(got.domain, want, f"hits={got.hits[:12]}")

    def test_attach_adds_vote_on_activity(self) -> None:
        body = "活动报名审核占名额；优秀个人投票评选与结果公示。"
        spec = attach_accept(
            {
                "domain": "DOM-ACTIVITY",
                "title": "高校社团活动报名与投票评选系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-ACTIVITY"]),
                "archetype": "ARCH-FLOW",
            },
            body,
        )
        caps = spec.get("capabilities") or []
        self.assertIn(VOTE_CAP, caps)
        self.assertIn("ticket_flow", caps)
        sch = spec.get("schema") or {}
        user_keys = {m.get("key") for m in (sch.get("menus") or {}).get("user") or []}
        self.assertIn("vote_campaigns", user_keys)
        self.assertIn("my_tickets", user_keys)

    def test_sql_yml(self) -> None:
        body = "活动报名与投票评选"
        sql = domain_sql(
            "DOM-ACTIVITY",
            "t_act_vote",
            title="高校社团活动报名与投票评选系统",
            proposal_text=body,
        )
        self.assertIn("activity", sql)
        self.assertIn("signup", sql)
        self.assertIn("vote_campaign", sql)
        self.assertIn("vote_ballot", sql)
        self.assertIn("活动优秀个人评选", sql)
        spec = attach_accept(
            {
                "domain": "DOM-ACTIVITY",
                "title": "高校社团活动报名与投票评选系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-ACTIVITY"]),
                "archetype": "ARCH-FLOW",
            },
            body,
        )
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-ACTIVITY", spec)
        self.assertIn("vote-enabled: true", yml)
        self.assertIn("enable-ticket: true", yml)

    def test_accept_full(self) -> None:
        caps = list(DOMAIN_CAPABILITIES["DOM-ACTIVITY"]) + [VOTE_CAP]
        d = resolve_accept(
            caps,
            "活动报名；投票评选；结果公示。",
            has_domain_overlay=True,
            has_baseline_runtime=True,
            archetypes=["ARCH-FLOW"],
            domain="DOM-ACTIVITY",
            primary_archetype="ARCH-FLOW",
        )
        self.assertEqual(d["accept"], "full", d)

    def test_sample(self) -> None:
        path = SAMPLES / "C-11-DOM-ACTIVITY-社团活动报名与优秀个人投票评选.txt"
        self.assertTrue(path.is_file(), path)


if __name__ == "__main__":
    unittest.main()
