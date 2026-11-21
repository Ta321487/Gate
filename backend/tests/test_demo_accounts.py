"""工厂测试账号卡：种子、域覆盖、三端齐全。"""

from __future__ import annotations

import unittest

from app.services import demo_accounts as da


class DemoAccountsUnit(unittest.TestCase):
    def setUp(self) -> None:
        da.invalidate_cache()
        da.bootstrap_from_seed()

    def test_seed_has_three_roles(self) -> None:
        rows = da._seed_payload()
        keys = [(r["domain_id"], r["role"]) for r in rows]
        self.assertEqual(len(keys), len(set(keys)))
        roles = {r["role"] for r in rows if r.get("domain_id") == "*"}
        self.assertEqual(roles, {"admin", "staff", "user"})

    def test_apply_wildcard(self) -> None:
        out = da.apply_demo_accounts_to_schema({}, "DOM-REPAIR")
        roles = [a["role"] for a in out["demoAccounts"]]
        self.assertEqual(roles, ["admin", "staff", "user"])
        admin = next(a for a in out["demoAccounts"] if a["role"] == "admin")
        self.assertEqual(admin["username"], "admin")
        self.assertTrue(admin["password"])

    def test_named_domain_overrides(self) -> None:
        rows = [
            {
                "domain_id": "*",
                "role": "admin",
                "username": "admin",
                "password": "admin123",
                "nickname_zh": "默认",
                "login_hint_zh": "",
                "sort": 1,
                "source": "migrated",
            },
            {
                "domain_id": "DOM-SHOP",
                "role": "admin",
                "username": "shopadmin",
                "password": "shop123",
                "nickname_zh": "店长",
                "login_hint_zh": "商城管理端",
                "sort": 1,
                "source": "migrated",
            },
            {
                "domain_id": "*",
                "role": "user",
                "username": "user",
                "password": "user123",
                "nickname_zh": "用户",
                "login_hint_zh": "",
                "sort": 2,
                "source": "migrated",
            },
        ]
        out = da.apply_demo_accounts_to_schema({}, "DOM-SHOP", rows=rows)
        by_role = {a["role"]: a for a in out["demoAccounts"]}
        self.assertEqual(by_role["admin"]["username"], "shopadmin")
        self.assertEqual(by_role["user"]["username"], "user")

    def test_apply_to_spec(self) -> None:
        spec = {"domain": "DOM-LIBRARY", "schema": {}}
        out = da.apply_demo_accounts_to_spec(spec)
        self.assertEqual(len(out["schema"]["demoAccounts"]), 3)

    def test_gap_flags_missing_role(self) -> None:
        trimmed = [r for r in da._seed_payload() if r.get("role") != "staff"]
        report = da.gap_report(rows=trimmed)
        roles = {g["role"] for g in report["gaps"]}
        self.assertIn("staff", roles)

    def test_role_labels_cover_all(self) -> None:
        for role in da.ROLES:
            self.assertIn(role, da.ROLE_LABELS_ZH)

    def test_no_hardcoded_dom_put(self) -> None:
        from pathlib import Path

        src = Path(da.__file__).read_text(encoding="utf-8")
        self.assertNotIn('put("DOM-', src)
        self.assertIn("load_seed_json", src)


if __name__ == "__main__":
    unittest.main()
