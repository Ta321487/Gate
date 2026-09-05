"""泳道 P-32：四轮商业租车 DOM-CARRENT（选车→租期下单→取还车）。"""

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
from app.bake.schema.templates import SCHEMA_BUILDERS

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "data" / "samples" / "长尾预设开题"


class CarrentP32Tests(unittest.TestCase):
    def test_domain_registered(self) -> None:
        self.assertIn("DOM-CARRENT", DOMAINS)
        caps = DOMAIN_CAPABILITIES["DOM-CARRENT"]
        self.assertIn("archive", caps)
        self.assertIn("slot_reserve", caps)
        self.assertIn("order_lines", caps)
        self.assertNotIn("ticket_flow", caps)
        self.assertIn("DOM-CARRENT", SCHEMA_BUILDERS)

    def test_match(self) -> None:
        got = match_text(
            "基于 Spring Boot 的汽车租赁管理系统的设计与实现。"
            "主要功能：车型档案、按日租车、取车还车、租车下单。"
        )
        self.assertEqual(got.domain, "DOM-CARRENT", f"hits={got.hits[:12]}")

    def test_match_nev(self) -> None:
        got = match_text(
            "新能源汽车在线租赁管理系统的设计与实现。"
            "主要功能：车型租赁、门店取车、取车还车。"
        )
        self.assertEqual(got.domain, "DOM-CARRENT", f"hits={got.hits[:12]}")

    def test_neighbors(self) -> None:
        cases = [
            ("汽车租赁与门店取车还车", "DOM-CARRENT", "DOM-FLEET"),
            ("公务用车选车申请审批", "DOM-FLEET", "DOM-CARRENT"),
            ("宾馆客房预订管理系统", "DOM-HOTEL", "DOM-CARRENT"),
            ("充电桩与共享车位时段预约", "DOM-PARKING", "DOM-CARRENT"),
            ("校园器材设备租借审核归还", "DOM-EQUIP", "DOM-CARRENT"),
            ("校园拼车行程同行意向对接", "DOM-CARPOOL", "DOM-CARRENT"),
            ("校园临时车辆通行证申请备案", "DOM-CARPASS", "DOM-CARRENT"),
        ]
        for phrase, want, avoid in cases:
            with self.subTest(phrase=phrase):
                got = match_text(f"基于 Spring Boot 的{phrase}系统的设计与实现")
                self.assertEqual(got.domain, want, f"hits={got.hits[:12]}")
                self.assertNotEqual(got.domain, avoid)

    def test_scene_commercial(self) -> None:
        self.assertEqual(
            scene_for(
                "DOM-CARRENT",
                "汽车租赁管理系统",
                "租车人选车下单，门店取还车。",
            ),
            "commercial",
        )

    def test_schema_menus_and_shell(self) -> None:
        schema = build_domain_schema(
            "汽车租赁管理系统",
            "DOM-CARRENT",
            proposal_text="车型档案；按日租期；取车还车。",
        )
        ok, errs = validate_schema(schema)
        self.assertTrue(ok, errs[:5])
        self.assertEqual(
            shell_kind(DOMAIN_CAPABILITIES["DOM-CARRENT"]),
            "slot",
        )
        user_keys = {m.get("key") for m in (schema.get("menus") or {}).get("user") or []}
        admin_keys = {m.get("key") for m in (schema.get("menus") or {}).get("admin") or []}
        self.assertIn("my_reservations", user_keys)
        self.assertIn("my_orders", user_keys)
        self.assertIn("archive", user_keys)
        self.assertIn("orders", admin_keys)
        self.assertNotIn("studentNo", {f["key"] for f in schema.get("profileFields") or []})
        from app.bake.domain_skin import traits_for_domain

        order = schema["entities"]["order"]
        self.assertEqual(order.get("fulfillMode"), "rental")
        self.assertEqual(order["verbs"].get("ship"), "办理取车")
        self.assertEqual(order["verbs"].get("complete"), "办理还车")
        self.assertTrue(traits_for_domain("DOM-CARRENT").get("slotCarrent"))

    def test_sql_and_accept(self) -> None:
        sql = domain_sql(
            "DOM-CARRENT",
            "t_carrent",
            title="汽车租赁管理系统",
            proposal_text="车型租赁取车还车",
        )
        self.assertIn("vehicle", sql)
        self.assertIn("reservation", sql)
        self.assertIn("biz_order", sql)
        self.assertIn("大众朗逸", sql)
        self.assertIn("比亚迪", sql)
        d = resolve_accept(
            list(DOMAIN_CAPABILITIES["DOM-CARRENT"]),
            "车型档案；按日租车；取车还车；租车下单。",
            has_domain_overlay=True,
            has_baseline_runtime=True,
            archetypes=["ARCH-RESERVE"],
            domain="DOM-CARRENT",
            primary_archetype="ARCH-RESERVE",
        )
        self.assertEqual(d["accept"], "full", d)
        spec = attach_accept(
            {
                "domain": "DOM-CARRENT",
                "title": "汽车租赁管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-CARRENT"]),
                "archetype": "ARCH-RESERVE",
            },
            "汽车租赁取车还车",
        )
        self.assertEqual(spec.get("accept"), "full", spec.get("accept_reason"))

    def test_sample_file(self) -> None:
        path = SAMPLES / "P-32-DOM-CARRENT-汽车租赁管理系统.txt"
        self.assertTrue(path.is_file(), path)
        text = path.read_text(encoding="utf-8")
        got = match_text(text)
        self.assertEqual(got.domain, "DOM-CARRENT", f"hits={got.hits[:12]}")


if __name__ == "__main__":
    unittest.main()
