"""逻辑层去重契约：fragments 只转发；thicken/门禁共用壳。"""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app" / "bake"


class LogicDedupeContractTest(unittest.TestCase):
    def test_fragments_ensure_dm_delegates(self):
        src = (ROOT / "sql" / "fragments.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        fn = next(
            n
            for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "ensure_dm_sql"
        )
        body = ast.get_source_segment(src, fn) or ""
        self.assertIn("app.bake.features.dm", body)
        self.assertNotIn("_DM_DDL", body)

    def test_many_ensure_are_delegates(self):
        src = (ROOT / "sql" / "fragments.py").read_text(encoding="utf-8")
        names = [
            "ensure_guestbook_sql",
            "ensure_vote_sql",
            "ensure_favorites_sql",
            "ensure_blind_box_sql",
            "ensure_borrow_structural_sql",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertRegex(
                    src,
                    rf"def {name}\([\s\S]*?from app\.bake\.features\.\w+ import {name} as _ensure",
                )

    def test_thicken_common_used(self):
        common = (ROOT / "features" / "thicken_common.py").read_text(encoding="utf-8")
        self.assertIn("def live_schema", common)
        self.assertIn("def add_feature", common)
        for name in ("apply_thicken.py", "trade_thicken.py", "borrow_thicken.py"):
            src = (ROOT / "features" / name).read_text(encoding="utf-8")
            with self.subTest(mod=name):
                self.assertIn("thicken_common", src)
                self.assertNotIn("def _live_schema(", src)

    def test_gate_source_scan_shared(self):
        util = (ROOT / "gates" / "source_scan.py").read_text(encoding="utf-8")
        self.assertIn("def strip_vue_comments", util)
        for rel in ("gates/evaluate.py", "gates/semantic.py"):
            src = (ROOT / rel).read_text(encoding="utf-8")
            with self.subTest(mod=rel):
                self.assertIn("source_scan", src)
                self.assertNotIn("def _strip_vue_comments(", src)

    def test_ensure_dm_behavior(self):
        from app.bake.sql.fragments import ensure_dm_sql

        base = "CREATE TABLE IF NOT EXISTS sys_user (id INT);\n"
        out = ensure_dm_sql(base, enabled=True)
        self.assertIn("sys_dm_message", out)
        self.assertEqual(ensure_dm_sql(base, enabled=False), base)

    def test_fragments_no_dead_vote_bodies(self):
        """vote 正文只在 features.vote；fragments 不得再留 DDL/列常量。"""
        src = (ROOT / "sql" / "fragments.py").read_text(encoding="utf-8")
        for needle in (
            "_VOTE_CORE_DDL",
            "_VOTE_ACTIVITY_SEED",
            "VOTE_CANDIDATE_COLUMNS",
            "VOTE_CAMPAIGN_COLUMNS",
            "VOTE_BALLOT_COLUMNS",
        ):
            with self.subTest(needle=needle):
                self.assertNotIn(needle, src)

    def test_ensure_vote_injects_i10_columns(self):
        from app.bake.sql.fragments import ensure_vote_sql

        raw = """
CREATE TABLE IF NOT EXISTS vote_campaign (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL
);
CREATE TABLE IF NOT EXISTS vote_candidate (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  campaign_id BIGINT NOT NULL,
  name VARCHAR(128) NOT NULL
);
CREATE TABLE IF NOT EXISTS vote_ballot (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  campaign_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  candidate_id BIGINT NOT NULL
);
"""
        out = ensure_vote_sql(raw, enabled=True)
        for col in (
            "slogan",
            "anonymous",
            "daily_vote_limit",
            "allow_abstain",
            "client_ip",
            "abstain",
        ):
            with self.subTest(col=col):
                self.assertIn(col, out)


if __name__ == "__main__":
    unittest.main()
