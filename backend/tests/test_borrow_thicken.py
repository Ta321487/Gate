"""借用/占用族：表数下限 10，三套补丁两端菜单可达。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import attach_accept
from app.bake.domains import BORROW_FAMILY_DOMAINS, DOMAIN_CAPABILITIES, DOMAINS
from app.bake.engine_sql import count_create_tables, domain_sql, table_budget_bounds
from app.bake.gate_contracts import dual_surface_menu_keys


def _borrow_ids() -> list[str]:
    return sorted(BORROW_FAMILY_DOMAINS)


class BorrowFamilyThickenTests(unittest.TestCase):
    def test_borrow_family_table_floor(self) -> None:
        for domain in _borrow_ids():
            with self.subTest(domain=domain):
                lo, hi = table_budget_bounds(domain)
                self.assertEqual(lo, 10)
                sql = domain_sql(
                    domain,
                    "db_test",
                    capabilities=list(DOMAIN_CAPABILITIES.get(domain) or []),
                    title=DOMAINS[domain]["label"],
                )
                n = count_create_tables(sql)
                self.assertGreaterEqual(n, lo, f"{domain} tables={n}")
                self.assertLessEqual(n, hi, f"{domain} tables={n}")

    def test_non_borrow_floor_stays_six(self) -> None:
        lo, _hi = table_budget_bounds("DOM-DORM")
        self.assertEqual(lo, 6)

    def test_ledger_span_material_dual_menus(self) -> None:
        samples = {
            "DOM-FUND": "balance_ledger",
            "DOM-ATTEND": "occupy_span",
            "DOM-CLUB": "material_check",
        }
        for domain, cap in samples.items():
            with self.subTest(domain=domain):
                out = attach_accept(
                    {
                        "domain": domain,
                        "title": DOMAINS[domain]["label"],
                        "capabilities": list(DOMAIN_CAPABILITIES[domain]),
                    },
                    "",
                )
                schema = out.get("schema") or {}
                caps = set(schema.get("capabilities") or [])
                self.assertIn(cap, caps)
                menus = schema.get("menus") or {}
                admin_keys = {
                    m.get("key")
                    for m in (menus.get("admin") or [])
                    if isinstance(m, dict)
                }
                user_keys = {
                    m.get("key")
                    for m in (menus.get("user") or [])
                    if isinstance(m, dict)
                }
                need_admin, need_user = dual_surface_menu_keys(cap)
                self.assertTrue(
                    need_admin & admin_keys,
                    f"{domain} admin missing {need_admin - admin_keys}",
                )
                self.assertTrue(
                    need_user & user_keys,
                    f"{domain} user missing {need_user - user_keys}",
                )

    def test_ledger_unit_follows_domain(self) -> None:
        expect = {
            "DOM-FUND": "元",
            "DOM-EXPENSE": "元",
            "DOM-SEAL": "次",
            "DOM-RECRUIT": "次",
            "DOM-CREDIT": "学分",
            "DOM-LABOR": "小时",
            "DOM-MORAL": "分",
            "DOM-AWARD": "学分",
        }
        for domain, unit in expect.items():
            with self.subTest(domain=domain):
                out = attach_accept(
                    {
                        "domain": domain,
                        "title": DOMAINS[domain]["label"],
                        "capabilities": list(DOMAIN_CAPABILITIES[domain]),
                    },
                    "",
                )
                labels = (out.get("schema") or {}).get("labels") or {}
                self.assertEqual(labels.get("balanceUnit"), unit)
                sql = domain_sql(
                    domain,
                    "db_test",
                    capabilities=list(DOMAIN_CAPABILITIES.get(domain) or []),
                    title=DOMAINS[domain]["label"],
                )
                self.assertIn(f"'{unit}'", sql)


if __name__ == "__main__":
    unittest.main()
