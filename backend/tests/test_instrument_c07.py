"""泳道 E · C-07：仪器机时借+约；P-19 挂 DOM-INSTRUMENT。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES, resolve_accept, scan_out_of_scope
from app.bake.catalog import match_text
from app.bake.domain_schema import build_domain_schema, validate_schema
from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
from app.bake.engine_sql import domain_sql
from app.bake.menu_routes import shell_kind
from app.bake.schema.followup_presets import FOLLOWUP_PRESETS
from app.bake.schema.templates import SCHEMA_BUILDERS

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples" / "申请预设开题"
ROOT = Path(__file__).resolve().parents[2]


class InstrumentC07Tests(unittest.TestCase):
    def test_capability_and_domain(self) -> None:
        self.assertIn("instrument_slot", CAPABILITIES)
        self.assertEqual(CAPABILITIES["instrument_slot"]["status"], "implemented")
        self.assertIn("DOM-INSTRUMENT", DOMAINS)
        caps = DOMAIN_CAPABILITIES["DOM-INSTRUMENT"]
        self.assertIn("ticket_flow", caps)
        self.assertIn("slot_reserve", caps)
        self.assertIn("instrument_slot", caps)
        self.assertIn("DOM-INSTRUMENT", FOLLOWUP_PRESETS)
        self.assertIn("DOM-INSTRUMENT", SCHEMA_BUILDERS)

    def test_p19_match(self) -> None:
        title = "高校大型仪器借用与机时预约管理系统"
        got = match_text(
            f"基于 Spring Boot 的{title}的设计与实现。"
            f"主要功能：大型仪器借用与机时时段预约。"
        )
        self.assertEqual(got.domain, "DOM-INSTRUMENT", f"hits={got.hits[:12]}")
        self.assertIn("ARCH-FLOW", got.archetypes or [])
        self.assertIn("ARCH-RESERVE", got.archetypes or [])

    def test_neighbors(self) -> None:
        cases = [
            ("大型仪器借用与机时时段预约", "DOM-INSTRUMENT", "DOM-MEETING"),
            ("大型仪器借用与机时时段预约", "DOM-INSTRUMENT", "DOM-EQUIP"),
            ("实验室器材借用归还管理", "DOM-EQUIP", "DOM-INSTRUMENT"),
            ("会议室场地时段预约管理", "DOM-MEETING", "DOM-INSTRUMENT"),
        ]
        for phrase, want, avoid in cases:
            with self.subTest(phrase=phrase, avoid=avoid):
                got = match_text(f"基于 Spring Boot 的{phrase}系统的设计与实现")
                self.assertEqual(got.domain, want, f"hits={got.hits[:12]}")
                self.assertNotEqual(got.domain, avoid)

    def test_schema_menus_and_shell(self) -> None:
        schema = build_domain_schema("高校大型仪器借用与机时预约管理系统", "DOM-INSTRUMENT")
        ok, errs = validate_schema(schema)
        self.assertTrue(ok, errs[:5])
        self.assertIn("reservation", (schema.get("entities") or {}))
        self.assertIn("ticket", (schema.get("entities") or {}))
        user_keys = {m.get("key") for m in (schema.get("menus") or {}).get("user") or []}
        self.assertIn("my_reservations", user_keys)
        self.assertIn("my_tickets", user_keys)
        self.assertEqual(
            shell_kind(DOMAIN_CAPABILITIES["DOM-INSTRUMENT"]),
            "archive_ticket_multi",
        )

    def test_sql_has_loan_and_slots(self) -> None:
        sql = domain_sql(
            "DOM-INSTRUMENT",
            "t_inst",
            title="高校大型仪器借用与机时预约管理系统",
            proposal_text="大型仪器借用与机时时段预约",
        )
        self.assertIn("instrument", sql)
        self.assertIn("instrument_loan", sql)
        self.assertIn("resource_slot", sql)
        self.assertIn("reservation", sql)
        # 过期时段不可约：SlotStore.listSlots(bookableOnly)/reserve 拦 start_at
        slot = (
            (ROOT / "skeletons" / "baseline" / "backend" / "src" / "main" / "java"
             / "com" / "thesis" / "capability" / "SlotStore.java").read_text(encoding="utf-8")
        )
        self.assertIn("bookableOnly", slot)
        self.assertIn("该时段已过，不可预约", slot)

    def test_named_fr_accept_full(self) -> None:
        d = resolve_accept(
            list(DOMAIN_CAPABILITIES["DOM-INSTRUMENT"]),
            "大型仪器。主要功能：仪器档案；机时时段预约；借用申请审核；归还。",
            has_domain_overlay=True,
            has_baseline_runtime=True,
            archetypes=["ARCH-FLOW", "ARCH-RESERVE"],
            domain="DOM-INSTRUMENT",
            primary_archetype="ARCH-FLOW",
        )
        self.assertEqual(d["accept"], "full", d)
        self.assertEqual(d.get("cross_path"), "FR")

    def test_sample_exists(self) -> None:
        path = SAMPLES / "P-19-DOM-INSTRUMENT-高校大型仪器借用与机时预约管理系统.txt"
        self.assertTrue(path.is_file(), path)

    def test_p30_oa_triple_reject(self) -> None:
        text = (
            "主要功能：行政印章用章申请、公务用车派车申请与在读证明开具申请三合一办公审批。"
        )
        hits = scan_out_of_scope(text)
        self.assertTrue(any("OA三联" in h for h in hits), hits)
        d = resolve_accept(
            list(DOMAIN_CAPABILITIES["DOM-SEAL"]),
            text,
            has_domain_overlay=True,
            has_baseline_runtime=True,
            archetypes=["ARCH-FLOW"],
            domain="DOM-SEAL",
            primary_archetype="ARCH-FLOW",
        )
        self.assertEqual(d["accept"], "reject", d)


if __name__ == "__main__":
    unittest.main()
