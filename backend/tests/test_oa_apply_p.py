"""泳道 C/E：P-01～P-08 申请域；P-09～P-11 互选域。"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from app.bake.catalog import match_text
from app.bake.domain_schema import build_domain_schema, validate_schema
from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
from app.bake.oa_apply_p import MUTUAL_CASES, OA_APPLY_CASES, OA_MUTUAL_SKELETON
from app.bake.schema.followup_presets import FOLLOWUP_PRESETS
from app.bake.schema.templates import SCHEMA_BUILDERS
from app.bake.ticket_columns import (
    apply_ticket_shell_sql,
    ticket_amount_shell_wanted,
    ticket_loan_shell_wanted,
)

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples" / "申请预设开题"
SQL_DIR = Path(__file__).resolve().parents[1] / "app" / "bake" / "sql" / "templates"
FLAVOR_JS = (
    Path(__file__).resolve().parents[2]
    / "skeletons"
    / "baseline"
    / "frontend"
    / "src"
    / "utils"
    / "domainFlavor.js"
)


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

    def test_no_dead_overdue_state(self) -> None:
        for sid, _phrase, domain, _title in OA_APPLY_CASES:
            with self.subTest(id=sid):
                ticket = (build_domain_schema("t", domain).get("entities") or {}).get("ticket") or {}
                self.assertNotIn("overdue", ticket.get("states") or {})
                self.assertFalse(ticket.get("slaDeadline"))
                self.assertFalse(ticket.get("applicantCompleteOnly"))
                self.assertFalse(ticket.get("pickLoanPeriod"))

    def test_direction_skins_differ(self) -> None:
        """各选题档案可见列不得八域同文案。"""
        labels = {}
        for _sid, _p, domain, _t in OA_APPLY_CASES:
            arch = (build_domain_schema("t", domain).get("entities") or {}).get("archive") or {}
            fields = {f.get("key"): f.get("label") for f in (arch.get("fields") or [])}
            labels[domain] = (fields.get("title"), fields.get("author"), fields.get("isbn"))
        self.assertEqual(labels["DOM-SEAL"][0], "用章事项")
        self.assertEqual(labels["DOM-FLEET"][1], "司机")
        self.assertEqual(labels["DOM-CERT"][0], "证明名称")
        self.assertEqual(labels["DOM-PROMO"][2], "张贴位置")
        self.assertEqual(labels["DOM-FITOUT"][2], "工期与要求")
        self.assertEqual(labels["DOM-ACAD"][0], "异动事项")
        self.assertEqual(labels["DOM-TRIP"][2], "填报说明")
        self.assertEqual(labels["DOM-EXPENSE"][0], "经费项目")
        uniq = set(labels.values())
        self.assertEqual(len(uniq), 8, labels)

    def test_trip_closeout_and_expense_amount(self) -> None:
        trip = (build_domain_schema("t", "DOM-TRIP").get("entities") or {}).get("ticket") or {}
        self.assertEqual((trip.get("verbs") or {}).get("return"), "销结")
        self.assertEqual((trip.get("states") or {}).get("returned"), "已销结")
        self.assertTrue(trip.get("pickDateRange"))
        exp = (build_domain_schema("t", "DOM-EXPENSE").get("entities") or {}).get("ticket") or {}
        self.assertEqual(exp.get("fineLabel"), "报销金额")
        self.assertTrue(ticket_amount_shell_wanted("DOM-EXPENSE", exp))
        self.assertFalse(ticket_loan_shell_wanted("DOM-EXPENSE", exp))
        raw = (SQL_DIR / "DOM-EXPENSE.sql").read_text(encoding="utf-8")
        out = apply_ticket_shell_sql(
            raw, domain="DOM-EXPENSE", ticket_table="expense_apply", ticket_flags=exp
        )
        m = re.search(r"CREATE TABLE IF NOT EXISTS expense_apply \((.*?)\n\);", out, re.S)
        self.assertIsNotNone(m)
        body = m.group(1)
        self.assertIn("fine_yuan", body)
        self.assertNotIn("due_at", body)
        self.assertNotIn("reminded_at", body)

    def test_acad_student_seed(self) -> None:
        sql = (SQL_DIR / "DOM-ACAD.sql").read_text(encoding="utf-8")
        self.assertIn('"identityType":"学生"', sql)
        self.assertIn('"studentNo":"20260001"', sql)
        self.assertNotIn('"identityType":"教职工"', sql)

    def test_fleet_hint_no_slot_conflict_claim(self) -> None:
        hint = str((DOMAINS.get("DOM-FLEET") or {}).get("match_hint") or "")
        self.assertIn("无时段冲突引擎", hint)
        self.assertNotIn("可选时段冲突", hint)

    def test_oa_keyword_budget(self) -> None:
        """与 DOM-EVENT 同口径：词表预算 ≤20，长尾靠 match_recommend。"""
        for sid, _phrase, domain, _title in OA_APPLY_CASES:
            with self.subTest(domain=domain):
                kws = DOMAINS[domain].get("keywords") or []
                self.assertLessEqual(len(kws), 20, kws)
                self.assertGreaterEqual(len(kws), 4, kws)

    def test_keyword_hard_split_does_not_steal_neighbors(self) -> None:
        """硬分流命中后不得抢邻域（旧域回归）。"""
        cases = [
            ("学生宿舍报修管理系统", "DOM-DORM"),
            ("图书借阅管理系统", "DOM-LIBRARY"),
            ("顶岗实习周报管理系统", "DOM-INTERN"),
            ("社团活动报名管理系统", "DOM-ACTIVITY"),
            ("校园停车位预约系统", "DOM-PARKING"),
            ("助学贷款困难认定申请", "DOM-FUND"),
            ("请销假考勤管理系统", "DOM-ATTEND"),
            ("物业报修工单系统", "DOM-PROPERTY"),
            ("成绩更正申请系统", "DOM-GRADE"),
            ("合同登记单级审批", "DOM-CONTRACT"),
        ]
        for phrase, want in cases:
            with self.subTest(phrase=phrase):
                got = match_text(f"基于 Spring Boot 的{phrase}的设计与实现")
                self.assertEqual(got.domain, want, f"hits={got.hits[:10]}")

    def test_oa_flavors_in_baseline(self) -> None:
        text = FLAVOR_JS.read_text(encoding="utf-8")
        for flavor in ("seal", "fleet", "cert", "promo", "fitout", "acad", "trip", "expense"):
            with self.subTest(flavor=flavor):
                self.assertIn(f"{flavor}:", text)

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
