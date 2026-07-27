"""泳道 D/E：P-12～P-16 学工；P-20/P-21 床位；P-22 查寝。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.catalog import match_text
from app.bake.domain_schema import build_domain_schema, validate_schema
from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
from app.bake.schema.followup_presets import FOLLOWUP_PRESETS
from app.bake.schema.templates import SCHEMA_BUILDERS
from app.bake.stuwork_p import BED_CASES, CHECKIN_CASES, STUWORK_BED_SKELETON, STUWORK_CASES

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples" / "学工预设开题"


class StuworkPTests(unittest.TestCase):
    def test_domains_registered(self) -> None:
        for sid, _p, domain, _t in STUWORK_CASES:
            with self.subTest(id=sid):
                self.assertIn(domain, DOMAINS)
                self.assertIn(domain, DOMAIN_CAPABILITIES)
                self.assertIn(domain, FOLLOWUP_PRESETS)
                self.assertIn(domain, SCHEMA_BUILDERS)

    def test_p12_p16_hit(self) -> None:
        self.assertEqual(len(STUWORK_CASES), 5)
        for sid, phrase, want, title in STUWORK_CASES:
            with self.subTest(id=sid):
                text = f"基于 Spring Boot 的{title}的设计与实现。主要功能：{phrase}。"
                got = match_text(text)
                self.assertEqual(got.domain, want, f"hits={got.hits[:10]}")

    def test_neighbors(self) -> None:
        cases = [
            ("第二课堂学分项目认定申请审批", "DOM-CREDIT", "DOM-ACTIVITY"),
            ("劳动教育志愿时长登记认定审批", "DOM-LABOR", "DOM-ACTIVITY"),
            ("学期末学生网上评教评分与评语", "DOM-EVAL", "DOM-GRADE"),
            ("综合测评德育分加减分申报审批", "DOM-MORAL", "DOM-GRADE"),
            ("创新学分竞赛获奖成果登记审批", "DOM-AWARD", "DOM-FUND"),
            ("新生宿舍床位在线选择分配", "DOM-BED", "DOM-DORM"),
            ("学生宿舍调宿退宿申请审批", "DOM-BED", "DOM-DORM"),
            ("宿舍查寝归寝签到缺勤记录", "DOM-CHECKIN", "DOM-DORM"),
            ("宿舍查寝归寝签到缺勤记录", "DOM-CHECKIN", "DOM-ATTEND"),
            ("宿舍查寝归寝签到缺勤记录", "DOM-CHECKIN", "DOM-ACTIVITY"),
        ]
        for phrase, want, avoid in cases:
            with self.subTest(phrase=f"{phrase}->{want}!={avoid}"):
                got = match_text(f"基于 Spring Boot 的{phrase}系统的设计与实现")
                self.assertEqual(got.domain, want, f"hits={got.hits[:10]}")
                self.assertNotEqual(got.domain, avoid)

    def test_samples_exist(self) -> None:
        for sid, _p, domain, title in [*STUWORK_CASES, *BED_CASES, *CHECKIN_CASES]:
            with self.subTest(id=sid):
                path = SAMPLES / f"{sid}-{domain}-{title}.txt"
                self.assertTrue(path.is_file(), path)

    def test_schema_builds(self) -> None:
        for sid, _p, domain, title in STUWORK_CASES:
            with self.subTest(id=sid):
                schema = build_domain_schema(title, domain)
                ok, errs = validate_schema(schema)
                self.assertTrue(ok, errs[:5])

    def test_eval_has_rating(self) -> None:
        schema = build_domain_schema("高校学生网上评教管理系统", "DOM-EVAL")
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("allowRating"))
        self.assertTrue(ticket.get("approveEndsFlow"))
        self.assertGreaterEqual(len(ticket.get("ratingDims") or []), 3)

    def test_bed_p20_p21_registered(self) -> None:
        self.assertEqual(len(BED_CASES), 2)
        self.assertIn("DOM-BED", DOMAINS)
        self.assertIn("bed_occupy", DOMAIN_CAPABILITIES["DOM-BED"])
        for sid, phrase, want, title in BED_CASES:
            with self.subTest(id=sid):
                got = match_text(f"基于 Spring Boot 的{title}的设计与实现。主要功能：{phrase}。")
                self.assertEqual(got.domain, want, f"hits={got.hits[:10]}")
                schema = build_domain_schema(title, want)
                ok, errs = validate_schema(schema)
                self.assertTrue(ok, errs[:5])

    def test_checkin_p22_registered(self) -> None:
        self.assertEqual(len(CHECKIN_CASES), 1)
        self.assertEqual(STUWORK_BED_SKELETON, [])
        self.assertIn("DOM-CHECKIN", DOMAINS)
        self.assertIn("checkin", DOMAIN_CAPABILITIES["DOM-CHECKIN"])
        for sid, phrase, want, title in CHECKIN_CASES:
            with self.subTest(id=sid):
                got = match_text(f"基于 Spring Boot 的{title}的设计与实现。主要功能：{phrase}。")
                self.assertEqual(got.domain, want, f"hits={got.hits[:10]}")
                schema = build_domain_schema(title, want)
                ok, errs = validate_schema(schema)
                self.assertTrue(ok, errs[:5])
                ticket = (schema.get("entities") or {}).get("ticket") or {}
                self.assertTrue(ticket.get("allowCheckin"))
                self.assertTrue(ticket.get("noShowAfterEnd"))
                self.assertEqual(ticket.get("checkinLabel"), "归寝签到")


if __name__ == "__main__":
    unittest.main()
