"""泳道 E · C-13：拼车结伴 DOM-CARPOOL（行程档案 + 意向单）。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import resolve_accept
from app.bake.catalog import match_text
from app.bake.domain_schema import attach_accept, build_domain_schema, validate_schema
from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
from app.bake.engine_sql import domain_sql
from app.bake.menu_routes import shell_kind
from app.bake.schema.followup_presets import FOLLOWUP_PRESETS
from app.bake.schema.templates import SCHEMA_BUILDERS

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "data" / "samples" / "拼车预设开题"


class CarpoolC13Tests(unittest.TestCase):
    def test_domain_registered(self) -> None:
        self.assertIn("DOM-CARPOOL", DOMAINS)
        caps = DOMAIN_CAPABILITIES["DOM-CARPOOL"]
        self.assertIn("archive", caps)
        self.assertIn("ticket_flow", caps)
        self.assertIn("quota", caps)
        self.assertIn("DOM-CARPOOL", FOLLOWUP_PRESETS)
        self.assertIn("DOM-CARPOOL", SCHEMA_BUILDERS)

    def test_match(self) -> None:
        got = match_text(
            "基于 Spring Boot 的高校校园拼车行程发布与同行意向对接系统的设计与实现。"
            "主要功能：行程发布、同行意向、审核对接。"
        )
        self.assertEqual(got.domain, "DOM-CARPOOL", f"hits={got.hits[:12]}")

    def test_neighbors(self) -> None:
        cases = [
            ("校园拼车行程发布与同行意向对接", "DOM-CARPOOL", "DOM-DATING"),
            ("婚恋交友牵线审核撮合", "DOM-DATING", "DOM-CARPOOL"),
            ("学习搭子组队意向互选确认", "DOM-MUTUAL-TEAM", "DOM-CARPOOL"),
            ("社团活动报名审核占名额", "DOM-ACTIVITY", "DOM-CARPOOL"),
        ]
        for phrase, want, avoid in cases:
            with self.subTest(phrase=phrase):
                got = match_text(f"基于 Spring Boot 的{phrase}系统的设计与实现")
                self.assertEqual(got.domain, want, f"hits={got.hits[:12]}")
                self.assertNotEqual(got.domain, avoid)

    def test_schema_menus_and_shell(self) -> None:
        schema = build_domain_schema("高校校园拼车行程与同行意向对接系统", "DOM-CARPOOL")
        ok, errs = validate_schema(schema)
        self.assertTrue(ok, errs[:5])
        self.assertEqual(
            shell_kind(DOMAIN_CAPABILITIES["DOM-CARPOOL"]),
            "archive_ticket",
        )
        user_keys = {m.get("key") for m in (schema.get("menus") or {}).get("user") or []}
        admin_keys = {m.get("key") for m in (schema.get("menus") or {}).get("admin") or []}
        self.assertIn("my_tickets", user_keys)
        self.assertIn("ticket_pending", admin_keys)
        self.assertIn("archive", user_keys)

    def test_sql_and_accept(self) -> None:
        sql = domain_sql(
            "DOM-CARPOOL",
            "t_carpool",
            title="高校校园拼车行程与同行意向对接系统",
            proposal_text="拼车行程同行意向对接",
        )
        self.assertIn("trip_route", sql)
        self.assertIn("carpool_intent", sql)
        d = resolve_accept(
            list(DOMAIN_CAPABILITIES["DOM-CARPOOL"]),
            "行程发布；同行意向；审核对接。",
            has_domain_overlay=True,
            has_baseline_runtime=True,
            archetypes=["ARCH-FLOW"],
            domain="DOM-CARPOOL",
            primary_archetype="ARCH-FLOW",
        )
        self.assertEqual(d["accept"], "full", d)
        spec = attach_accept(
            {
                "domain": "DOM-CARPOOL",
                "title": "高校校园拼车行程与同行意向对接系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-CARPOOL"]),
                "archetype": "ARCH-FLOW",
            },
            "拼车结伴",
        )
        self.assertEqual(spec.get("accept"), "full", spec.get("accept_reason"))

    def test_sample(self) -> None:
        path = SAMPLES / "C-13-DOM-CARPOOL-高校校园拼车行程与同行意向对接系统.txt"
        self.assertTrue(path.is_file(), path)


if __name__ == "__main__":
    unittest.main()
