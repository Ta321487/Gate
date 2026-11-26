"""工厂字典台：种子、解析、注入、缺口。"""

from __future__ import annotations

import unittest

from app.services import dict_values as dv


class DictValuesUnit(unittest.TestCase):
    def setUp(self) -> None:
        dv.invalidate_cache()
        dv.EXPECTED_DICT_CODES = {}
        dv._ticket_domains_cache = None
        dv.bootstrap_from_seed()

    def test_seed_shop_refund_and_priority_wildcard(self) -> None:
        self.assertEqual(
            dv.resolve_label("DOM-SHOP", "refund_type", "refund_only"),
            "仅退款",
        )
        self.assertEqual(
            dv.resolve_label("DOM-SHOP", "refund_type", "return_refund"),
            "退货退款",
        )
        self.assertEqual(
            dv.resolve_label("DOM-FOOD", "refund_type", "refund_only"),
            "仅退款",
        )
        self.assertEqual(
            dv.resolve_label("DOM-CINEMA", "refund_type", "return_refund"),
            "退货退款",
        )
        # 报修域吃 * 优先级
        self.assertEqual(
            dv.resolve_label("DOM-DORM", "ticket_priority", "普通"),
            "普通",
        )
        opts = dv.list_dict_options("DOM-IT", "ticket_priority")
        codes = [o["value"] for o in opts]
        self.assertEqual(codes, ["普通", "紧急", "高"])

    def test_domain_overrides_wildcard(self) -> None:
        rows = dv._seed_payload() + [
            {
                "domain_id": "DOM-DORM",
                "skin_id": "",
                "dict_key": "ticket_priority",
                "value_code": "普通",
                "label_zh": "一般",
                "sort": 0,
                "enabled": True,
                "source": "manual",
            }
        ]
        self.assertEqual(
            dv.resolve_label("DOM-DORM", "ticket_priority", "普通", rows=rows),
            "一般",
        )
        self.assertEqual(
            dv.resolve_label("DOM-PROPERTY", "ticket_priority", "普通", rows=rows),
            "普通",
        )

    def test_apply_injects_dicts_and_refund_labels(self) -> None:
        schema = {"domain": "DOM-SHOP", "labels": {}}
        out = dv.apply_dict_values_to_schema(schema, "DOM-SHOP")
        self.assertIn("dicts", out)
        refund = out["dicts"]["refund_type"]
        self.assertEqual(refund[0]["value"], "refund_only")
        self.assertEqual(out["labels"]["refundTypeRefundOnly"], "仅退款")
        self.assertEqual(out["labels"]["refundTypeReturnRefund"], "退货退款")

    def test_gap_reports_missing_code(self) -> None:
        rows = [
            r
            for r in dv._seed_payload()
            if not (r["dict_key"] == "refund_type" and r["value_code"] == "return_refund")
        ]
        report = dv.gap_report("DOM-SHOP", rows=rows)
        codes = {g["value_code"] for g in report["gaps"]}
        self.assertIn("return_refund", codes)
        self.assertNotIn("refund_only", codes)

    def test_build_domain_schema_shop_has_dicts(self) -> None:
        from app.bake.domain_schema import build_domain_schema

        schema = build_domain_schema("测试商城", "DOM-SHOP")
        self.assertIn("dicts", schema)
        self.assertEqual(schema["dicts"]["refund_type"][0]["label"], "仅退款")

    def test_dorm_schema_has_priority_dict(self) -> None:
        from app.bake.domain_schema import build_domain_schema

        schema = build_domain_schema("测试宿舍报修", "DOM-DORM")
        self.assertIn("ticket_priority", schema.get("dicts") or {})
        vals = [o["value"] for o in schema["dicts"]["ticket_priority"]]
        self.assertIn("普通", vals)

    def test_empty_rows_fallback_seed(self) -> None:
        self.assertEqual(
            dv.resolve_label("DOM-SHOP", "refund_type", "refund_only", rows=[]),
            "仅退款",
        )

    def test_seed_payload_unique_keys(self) -> None:
        """种子自身主键不撞；迁入只追加依赖此合同。"""
        rows = dv._seed_payload()
        keys = [
            (r["domain_id"], r["skin_id"], r["dict_key"], r["value_code"]) for r in rows
        ]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertGreaterEqual(len(rows), 80)

    def test_catalog_domain_gaps_zero(self) -> None:
        report = dv.catalog_domain_gaps()
        self.assertEqual(
            report["gap_count"],
            0,
            msg="; ".join(
                f"{g['domain_id']}.{g['dict_key']}.{g['value_code']}"
                for g in report["gaps"][:20]
            ),
        )
        self.assertEqual(report["domain_count"], 68)

    def test_named_ticket_priority_and_carrent_refund(self) -> None:
        self.assertEqual(
            dv.resolve_label("DOM-CERT", "ticket_priority", "普通"),
            "普通",
        )
        # 具名行优先于 *
        hit_dom = None
        for r in dv._seed_payload():
            if (
                r["domain_id"] == "DOM-CERT"
                and r["dict_key"] == "ticket_priority"
                and r["value_code"] == "普通"
            ):
                hit_dom = r["domain_id"]
                break
        self.assertEqual(hit_dom, "DOM-CERT")
        self.assertEqual(
            dv.resolve_label("DOM-CARRENT", "refund_type", "return_refund"),
            "退租退款",
        )
        self.assertEqual(
            dv.resolve_label("DOM-HOTEL", "refund_type", "return_refund"),
            "退订退款",
        )


if __name__ == "__main__":
    unittest.main()
