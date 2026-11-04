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

    def test_cross_domain_noun_in_faq_seed_is_caught(self):
        from app.bake.domain_vocab import faq_seed_findings, lexicon_findings
        from app.llm.agents_qa import _fallback_qa
        from app.services.delivery_review import apply_qa_to_gates

        sql = (
            "INSERT INTO sys_ai_knowledge (category, title, content, keywords, hit_count)\n"
            "SELECT '流程', '办事指引', '客户可在此提交挂号并跟踪进度', '挂号', 0\n"
            "FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_ai_knowledge WHERE title='办事指引');"
        )
        schema = SCHEMA_BUILDERS["DOM-CRM"]("测试课题")
        hits = faq_seed_findings(sql, schema, domain="DOM-CRM")
        self.assertTrue(any("挂号" in f["msg"] for f in hits), hits)
        self.assertTrue(all(f["level"] == "error" for f in hits))

        bundled = lexicon_findings(schema, domain="DOM-CRM", title="测试课题", seed_sql=sql)
        self.assertTrue(any("挂号" in f["msg"] for f in bundled), bundled)

        qa = _fallback_qa(
            {
                "domain": "DOM-CRM",
                "title": "测试课题",
                "schema": schema,
                "labels": schema.get("labels") or {},
                "menus": schema.get("menus") or {},
                "menuKeys": {},
                "entityKeys": list((schema.get("entities") or {}).keys()),
                "capabilities": [],
                "files": {},
                "missing_files": [],
                "seed_sql": sql,
                "proposal": "",
            }
        )
        self.assertFalse(qa.get("ok"), qa)
        gates = {"overall": True, "zip_allowed": True}
        apply_qa_to_gates(gates, qa, warn_blocks=False)
        self.assertFalse(gates["zip_allowed"])

    def test_faq_category_not_in_lookup_is_error(self):
        """有 category 种子时，FAQ 分类写表外名 → error 挡包。"""
        from app.bake.domain_vocab import faq_category_alignment_findings, lexicon_findings

        sql = (
            "INSERT IGNORE INTO category (id, name) VALUES "
            "(1, '重点客户'), (2, '普通客户'), (3, '潜在线索');\n"
            "INSERT INTO sys_ai_knowledge (category, title, content, keywords, hit_count)\n"
            "SELECT '挂号科', '错分类', '正文', 'x', 0\n"
            "FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_ai_knowledge LIMIT 1);"
        )
        hits = faq_category_alignment_findings(sql)
        self.assertTrue(any("挂号科" in f["msg"] for f in hits), hits)
        self.assertTrue(all(f["level"] == "error" for f in hits))

        schema = SCHEMA_BUILDERS["DOM-CRM"]("测试课题")
        bundled = lexicon_findings(schema, domain="DOM-CRM", title="测", seed_sql=sql)
        self.assertTrue(any("挂号科" in f["msg"] for f in bundled), bundled)

        ok_sql = (
            "INSERT IGNORE INTO category (id, name) VALUES "
            "(1, '重点客户'), (2, '普通客户'), (3, '潜在线索');\n"
            "INSERT INTO sys_ai_knowledge (category, title, content, keywords, hit_count)\n"
            "SELECT '重点客户', '重点客户怎么跟进', '在重点客户打开档案', 'x', 0\n"
            "FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_ai_knowledge LIMIT 1);"
        )
        self.assertEqual(faq_category_alignment_findings(ok_sql), [])


if __name__ == "__main__":
    unittest.main()
