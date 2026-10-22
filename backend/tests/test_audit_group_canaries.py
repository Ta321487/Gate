# -*- coding: utf-8 -*-
"""交付审计旧题回归：DOMAIN_GROUPS 每组代表匹配 + bake 交付物不红。

真源：``app.bake.domains.AUDIT_GROUP_CANARIES``（与 docs §3.1 #2 / 探针 --canary 对齐）。
人工小卡另核本轮邻域与触点域；本测钉住「组代表全域覆盖」机器底线。
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from app.bake.catalog import build_spec, match_text
from app.bake.domain_schema import validate_schema
from app.bake.domains import (
    AUDIT_GROUP_CANARIES,
    CLASSIC_AUDIT_CANARIES,
    DOMAIN_CAPABILITIES,
    DOMAIN_GROUPS,
    audit_group_canary_domains,
)
from app.bake.engine import assert_table_budget, domain_sql
from app.bake.schema.modules import iter_nodes, module_model
from app.bake.schema.testcases import build_testcase_rows
from app.bake.themes import default_theme

CORPUS = Path(__file__).resolve().parent / "fixtures" / "domain_opening_corpus.json"


def _slug_db(domain: str) -> str:
    return "gf_" + re.sub(r"[^a-z0-9]+", "_", domain.lower())[:40]


def _bake(text: str, filename: str = "") -> tuple[object, dict]:
    m = match_text(text, filename)
    title = (m.title or "").strip() or filename.replace(".txt", "") or "管理系统"
    theme = default_theme(m.domain) or ""
    spec = build_spec(
        title,
        m.archetype,
        m.domain,
        theme,
        False,
        "auto",
        float(m.confidence or 0.8),
        list(m.hits or []),
        proposal={"excerpt": text, "text": text},
        archetypes=list(m.archetypes or [m.archetype]),
    )
    return m, spec


class AuditGroupCanariesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        data = json.loads(CORPUS.read_text(encoding="utf-8"))
        cls.by_domain = {s["domain"]: s for s in data["samples"]}
        cls.generic = data["generic"]

    def test_canaries_cover_every_domain_group(self) -> None:
        group_ids = [gid for gid, _label, _members in DOMAIN_GROUPS]
        canary_groups = [gid for gid, _dom, _title in AUDIT_GROUP_CANARIES]
        self.assertEqual(canary_groups, group_ids, "组代表须与 DOMAIN_GROUPS 同序全覆盖")
        members = {gid: set(doms) for gid, _l, doms in DOMAIN_GROUPS}
        for gid, dom, title in AUDIT_GROUP_CANARIES:
            self.assertIn(dom, members[gid], f"{dom} 不属于组 {gid}（题={title}）")

    def test_classic_trio_subset_of_canaries(self) -> None:
        have = set(audit_group_canary_domains())
        missing = CLASSIC_AUDIT_CANARIES - have
        self.assertFalse(missing, f"经典金丝雀须在组代表内: {missing}")

    def test_each_canary_matches_and_bakes(self) -> None:
        """组代表：匹配对域 + accept full + schema/SQL/模块/测例可生成。"""
        for gid, want, title in AUDIT_GROUP_CANARIES:
            with self.subTest(group=gid, domain=want, title=title):
                if want == "DOM-GENERIC":
                    text = self.generic["text"]
                    sample_title = self.generic["title"]
                else:
                    sample = self.by_domain.get(want)
                    self.assertIsNotNone(sample, f"corpus 缺组代表缩样: {want}")
                    assert sample is not None
                    text = sample["text"]
                    sample_title = sample["title"]
                m, spec = _bake(text, f"{sample_title}.txt")
                self.assertEqual(m.domain, want, f"hits={m.hits[:12]}")
                self.assertEqual(spec.get("domain"), want)
                self.assertEqual(
                    spec.get("accept"),
                    "full",
                    f"reason={spec.get('accept_reason')}",
                )
                schema = spec.get("schema") or {}
                good, errs = validate_schema(schema)
                self.assertTrue(good, errs[:6])
                need = set(DOMAIN_CAPABILITIES.get(want) or [])
                caps = set(spec.get("capabilities") or [])
                self.assertTrue(need <= caps, f"缺域默认能力 {need - caps}")
                sql = domain_sql(
                    want,
                    _slug_db(want),
                    m.archetype,
                    list(m.archetypes or [m.archetype]),
                    capabilities=list(caps),
                    proposal_text=text,
                )
                assert_table_budget(sql, f"audit-canary-{want}")
                self.assertIn("CREATE TABLE", sql.upper())
                mod = module_model(
                    schema, proposal_text=text, title_fallback=sample_title
                )
                self.assertTrue(mod and iter_nodes(mod), mod)
                rows = build_testcase_rows(schema)
                self.assertGreaterEqual(len(rows), 3, rows[:2])

    def test_short_title_still_hits_canary_domain(self) -> None:
        """短题名（小卡抽查口径）也能落到组代表域，不抢邻组。"""
        for gid, want, title in AUDIT_GROUP_CANARIES:
            with self.subTest(group=gid, domain=want, title=title):
                m = match_text(title, f"{title}.txt")
                self.assertEqual(
                    m.domain,
                    want,
                    f"短题名串味: got={m.domain} hits={m.hits[:12]}",
                )


if __name__ == "__main__":
    unittest.main()
