"""工厂状态机话术台：种子、解析、注入、缺口。"""

from __future__ import annotations

import unittest

from app.services import status_copy as sc


class StatusCopyUnit(unittest.TestCase):
    def setUp(self) -> None:
        sc.invalidate_cache()
        sc.bootstrap_from_seed()

    def test_seed_shop_order_and_ticket_wildcard(self) -> None:
        shop_pending = sc.resolve_status("DOM-SHOP", "order", "pending")
        self.assertIsNotNone(shop_pending)
        assert shop_pending is not None
        self.assertEqual(shop_pending["label"], "待付款")
        self.assertEqual(shop_pending["action"], "去付款")

        ticket = sc.resolve_status("DOM-LIBRARY", "ticket", "pending")
        self.assertIsNotNone(ticket)
        assert ticket is not None
        self.assertEqual(ticket["label"], "待审核")
        self.assertEqual(ticket["domain_id"], "DOM-LIBRARY")
        # 无专行的域吃 *
        generic = sc.resolve_status("DOM-CERT", "ticket", "pending")
        assert generic is not None
        self.assertEqual(generic["label"], "待审")
        self.assertEqual(generic["domain_id"], "*")

    def test_domain_overrides_wildcard(self) -> None:
        rows = sc._seed_payload() + [
            {
                "domain_id": "DOM-LIBRARY",
                "machine_id": "ticket",
                "status_code": "pending",
                "label_zh": "待馆员审",
                "action_zh": "通过",
                "empty_zh": "",
                "for_roles": "admin,staff,user",
                "source": "manual",
            }
        ]
        hit = sc.resolve_status("DOM-LIBRARY", "ticket", "pending", rows=rows)
        self.assertEqual(hit["label"], "待馆员审")
        # 无专行域仍吃 *（CERT 不在种子专行里）
        other = sc.resolve_status("DOM-CERT", "ticket", "pending", rows=rows)
        self.assertEqual(other["label"], "待审")

    def test_apply_injects_status_copy_and_states(self) -> None:
        schema = {
            "domain": "DOM-SHOP",
            "entities": {
                "order": {
                    "states": {
                        "pending": "旧名",
                        "confirmed": "旧确认",
                        "completed": "旧完成",
                    }
                }
            },
        }
        out = sc.apply_status_copy_to_schema(schema, "DOM-SHOP")
        self.assertIn("statusCopy", out)
        self.assertEqual(out["statusCopy"]["order"]["pending"]["label"], "待付款")
        self.assertEqual(out["entities"]["order"]["states"]["pending"], "待付款")
        self.assertEqual(out["entities"]["order"]["states"]["confirmed"], "待发货")

    def test_gap_reports_missing_status(self) -> None:
        schema = {
            "entities": {
                "order": {
                    "states": {
                        "pending": "待付款",
                        "weird_state": "怪态",
                    }
                }
            }
        }
        report = sc.gap_report("DOM-SHOP", schema)
        codes = {g["status_code"] for g in report["gaps"]}
        self.assertIn("weird_state", codes)
        self.assertNotIn("pending", codes)

    def test_build_domain_schema_shop_has_status_copy(self) -> None:
        from app.bake.domain_schema import build_domain_schema

        schema = build_domain_schema("测试商城", "DOM-SHOP")
        self.assertIn("statusCopy", schema)
        self.assertEqual(schema["statusCopy"]["order"]["pending"]["label"], "待付款")
        states = (schema.get("entities") or {}).get("order", {}).get("states") or {}
        self.assertEqual(states.get("pending"), "待付款")

    def test_empty_rows_fallback_seed(self) -> None:
        hit = sc.resolve_status("DOM-SHOP", "order", "shipped", rows=[])
        self.assertEqual(hit["label"], "已发货")

    def test_all_domains_zero_status_gaps(self) -> None:
        """68 域实体 states 相对种子零缺口（跳过 status_copy 覆盖后再扫）。"""
        from app.bake.catalog import DOMAINS
        from app.bake import domain_schema as ds

        seed = sc._seed_payload()
        saved_sc = sc.apply_status_copy_to_schema
        from app.services import dict_values as dv

        saved_dv = dv.apply_dict_values_to_schema
        sc.apply_status_copy_to_schema = lambda s, d, **k: s  # type: ignore[assignment]
        dv.apply_dict_values_to_schema = lambda s, d, **k: s  # type: ignore[assignment]
        try:
            bad: list[str] = []
            for dom in sorted(DOMAINS):
                sch = ds.build_domain_schema("缺口审计", dom)
                report = sc.gap_report(dom, sch, rows=seed)
                if report["gap_count"]:
                    codes = [
                        f"{g['machine_id']}.{g['status_code']}" for g in report["gaps"]
                    ]
                    bad.append(f"{dom}:{','.join(codes)}")
            self.assertEqual(bad, [], msg="; ".join(bad[:20]))
        finally:
            sc.apply_status_copy_to_schema = saved_sc  # type: ignore[assignment]
            dv.apply_dict_values_to_schema = saved_dv  # type: ignore[assignment]

    def test_food_cinema_carrent_reservation_labels(self) -> None:
        self.assertEqual(
            sc.resolve_status("DOM-FOOD", "order", "pending")["label"], "待出餐"
        )
        self.assertEqual(
            sc.resolve_status("DOM-CINEMA", "order", "pending")["label"], "待取票"
        )
        self.assertEqual(
            sc.resolve_status("DOM-HOSPITAL", "reservation", "confirmed")["label"],
            "已挂号",
        )
        self.assertEqual(
            sc.resolve_status("DOM-RECRUIT", "ticket", "pending_final")["label"],
            "待面试",
        )

    def test_seed_payload_unique_keys(self) -> None:
        rows = sc._seed_payload()
        keys = [(r["domain_id"], r["machine_id"], r["status_code"]) for r in rows]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertGreaterEqual(len(rows), 100)


if __name__ == "__main__":
    unittest.main()
