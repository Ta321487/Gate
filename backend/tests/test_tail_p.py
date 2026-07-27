"""泳道 E 长尾：P-18、P-23～P-29 具名 DOM。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.catalog import match_text
from app.bake.domain_schema import build_domain_schema, validate_schema
from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
from app.bake.engine_sql import domain_sql
from app.bake.schema.followup_presets import FOLLOWUP_PRESETS
from app.bake.schema.templates import SCHEMA_BUILDERS
from app.bake.tail_p import TAIL_CASES

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples" / "长尾预设开题"


class TailPTests(unittest.TestCase):
    def test_domains_registered(self) -> None:
        self.assertEqual(len(TAIL_CASES), 8)
        for sid, _phrase, domain, _title in TAIL_CASES:
            with self.subTest(id=sid):
                self.assertIn(domain, DOMAINS)
                self.assertIn(domain, DOMAIN_CAPABILITIES)
                self.assertIn(domain, FOLLOWUP_PRESETS)
                self.assertIn(domain, SCHEMA_BUILDERS)

    def test_all_hit_named_domain(self) -> None:
        for sid, phrase, want, title in TAIL_CASES:
            with self.subTest(id=sid, title=title):
                text = f"基于 Spring Boot 的{title}的设计与实现。主要功能：{phrase}。"
                got = match_text(text)
                self.assertEqual(got.domain, want, f"hits={got.hits[:12]}")

    def test_neighbors_do_not_steal(self) -> None:
        cases = [
            ("临时车辆通行证与车牌备案申请审批", "DOM-CARPASS", "DOM-PARKING"),
            ("临时车辆通行证与车牌备案申请审批", "DOM-CARPASS", "DOM-VISITOR"),
            ("房源中介挂牌与带看意向跟进", "DOM-LISTING", "DOM-HOTEL"),
            ("房源中介挂牌与带看意向跟进", "DOM-LISTING", "DOM-CRM"),
            ("物资采购申请与申购单审批", "DOM-PROCURE", "DOM-ASSET"),
            ("学生社团注册成立与年审材料审批", "DOM-CLUB", "DOM-ACTIVITY"),
            ("大创项目申报与中期检查材料审批", "DOM-PROJ", "DOM-FUND"),
            ("伦理审查与开题答辩材料提交审核", "DOM-ETHIC", "DOM-GRADE"),
            ("入党申请与党员发展阶段材料审批", "DOM-PARTY", "DOM-EVENT"),
            ("合同登记与单级审批管理", "DOM-CONTRACT", "DOM-SEAL"),
            ("停车场车位时段预约管理", "DOM-PARKING", "DOM-CARPASS"),
        ]
        for phrase, want, avoid in cases:
            with self.subTest(phrase=phrase, avoid=avoid):
                got = match_text(f"基于 Spring Boot 的{phrase}系统的设计与实现")
                self.assertEqual(got.domain, want, f"hits={got.hits[:12]}")
                self.assertNotEqual(got.domain, avoid)

    def test_carpass_issue_pass_code(self) -> None:
        schema = build_domain_schema("高校临时车辆通行证备案管理系统", "DOM-CARPASS")
        ok, errs = validate_schema(schema)
        self.assertTrue(ok, errs[:5])
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("issuePassCode"))
        self.assertIn("pass_code", DOMAIN_CAPABILITIES["DOM-CARPASS"])
        sql = domain_sql(
            "DOM-CARPASS",
            "t_carpass",
            title="高校临时车辆通行证备案管理系统",
            proposal_text="临时车辆通行证与车牌备案",
        )
        self.assertIn("pass_code", sql)
        self.assertIn("pass_zone", sql)

    def test_schema_builds(self) -> None:
        for sid, _phrase, domain, title in TAIL_CASES:
            with self.subTest(id=sid):
                schema = build_domain_schema(title, domain)
                ok, errs = validate_schema(schema)
                self.assertTrue(ok, errs[:5])

    def test_sample_files_exist(self) -> None:
        self.assertTrue(SAMPLES.is_dir(), SAMPLES)
        for sid, _phrase, domain, title in TAIL_CASES:
            with self.subTest(id=sid):
                path = SAMPLES / f"{sid}-{domain}-{title}.txt"
                self.assertTrue(path.is_file(), path)


if __name__ == "__main__":
    unittest.main()
