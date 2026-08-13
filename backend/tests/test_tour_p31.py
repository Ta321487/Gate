"""泳道 C/P-31：旅行社线路报名 DOM-TOUR（线路档案 + 报名占名额）。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import resolve_accept
from app.bake.catalog import match_text
from app.bake.domain_schema import attach_accept, build_domain_schema, validate_schema
from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
from app.bake.engine_sql import domain_sql
from app.bake.menu_routes import shell_kind
from app.bake.scene_scan import scene_for
from app.bake.schema.followup_presets import FOLLOWUP_PRESETS
from app.bake.schema.templates import SCHEMA_BUILDERS

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "data" / "samples" / "长尾预设开题"


class TourP31Tests(unittest.TestCase):
    def test_domain_registered(self) -> None:
        self.assertIn("DOM-TOUR", DOMAINS)
        caps = DOMAIN_CAPABILITIES["DOM-TOUR"]
        self.assertIn("archive", caps)
        self.assertIn("ticket_flow", caps)
        self.assertIn("quota", caps)
        self.assertNotIn("slot_reserve", caps)
        self.assertNotIn("order_lines", caps)
        self.assertIn("DOM-TOUR", FOLLOWUP_PRESETS)
        self.assertIn("DOM-TOUR", SCHEMA_BUILDERS)

    def test_match(self) -> None:
        got = match_text(
            "基于 Spring Boot 的旅行社线路报名管理系统的设计与实现。"
            "主要功能：线路档案、跟团报名、审核占名额、确认报名。"
        )
        self.assertEqual(got.domain, "DOM-TOUR", f"hits={got.hits[:12]}")

    def test_neighbors(self) -> None:
        cases = [
            ("旅行社线路报名与出团确认", "DOM-TOUR", "DOM-ACTIVITY"),
            ("社团活动报名审核占名额", "DOM-ACTIVITY", "DOM-TOUR"),
            ("宾馆客房预订管理系统", "DOM-HOTEL", "DOM-TOUR"),
            ("校园拼车行程同行意向对接", "DOM-CARPOOL", "DOM-TOUR"),
            ("公务出差申请审批销结", "DOM-TRIP", "DOM-TOUR"),
            ("旅游套餐商城购物车下单", "DOM-SHOP", "DOM-TOUR"),
        ]
        for phrase, want, avoid in cases:
            with self.subTest(phrase=phrase):
                got = match_text(f"基于 Spring Boot 的{phrase}系统的设计与实现")
                self.assertEqual(got.domain, want, f"hits={got.hits[:12]}")
                self.assertNotEqual(got.domain, avoid)

    def test_scene_enterprise_default(self) -> None:
        self.assertEqual(
            scene_for(
                "DOM-TOUR",
                "旅行社线路报名管理系统",
                "游客在线报名，计调审核确认。",
            ),
            "enterprise",
        )

    def test_schema_menus_and_shell(self) -> None:
        schema = build_domain_schema(
            "旅行社线路报名管理系统",
            "DOM-TOUR",
            proposal_text="线路档案；游客报名；计调审核占名额。",
        )
        ok, errs = validate_schema(schema)
        self.assertTrue(ok, errs[:5])
        self.assertEqual(
            shell_kind(DOMAIN_CAPABILITIES["DOM-TOUR"]),
            "archive_ticket",
        )
        user_keys = {m.get("key") for m in (schema.get("menus") or {}).get("user") or []}
        admin_keys = {m.get("key") for m in (schema.get("menus") or {}).get("admin") or []}
        self.assertIn("my_tickets", user_keys)
        self.assertIn("ticket_pending", admin_keys)
        self.assertIn("archive", user_keys)
        self.assertNotIn("studentNo", {f["key"] for f in schema.get("profileFields") or []})
        verbs = schema["entities"]["ticket"]["verbs"]
        self.assertEqual(verbs.get("approve"), "确认报名")
        self.assertEqual(verbs.get("return"), "取消报名")

    def test_sql_and_accept(self) -> None:
        sql = domain_sql(
            "DOM-TOUR",
            "t_tour",
            title="旅行社线路报名管理系统",
            proposal_text="线路报名审核确认",
        )
        self.assertIn("tour_line", sql)
        self.assertIn("tour_signup", sql)
        self.assertIn("stage", sql)
        self.assertIn("开放报名", sql)
        self.assertIn("apply_deadline_at", sql)
        self.assertIn("请确认报名", sql)
        schema = build_domain_schema(
            "旅行社线路报名管理系统",
            "DOM-TOUR",
            proposal_text="线路档案；游客报名；计调审核占名额。",
        )
        keys = {f.get("key") for f in schema["entities"]["archive"]["fields"]}
        self.assertIn("applyDeadlineAt", keys)
        d = resolve_accept(
            list(DOMAIN_CAPABILITIES["DOM-TOUR"]),
            "线路档案；跟团报名；审核占名额；确认报名。",
            has_domain_overlay=True,
            has_baseline_runtime=True,
            archetypes=["ARCH-FLOW"],
            domain="DOM-TOUR",
            primary_archetype="ARCH-FLOW",
        )
        self.assertEqual(d["accept"], "full", d)
        spec = attach_accept(
            {
                "domain": "DOM-TOUR",
                "title": "旅行社线路报名管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-TOUR"]),
                "archetype": "ARCH-FLOW",
            },
            "旅行社线路报名",
        )
        self.assertEqual(spec.get("accept"), "full", spec.get("accept_reason"))

    def test_sample(self) -> None:
        path = SAMPLES / "P-31-DOM-TOUR-旅行社线路报名管理系统.txt"
        self.assertTrue(path.is_file(), path)


if __name__ == "__main__":
    unittest.main()
