"""种子公告（sql/sys_notice）口径全量判据：所有具名域零命中。

种子公告由 `sql/domain_scene_seed.py` 等手写、随 DDL 插进学生包，是可见文案的
第四个来源；本测试把它纳入门禁（与 QA 的「交付质量摘要」同一函数）。
"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.domain_vocab import notice_slot_findings, seed_notices
from app.bake.engine import domain_sql
from app.bake.schema.templates import SCHEMA_BUILDERS

ROOT = Path(__file__).resolve().parents[2]


class SeedNoticeLexiconTests(unittest.TestCase):
    def test_all_domains_seed_notices_match_entity_wording(self):
        total = 0
        for domain, builder in sorted(SCHEMA_BUILDERS.items()):
            sql = domain_sql(domain, "thesis_test")
            notices = seed_notices(sql)
            total += len(notices)
            findings = notice_slot_findings(sql, builder("测试课题"), domain=domain)
            self.assertEqual(
                findings,
                [],
                f"{domain}: " + "；".join(f["msg"] for f in findings[:3]),
            )
        self.assertGreater(total, 60, "种子公告应覆盖各域，勿退化成空扫")

    def test_divergence_is_caught(self):
        """反例必红：把公告正文改成另一个簇词 → 必须报 error。"""
        sql = (
            "INSERT INTO sys_notice (title, content, p) "
            "SELECT '客户公告', '请尽快提交登记并等待确认。', 'admin'"
        )
        schema = SCHEMA_BUILDERS["DOM-CRM"]("测试课题")
        findings = notice_slot_findings(sql, schema, domain="DOM-CRM")
        self.assertTrue(findings)
        self.assertTrue(all(f["level"] == "error" for f in findings))

    def test_cross_domain_noun_in_notice_is_caught(self):
        sql = (
            "INSERT INTO sys_notice (title, content, p) "
            "SELECT '办公公告', '本周开始办理挂号与取药。', 'admin'"
        )
        schema = SCHEMA_BUILDERS["DOM-CRM"]("测试课题")
        findings = notice_slot_findings(sql, schema, domain="DOM-CRM")
        self.assertTrue(any("挂号" in f["msg"] for f in findings))


if __name__ == "__main__":
    unittest.main()
