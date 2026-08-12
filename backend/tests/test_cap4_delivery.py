"""能力四域 C-01/C-03/C-04/C-12：档案列、CTA、选题包与换说法抽检。"""

from __future__ import annotations

import unittest

from app.bake.archive_columns import archive_column_spec_for
from app.bake.catalog import match_text
from app.bake.engine_sql import domain_sql
from app.bake.guest_cta import CTA_BY_DOMAIN, pick_guest_login_cta
from app.bake.proposal_packs import PACKS
from app.bake.sample_proposal import build_sample_proposal
from app.bake.schema.er import collect_english_gaps, schema_model


class Cap4DeliveryTests(unittest.TestCase):
    def test_archive_columns_and_er(self) -> None:
        cases = {
            "DOM-EXAM": "exam_subject",
            "DOM-SURVEY": "survey_form",
            "DOM-VOTE": "vote_campaign",
            "DOM-DOCLIB": "doc_item",
        }
        for domain, table in cases.items():
            with self.subTest(domain=domain):
                expect = {
                    "DOM-EXAM": ("course_unit", "note_hint"),
                    "DOM-SURVEY": ("publish_unit", "note_hint"),
                    "DOM-VOTE": ("host_unit", "rule_note"),
                    "DOM-DOCLIB": ("publish_unit", "summary_note"),
                }[domain]
                (a, _), (i, _) = archive_column_spec_for(domain)
                self.assertEqual((a, i), expect)
                sql = domain_sql(domain, "thesis_test")
                self.assertIn(f"CREATE TABLE IF NOT EXISTS {table}", sql)
                self.assertIn(a, sql)
                self.assertIn(i, sql)
                self.assertNotIn("isbn VARCHAR", sql)
                gaps = [
                    c
                    for c in collect_english_gaps(schema_model(sql))["columns"]
                    if c.get("table") == table
                    and c.get("name") in ("dept_name", "note_hint", "subtitle", "detail", a, i)
                ]
                self.assertEqual(gaps, [], gaps)

    def test_cta_and_packs(self) -> None:
        for domain, pid in (
            ("DOM-EXAM", "exam"),
            ("DOM-SURVEY", "survey"),
            ("DOM-VOTE", "vote"),
            ("DOM-DOCLIB", "doclib"),
        ):
            with self.subTest(domain=domain):
                self.assertIn(domain, CTA_BY_DOMAIN)
                self.assertTrue(pick_guest_login_cta(domain, "C-01"))
                pack = next(p for p in PACKS if p["id"] == pid)
                self.assertEqual(pack["anchor_domain"], domain)
                # 选题包正文勿写「演示级」；整份开题模板仍可有「答辩必演示项」套话
                blob = " ".join(
                    str(pack.get(k) or "")
                    for k in ("problem", "value", "focus", "main_path", "features", "key_consistency")
                )
                self.assertNotIn("演示级", blob)
                sp = build_sample_proposal(pack_id=pid, seed=1)
                got = match_text(sp.text)
                self.assertEqual(got.domain, domain, f"hits={got.hits[:12]}")

    def test_neighbors_and_paraphrase(self) -> None:
        cases = [
            ("高校在线考试与题库管理", "DOM-EXAM", "DOM-SURVEY"),
            ("党建答题党史专题组卷", "DOM-EXAM", "DOM-PARTY"),
            ("满意度问卷调查填写回收统计", "DOM-SURVEY", "DOM-EVAL"),
            ("校园十佳投票评选选票计票", "DOM-VOTE", "DOM-ACTIVITY"),
            ("制度文件文库下载台账", "DOM-DOCLIB", "DOM-LIBRARY"),
            ("政策文件资料库下载", "DOM-DOCLIB", "DOM-BLOG"),
            ("图书馆图书借阅", "DOM-LIBRARY", "DOM-DOCLIB"),
            ("网上评教多维打分", "DOM-EVAL", "DOM-SURVEY"),
        ]
        for phrase, want, avoid in cases:
            with self.subTest(phrase=phrase):
                got = match_text(f"基于 Spring Boot 的{phrase}系统的设计与实现")
                self.assertEqual(got.domain, want, f"hits={got.hits[:12]}")
                self.assertNotEqual(got.domain, avoid)


if __name__ == "__main__":
    unittest.main()
