"""泳道 E · C-15：影院选座购票 seat_select + DOM-CINEMA。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES, resolve_accept
from app.bake.catalog import match_text
from app.bake.domain_schema import attach_accept, build_domain_schema, validate_schema
from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.seat_select import SEAT_SELECT_CAP
from app.bake.menu_routes import shell_kind
from app.bake.schema.templates import SCHEMA_BUILDERS

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "data" / "samples" / "能力预设开题"
BASELINE = ROOT / "skeletons" / "baseline"


class CinemaC15Tests(unittest.TestCase):
    def test_capability_and_domain(self) -> None:
        self.assertIn("seat_select", CAPABILITIES)
        self.assertEqual(CAPABILITIES["seat_select"]["status"], "implemented")
        self.assertIn("DOM-CINEMA", DOMAINS)
        caps = DOMAIN_CAPABILITIES["DOM-CINEMA"]
        self.assertIn(SEAT_SELECT_CAP, caps)
        self.assertIn("order_lines", caps)
        self.assertIn("quota", caps)
        self.assertNotIn("ticket_flow", caps)
        self.assertIn("DOM-CINEMA", SCHEMA_BUILDERS)

    def test_match(self) -> None:
        got = match_text(
            "基于 Spring Boot 的影院选座购票管理系统的设计与实现。"
            "主要功能：场次维护、座位图选座、下单占座、订单查询。"
        )
        self.assertEqual(got.domain, "DOM-CINEMA", f"hits={got.hits[:12]}")

    def test_neighbors(self) -> None:
        cases = [
            ("影院选座购票座位图下单", "DOM-CINEMA", "DOM-MEDIA"),
            ("影视综点播片单收藏播放", "DOM-MEDIA", "DOM-CINEMA"),
            ("自习室座位占座时段预约管理", "DOM-MEETING", "DOM-CINEMA"),
            ("社团活动报名审核占名额管理", "DOM-ACTIVITY", "DOM-CINEMA"),
        ]
        for phrase, want, avoid in cases:
            with self.subTest(phrase=phrase):
                got = match_text(f"基于 Spring Boot 的{phrase}系统的设计与实现")
                self.assertEqual(got.domain, want, f"hits={got.hits[:12]}")
                self.assertNotEqual(got.domain, avoid)

    def test_schema_and_shell(self) -> None:
        schema = build_domain_schema("影院选座购票管理系统", "DOM-CINEMA")
        ok, errs = validate_schema(schema)
        self.assertTrue(ok, errs[:5])
        self.assertEqual(shell_kind(DOMAIN_CAPABILITIES["DOM-CINEMA"]), "order")
        spec = attach_accept(
            {
                "domain": "DOM-CINEMA",
                "title": "影院选座购票管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-CINEMA"]),
                "archetype": "ARCH-TRADE",
            },
            "场次；座位图选座；订单占座。",
        )
        sch = spec.get("schema") or {}
        user_keys = {m.get("key") for m in (sch.get("menus") or {}).get("user") or []}
        self.assertIn("seat_shows", user_keys)
        self.assertIn("my_orders", user_keys)
        self.assertNotIn("cart", user_keys)
        self.assertIn(SEAT_SELECT_CAP, spec.get("capabilities") or [])

    def test_sql_yml_accept(self) -> None:
        sql = domain_sql(
            "DOM-CINEMA",
            "t_cin",
            title="影院选座购票管理系统",
            proposal_text="影院选座购票座位图",
        )
        for t in ("cinema_show", "cinema_seat", "biz_order", "order_line"):
            self.assertIn(t, sql)
        spec = attach_accept(
            {
                "domain": "DOM-CINEMA",
                "title": "影院选座购票管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-CINEMA"]),
                "archetype": "ARCH-TRADE",
            },
            "选座购票",
        )
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-CINEMA", spec)
        self.assertIn("seat-select-enabled: true", yml)
        self.assertIn("order-cart-table:", yml)
        d = resolve_accept(
            list(DOMAIN_CAPABILITIES["DOM-CINEMA"]),
            "场次选座；座位图；订单。",
            has_domain_overlay=True,
            has_baseline_runtime=True,
            archetypes=["ARCH-TRADE"],
            domain="DOM-CINEMA",
            primary_archetype="ARCH-TRADE",
        )
        self.assertEqual(d["accept"], "full", d)

    def test_runtime_files(self) -> None:
        self.assertTrue((BASELINE / "backend/src/main/java/com/thesis/service/SeatStore.java").is_file())
        self.assertTrue(
            (BASELINE / "backend/src/main/java/com/thesis/controller/SeatController.java").is_file()
        )
        self.assertTrue((BASELINE / "frontend/src/views/SeatShows.vue").is_file())
        self.assertTrue((BASELINE / "frontend/src/views/SeatMap.vue").is_file())

    def test_sample(self) -> None:
        path = SAMPLES / "C-15-DOM-CINEMA-影院选座购票管理系统.txt"
        self.assertTrue(path.is_file(), path)


if __name__ == "__main__":
    unittest.main()
