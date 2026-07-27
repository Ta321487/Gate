"""泳道 E · C-04：投票评选 vote + DOM-VOTE。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES, resolve_accept
from app.bake.catalog import match_text
from app.bake.domain_schema import attach_accept, build_domain_schema, validate_schema
from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.vote import VOTE_CAP
from app.bake.menu_routes import shell_kind
from app.bake.schema.templates import SCHEMA_BUILDERS

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "data" / "samples" / "投票预设开题"
BASELINE = ROOT / "skeletons" / "baseline"


class VoteC04Tests(unittest.TestCase):
    def test_capability_and_domain(self) -> None:
        self.assertIn("vote", CAPABILITIES)
        self.assertEqual(CAPABILITIES["vote"]["status"], "implemented")
        self.assertIn("DOM-VOTE", DOMAINS)
        self.assertIn(VOTE_CAP, DOMAIN_CAPABILITIES["DOM-VOTE"])
        self.assertNotIn("ticket_flow", DOMAIN_CAPABILITIES["DOM-VOTE"])
        self.assertIn("DOM-VOTE", SCHEMA_BUILDERS)

    def test_match(self) -> None:
        got = match_text(
            "基于 Spring Boot 的高校校园十佳大学生投票评选系统的设计与实现。"
            "主要功能：候选人管理、在线投票、限票、结果公示。"
        )
        self.assertEqual(got.domain, "DOM-VOTE", f"hits={got.hits[:12]}")

    def test_neighbors(self) -> None:
        cases = [
            ("校园十佳大学生投票评选选票计票", "DOM-VOTE", "DOM-ACTIVITY"),
            ("社团活动报名审核占名额", "DOM-ACTIVITY", "DOM-VOTE"),
            ("满意度问卷调查填写回收统计", "DOM-SURVEY", "DOM-VOTE"),
        ]
        for phrase, want, avoid in cases:
            with self.subTest(phrase=phrase):
                got = match_text(f"基于 Spring Boot 的{phrase}系统的设计与实现")
                self.assertEqual(got.domain, want, f"hits={got.hits[:12]}")
                self.assertNotEqual(got.domain, avoid)

    def test_schema_and_shell(self) -> None:
        schema = build_domain_schema("高校校园十佳大学生投票评选系统", "DOM-VOTE")
        ok, errs = validate_schema(schema)
        self.assertTrue(ok, errs[:5])
        self.assertEqual(shell_kind(DOMAIN_CAPABILITIES["DOM-VOTE"]), "archive_only")
        spec = attach_accept(
            {
                "domain": "DOM-VOTE",
                "title": "高校校园十佳大学生投票评选系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-VOTE"]),
                "archetype": "ARCH-CRUD",
            },
            "候选人管理、在线投票、限票、结果公示。",
        )
        sch = spec.get("schema") or {}
        user_keys = {m.get("key") for m in (sch.get("menus") or {}).get("user") or []}
        admin_keys = {m.get("key") for m in (sch.get("menus") or {}).get("admin") or []}
        self.assertIn("vote_campaigns", user_keys)
        self.assertIn("vote_mine", user_keys)
        self.assertIn("vote_candidates", admin_keys)
        self.assertIn("vote_results", admin_keys)

    def test_sql_yml_accept(self) -> None:
        sql = domain_sql(
            "DOM-VOTE",
            "t_vote",
            title="高校校园十佳大学生投票评选系统",
            proposal_text="投票评选候选人计票公示",
        )
        for t in ("vote_campaign", "vote_candidate", "vote_ballot"):
            self.assertIn(t, sql)
        spec = attach_accept(
            {
                "domain": "DOM-VOTE",
                "title": "高校校园十佳大学生投票评选系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-VOTE"]),
                "archetype": "ARCH-CRUD",
            },
            "投票评选",
        )
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-VOTE", spec)
        self.assertIn("vote-enabled: true", yml)
        self.assertIn("enable-ticket: false", yml)
        d = resolve_accept(
            list(DOMAIN_CAPABILITIES["DOM-VOTE"]),
            "候选人；在线投票；结果公示。",
            has_domain_overlay=True,
            has_baseline_runtime=True,
            archetypes=["ARCH-CRUD"],
            domain="DOM-VOTE",
            primary_archetype="ARCH-CRUD",
        )
        self.assertEqual(d["accept"], "full", d)

    def test_runtime_files(self) -> None:
        self.assertTrue((BASELINE / "backend/src/main/java/com/thesis/service/VoteStore.java").is_file())
        self.assertTrue((BASELINE / "backend/src/main/java/com/thesis/controller/VoteController.java").is_file())
        self.assertTrue((BASELINE / "frontend/src/views/VoteCampaigns.vue").is_file())
        self.assertTrue((BASELINE / "frontend/src/views/admin/VoteResultsAdmin.vue").is_file())
        self.assertTrue(
            (
                ROOT
                / "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/mapper/VoteMapper.java"
            ).is_file()
        )

    def test_sample(self) -> None:
        path = SAMPLES / "C-04-DOM-VOTE-高校校园十佳大学生投票评选系统.txt"
        self.assertTrue(path.is_file(), path)


if __name__ == "__main__":
    unittest.main()
