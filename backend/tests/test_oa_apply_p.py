"""泳道 C/E：P-01～P-08 申请域；P-09～P-11 互选域。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.catalog import match_text
from app.bake.domain_schema import build_domain_schema, validate_schema
from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
from app.bake.oa_apply_p import MUTUAL_CASES, OA_APPLY_CASES, OA_MUTUAL_SKELETON
from app.bake.schema.followup_presets import FOLLOWUP_PRESETS
from app.bake.schema.templates import SCHEMA_BUILDERS

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples" / "申请预设开题"


class OaApplyPTests(unittest.TestCase):
    def test_domains_registered(self) -> None:
        for sid, _phrase, domain, _title in OA_APPLY_CASES:
            with self.subTest(id=sid):
                self.assertIn(domain, DOMAINS)
                self.assertIn(domain, DOMAIN_CAPABILITIES)
                self.assertIn(domain, FOLLOWUP_PRESETS)
                self.assertIn(domain, SCHEMA_BUILDERS)

    def test_all_p01_p08_hit_named_domain(self) -> None:
        self.assertEqual(len(OA_APPLY_CASES), 8)
        for sid, phrase, want, title in OA_APPLY_CASES:
            with self.subTest(id=sid, title=title):
                text = f"基于 Spring Boot 的{title}的设计与实现。主要功能：{phrase}。"
                got = match_text(text)
                self.assertEqual(got.domain, want, f"hits={got.hits[:10]}")

    def test_neighbors_do_not_steal(self) -> None:
        cases = [
            ("学校行政印章使用申请审批", "DOM-SEAL", "DOM-FUND"),
            ("公务用车申请审批管理", "DOM-FLEET", "DOM-PARKING"),
            ("在读成绩单在职证明开具申请", "DOM-CERT", "DOM-GRADE"),
            ("横幅海报户外宣传方案审批", "DOM-PROMO", "DOM-ACTIVITY"),
            ("装修进场施工备案申请审批", "DOM-FITOUT", "DOM-PROPERTY"),
            ("学籍异动转专业缓考申请审批", "DOM-ACAD", "DOM-GRADE"),
            ("出差加班申请审批与销结", "DOM-TRIP", "DOM-ATTEND"),
            ("经费差旅报销单填写与审批", "DOM-EXPENSE", "DOM-FUND"),
        ]
        for phrase, want, avoid in cases:
            with self.subTest(phrase=phrase):
                got = match_text(f"基于 Spring Boot 的{phrase}系统的设计与实现")
                self.assertEqual(got.domain, want, f"hits={got.hits[:10]}")
                self.assertNotEqual(got.domain, avoid)

    def test_sample_files_exist(self) -> None:
        self.assertTrue(SAMPLES.is_dir(), SAMPLES)
        for sid, _phrase, domain, title in [*OA_APPLY_CASES, *MUTUAL_CASES]:
            with self.subTest(id=sid):
                path = SAMPLES / f"{sid}-{domain}-{title}.txt"
                self.assertTrue(path.is_file(), path)

    def test_schema_builds(self) -> None:
        for sid, _phrase, domain, title in OA_APPLY_CASES:
            with self.subTest(id=sid):
                schema = build_domain_schema(title, domain)
                ok, errs = validate_schema(schema)
                self.assertTrue(ok, errs[:5])
                labels = schema.get("labels") or {}
                self.assertTrue(labels.get("authEyebrow"), labels)

    def test_mutual_p09_p11_registered(self) -> None:
        self.assertEqual(OA_MUTUAL_SKELETON, [])
        self.assertEqual(len(MUTUAL_CASES), 3)
        for sid, phrase, want, title in MUTUAL_CASES:
            with self.subTest(id=sid):
                self.assertIn(want, DOMAINS)
                got = match_text(f"基于 Spring Boot 的{title}的设计与实现。主要功能：{phrase}。")
                self.assertEqual(got.domain, want, f"hits={got.hits[:10]}")


if __name__ == "__main__":
    unittest.main()
