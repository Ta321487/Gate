"""工厂岗位×菜单矩阵：种子、bake 补齐、能力缺口。"""

from __future__ import annotations

import unittest

from app.services import menu_matrix as mm


class MenuMatrixUnit(unittest.TestCase):
    def setUp(self) -> None:
        mm.invalidate_cache()
        mm.bootstrap_from_seed()

    def test_seed_unique_and_has_ai(self) -> None:
        rows = mm._seed_payload()
        keys = [(r["domain_id"], r["role"], r["menu_id"]) for r in rows]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertGreaterEqual(len(rows), 5)
        aids = {(r["role"], r["menu_id"]) for r in rows if r.get("cap_id") == "ai_assistant"}
        self.assertIn(("admin", "ai_assistant"), aids)
        self.assertIn(("admin", "ai_knowledge"), aids)

    def test_always_on_dashboard_without_cap(self) -> None:
        schema = {"menus": {"admin": [], "staff": [], "user": []}, "capabilities": []}
        out = mm.apply_menu_matrix_to_schema(schema, "DOM-SHOP", addons={})
        admin_keys = {m.get("key") for m in out["menus"]["admin"]}
        self.assertIn("dashboard", admin_keys)
        user_keys = {m.get("key") for m in out["menus"]["user"]}
        self.assertIn("home", user_keys)
        self.assertNotIn("ai_assistant", admin_keys)

    def test_ai_cap_on_adds_menus(self) -> None:
        schema = {
            "menus": {"admin": [{"key": "dashboard", "label": "工作台"}], "user": []},
            "capabilities": ["ai_assistant"],
        }
        out = mm.apply_menu_matrix_to_schema(
            schema, "DOM-REPAIR", addons={"ai_assistant": True}
        )
        admin_keys = {m.get("key") for m in out["menus"]["admin"]}
        self.assertIn("ai_assistant", admin_keys)
        self.assertIn("ai_knowledge", admin_keys)
        user_keys = {m.get("key") for m in out["menus"]["user"]}
        self.assertIn("ai_assistant", user_keys)

    def test_does_not_duplicate_existing(self) -> None:
        schema = {
            "menus": {
                "admin": [{"key": "ai_assistant", "label": "已有"}],
            },
            "capabilities": ["ai_assistant"],
        }
        out = mm.apply_menu_matrix_to_schema(
            schema, "*", addons={"ai_assistant": True}
        )
        hits = [m for m in out["menus"]["admin"] if m.get("key") == "ai_assistant"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["label"], "已有")

    def test_apply_to_spec(self) -> None:
        spec = {
            "domain": "DOM-SHOP",
            "addons": {"ai_assistant": True},
            "capabilities": ["ai_assistant"],
            "schema": {"menus": {"admin": [], "staff": [], "user": []}},
        }
        out = mm.apply_menu_matrix_to_spec(spec)
        keys = {m.get("key") for m in out["schema"]["menus"]["admin"]}
        self.assertIn("dashboard", keys)
        self.assertIn("ai_assistant", keys)
        self.assertIn("menuMatrix", out["schema"])

    def test_gap_flags_missing_cap_menu(self) -> None:
        seed = mm._seed_payload()
        trimmed = [r for r in seed if r.get("menu_id") != "ai_knowledge"]
        report = mm.gap_report(rows=trimmed)
        reasons = " ".join(g["reason"] for g in report["gaps"])
        self.assertIn("ai_knowledge", "".join(g["menu_id"] for g in report["gaps"]))
        self.assertTrue("能力" in reasons or "种子" in reasons)

    def test_no_hardcoded_dom_put(self) -> None:
        from pathlib import Path

        src = Path(mm.__file__).read_text(encoding="utf-8")
        self.assertNotIn('put("DOM-', src)
        self.assertIn("load_seed_json", src)
        for role in mm.ROLES:
            self.assertIn(role, mm.ROLE_LABELS_ZH)


if __name__ == "__main__":
    unittest.main()
