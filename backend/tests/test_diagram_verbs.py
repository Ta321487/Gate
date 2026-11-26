"""实体动作词：种子 / 材料优先 / 中性骨架 / 缺口。"""

from __future__ import annotations

import unittest

from app.services import diagram_verbs as dv


class DiagramVerbsUnit(unittest.TestCase):
    def setUp(self) -> None:
        dv.invalidate_cache()
        dv.bootstrap_from_seed()

    def test_seed_rows_use_known_keys_and_short_text(self) -> None:
        keys = dv.verb_key_names()
        self.assertTrue(keys)
        for row in dv._seed_payload():
            self.assertIn(row["verb_key"], keys, row)
            self.assertLessEqual(len(row["action_zh"]), 32, row)

    def test_seed_reads_material_verbs_per_domain(self) -> None:
        self.assertEqual(dv.resolve_verb("order", "ship", domain="DOM-CINEMA"), "出票")
        self.assertEqual(dv.resolve_verb("order", "complete", domain="DOM-CINEMA"), "确认观影")
        self.assertEqual(dv.resolve_verb("order", "ship", domain="DOM-CARRENT"), "办理取车")
        self.assertEqual(dv.resolve_verb("order", "complete", domain="DOM-CARRENT"), "办理还车")
        self.assertEqual(dv.resolve_verb("order", "ship", domain="DOM-HOTEL"), "办理入住")

    def test_no_cross_domain_leak(self) -> None:
        self.assertEqual(dv.resolve_verb("order", "ship", domain="DOM-FOOD"), "出餐")
        self.assertEqual(dv.resolve_verb("order", "ship", domain="DOM-UNKNOWN"), "")

    def test_material_beats_factory(self) -> None:
        schema = {"entities": {"order": {"verbs": {"ship": "出票", "complete": "确认观演"}}}}
        self.assertEqual(
            dv.resolve_verb("order", "complete", domain="DOM-CINEMA", schema=schema),
            "确认观演",
        )

    def test_named_domain_beats_wildcard(self) -> None:
        rows = [
            {"domain_id": "*", "skin_id": "", "entity_key": "order", "verb_key": "ship",
             "action_zh": "发货", "source": "migrated"},
            {"domain_id": "DOM-SHOP", "skin_id": "", "entity_key": "order", "verb_key": "ship",
             "action_zh": "出库", "source": "migrated"},
        ]
        self.assertEqual(dv.resolve_verb("order", "ship", domain="DOM-SHOP", rows=rows), "出库")
        self.assertEqual(dv.resolve_verb("order", "ship", domain="DOM-BLOG", rows=rows), "发货")

    # ---------- 拼句 ----------
    def test_phases_use_material_words(self) -> None:
        schema = {
            "domain": "DOM-CINEMA",
            "entities": {
                "order": {
                    "label": "订单",
                    "verbs": {"ship": "出票", "complete": "确认观演"},
                    "states": {"pending": "待取票", "shipped": "已出票", "completed": "已观影"},
                }
            },
        }
        admin = dv.material_phases("orders", schema)
        self.assertEqual(
            admin,
            {"select": "选择待取票订单", "confirm": "出票", "submit": "发起出票",
             "save": "更新订单为已出票", "ok": "出票成功"},
        )
        user = dv.material_phases("my_orders", schema)
        self.assertEqual(user["select"], "选择已出票订单")
        self.assertEqual(user["confirm"], "确认观演")
        self.assertEqual(user["save"], "更新订单为已观影")

    def test_missing_verb_degrades_to_neutral_skeleton(self) -> None:
        schema = {"domain": "DOM-SHOP", "entities": {"order": {"label": "订单"}}}
        ph = dv.material_phases("my_orders", schema)
        self.assertIsNotNone(ph)
        self.assertNotIn("收货", "".join(ph.values()))
        self.assertEqual(ph["select"], "查看订单")

    def test_missing_label_returns_none(self) -> None:
        self.assertIsNone(dv.material_phases("my_orders", {"entities": {}}))

    def test_open_kind_uses_menu_words(self) -> None:
        schema = {"domain": "DOM-CINEMA", "entities": {"archive": {"label": "场次"}}}
        ph = dv.material_phases("open", schema, menu_label="场次选座")
        self.assertIsNotNone(ph)
        self.assertIn("场次", ph["select"])
        self.assertNotIn("主表单", "".join(ph.values()))

    def test_open_kind_resolves_entity_by_menu_key(self) -> None:
        schema = {
            "domain": "DOM-CINEMA",
            "entities": {"archive": {"label": "场次"}, "order": {"label": "订单"}},
        }
        ph = dv.material_phases("open", schema, menu_key="archive_list", menu_label="选座办理")
        self.assertIsNotNone(ph)
        self.assertIn("场次", ph["select"])
        self.assertNotIn("订单", "".join(ph.values()))

    def test_empty_cache_falls_back_to_seed(self) -> None:
        """未迁入或空表缓存不得让跨域默认词静默消失。"""
        with dv._lock:
            dv._rows_cache = []
        self.assertEqual(dv.resolve_verb("order", "ship", domain="DOM-CINEMA"), "出票")
        dv.invalidate_cache()
        dv.bootstrap_from_seed()

    # ---------- 缺口 ----------
    def test_flow_gap_reports_missing_verb_only(self) -> None:
        schema = {"domain": "DOM-SHOP", "entities": {"order": {"label": "订单"}}}
        gap = dv.flow_gap("my_orders", schema)
        self.assertEqual(gap["verb_key"], "complete")
        self.assertIn("verbs.complete", gap["reason"])
        self.assertIsNone(dv.flow_gap("open", schema, menu_label="场次选座"))
        self.assertIsNone(dv.flow_gap("auth_login", schema))

    def test_domain_gaps_shop_order_seeded(self) -> None:
        """SHOP 订单 ship/complete 已进种子；缺行时仍应报缺口。"""
        rep = dv.domain_gaps("DOM-SHOP")
        pairs = {(g["entity_key"], g["verb_key"]) for g in rep["gaps"]}
        self.assertNotIn(("order", "ship"), pairs)
        self.assertNotIn(("order", "complete"), pairs)
        trimmed = [
            r
            for r in dv._seed_payload()
            if not (
                r.get("domain_id") == "DOM-SHOP"
                and r.get("entity_key") == "order"
                and r.get("verb_key") in ("ship", "complete")
            )
        ]
        miss = {
            (g["entity_key"], g["verb_key"])
            for g in dv.domain_gaps("DOM-SHOP", rows=trimmed)["gaps"]
        }
        self.assertIn(("order", "ship"), miss)
        self.assertIn(("order", "complete"), miss)
        cinema = {(g["entity_key"], g["verb_key"]) for g in dv.domain_gaps("DOM-CINEMA")["gaps"]}
        self.assertNotIn(("order", "ship"), cinema)
        self.assertNotIn(("order", "complete"), cinema)

    def test_catalog_domain_gaps_zero(self) -> None:
        from app.bake.catalog import DOMAINS

        report = dv.catalog_domain_gaps()
        self.assertEqual(report["domain_count"], len(DOMAINS))
        self.assertEqual(report["gap_count"], 0, msg=str(report.get("reports")[:3]))

    def test_flow_seed_covers_diagram_kinds(self) -> None:
        kinds = {c["kind"] for c in dv._seed_flow()}
        for k in ("my_orders", "orders", "cart", "open", "order_reviews_user"):
            self.assertIn(k, kinds)


class FlowSeedShape(unittest.TestCase):
    def test_every_flow_row_has_required_fields(self) -> None:
        for row in dv.flow_for_kind("my_orders"), dv.flow_for_kind("orders"):
            self.assertIsNotNone(row)
        rows = dv._seed_flow()
        for r in rows:
            for f in ("kind", "side", "entity_key", "verb_key"):
                self.assertIn(f, r, r)


if __name__ == "__main__":
    unittest.main()
