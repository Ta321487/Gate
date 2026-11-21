"""工厂业务规则参数：种子、域覆盖、schema 补缺。"""

from __future__ import annotations

import unittest

from app.services import rule_params as rp


class RuleParamsUnit(unittest.TestCase):
    def setUp(self) -> None:
        rp.invalidate_cache()
        rp.bootstrap_from_seed()

    def test_seed_unique(self) -> None:
        rows = rp._seed_payload()
        keys = [(r["domain_id"], r["rule_id"]) for r in rows]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertGreaterEqual(len(rows), 3)
        ids = {r["rule_id"] for r in rows}
        self.assertIn("order_pay_timeout_min", ids)
        self.assertIn("reservation_advance_hours", ids)

    def test_wildcard_fills_missing_schema_key(self) -> None:
        schema: dict = {}
        out = rp.apply_rule_params_to_schema(schema, "DOM-REPAIR")
        self.assertEqual(out.get("orderTimeoutMinutes"), 30)
        self.assertEqual(out.get("reservationAdvanceHours"), 1)
        self.assertIn("ruleParams", out)
        self.assertIn("order_pay_timeout_min", out["ruleParams"])

    def test_named_domain_overrides_wildcard(self) -> None:
        # 种子 DOM-SHOP 与 * 同值；用假行验证具名优先
        rows = [
            {
                "domain_id": "*",
                "rule_id": "order_pay_timeout_min",
                "label_zh": "默认",
                "value_num": 15,
                "unit_zh": "分钟",
                "schema_key": "orderTimeoutMinutes",
                "sort": 1,
                "source": "migrated",
            },
            {
                "domain_id": "DOM-SHOP",
                "rule_id": "order_pay_timeout_min",
                "label_zh": "商城",
                "value_num": 45,
                "unit_zh": "分钟",
                "schema_key": "orderTimeoutMinutes",
                "sort": 1,
                "source": "migrated",
            },
        ]
        out = rp.apply_rule_params_to_schema({}, "DOM-SHOP", rows=rows)
        self.assertEqual(out["orderTimeoutMinutes"], 45)
        self.assertEqual(out["ruleParams"]["order_pay_timeout_min"]["label_zh"], "商城")

    def test_does_not_overwrite_existing_schema_key(self) -> None:
        schema = {"orderTimeoutMinutes": 99}
        out = rp.apply_rule_params_to_schema(schema, "DOM-SHOP")
        self.assertEqual(out["orderTimeoutMinutes"], 99)
        self.assertEqual(out["ruleParams"]["order_pay_timeout_min"]["value"], 30)

    def test_apply_to_spec(self) -> None:
        spec = {"domain": "DOM-LIBRARY", "schema": {}}
        out = rp.apply_rule_params_to_spec(spec)
        self.assertIn("ruleParams", out["schema"])
        self.assertEqual(out["schema"].get("reservationAdvanceHours"), 1)

    def test_gap_when_trimmed(self) -> None:
        seed = rp._seed_payload()
        trimmed = [r for r in seed if r.get("rule_id") != "points_earn_rate"]
        report = rp.gap_report(rows=trimmed)
        aids = {g["rule_id"] for g in report["gaps"]}
        self.assertIn("points_earn_rate", aids)

    def test_no_hardcoded_dom_put(self) -> None:
        from pathlib import Path

        src = Path(rp.__file__).read_text(encoding="utf-8")
        self.assertNotIn('put("DOM-', src)
        self.assertIn("load_seed_json", src)


if __name__ == "__main__":
    unittest.main()
