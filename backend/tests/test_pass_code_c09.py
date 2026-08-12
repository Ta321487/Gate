"""泳道 E · C-09：演示通行码；P-17 挂 DOM-VISITOR。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES, resolve_accept, scan_out_of_scope
from app.bake.catalog import match_text
from app.bake.domain_schema import build_domain_schema, validate_schema
from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
from app.bake.engine_sql import domain_sql
from app.bake.sql.fragments import _ticket_flag_column_names

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples" / "申请预设开题"


class PassCodeC09Tests(unittest.TestCase):
    def test_capability_registered(self) -> None:
        self.assertIn("pass_code", CAPABILITIES)
        self.assertEqual(CAPABILITIES["pass_code"]["status"], "implemented")
        self.assertIn("pass_code", DOMAIN_CAPABILITIES["DOM-VISITOR"])

    def test_visitor_schema_and_match(self) -> None:
        self.assertIn("DOM-VISITOR", DOMAINS)
        title = "高校访客登记与临时门禁申请系统"
        got = match_text(
            f"基于 Spring Boot 的高校访客预约登记与通行码管理系统的设计与实现。"
            f"主要功能：访客登记临时门禁申请。"
        )
        self.assertEqual(got.domain, "DOM-VISITOR", f"hits={got.hits[:10]}")
        schema = build_domain_schema(title, "DOM-VISITOR")
        ok, errs = validate_schema(schema)
        self.assertTrue(ok, errs[:5])
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("issuePassCode"))
        self.assertTrue(ticket.get("approveEndsFlow"))
        self.assertEqual(ticket.get("passCodeLabel"), "通行码")
        names = _ticket_flag_column_names(ticket)
        self.assertIn("pass_code", names)

    def test_sql_has_pass_code(self) -> None:
        sql = domain_sql(
            "DOM-VISITOR",
            "t_visitor",
            title="高校访客登记与临时门禁申请系统",
            proposal_text="访客登记临时门禁申请",
        )
        self.assertIn("pass_code", sql)
        self.assertIn("visit_zone", sql)
        self.assertIn("visitor_apply", sql)

    def test_neighbors(self) -> None:
        cases = [
            ("校园访客登记与临时门禁申请", "DOM-VISITOR", "DOM-LABSAFE"),
            ("校园访客登记与临时门禁申请", "DOM-VISITOR", "DOM-MEETING"),
            ("会议室预约时段管理", "DOM-MEETING", "DOM-VISITOR"),
        ]
        for phrase, want, avoid in cases:
            with self.subTest(phrase=phrase):
                got = match_text(f"基于 Spring Boot 的{phrase}系统的设计与实现")
                self.assertEqual(got.domain, want, f"hits={got.hits[:10]}")
                self.assertNotEqual(got.domain, avoid)

    def test_sample_exists(self) -> None:
        path = SAMPLES / "P-17-DOM-VISITOR-高校访客登记与临时门禁申请系统.txt"
        self.assertTrue(path.is_file(), path)

    def test_barrier_hardware_rejects_carpass_software_ok(self) -> None:
        """道闸/抬杆/车牌识别属硬件联控 → reject；纯通行证备案仍 full。"""
        shallow = "主要功能：临时车辆通行证申请与车牌备案审核，通过后签发通行码。"
        self.assertEqual(scan_out_of_scope(shallow), [])
        shallow_d = resolve_accept(
            list(DOMAIN_CAPABILITIES["DOM-CARPASS"]),
            shallow,
            has_domain_overlay=True,
            has_baseline_runtime=True,
            archetypes=["ARCH-FLOW"],
            domain="DOM-CARPASS",
            primary_archetype="ARCH-FLOW",
        )
        self.assertEqual(shallow_d["accept"], "full", shallow_d)

        hard = "主要功能：车牌识别自动抬杆与停车场道闸联动。"
        hits = scan_out_of_scope(hard)
        self.assertTrue(
            any("道闸" in h or "车牌识别" in h for h in hits),
            hits,
        )
        hard_d = resolve_accept(
            list(DOMAIN_CAPABILITIES["DOM-CARPASS"]),
            hard,
            has_domain_overlay=True,
            has_baseline_runtime=True,
            archetypes=["ARCH-FLOW"],
            domain="DOM-CARPASS",
            primary_archetype="ARCH-FLOW",
        )
        self.assertEqual(hard_d["accept"], "reject", hard_d)

        # 否定划界不误伤
        scoped = "主要功能：车辆通行证备案审核。本期不对接道闸抬杆与车牌识别硬件。"
        self.assertEqual(scan_out_of_scope(scoped), [])


if __name__ == "__main__":
    unittest.main()
