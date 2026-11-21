"""工厂演示剧本台：种子、注入、缺口、全族覆盖。"""

from __future__ import annotations

import unittest

from app.bake.catalog import DOMAINS
from app.services import demo_scripts as ds


class DemoScriptsUnit(unittest.TestCase):
    def setUp(self) -> None:
        ds.invalidate_cache()
        ds.bootstrap_from_seed()

    def test_seed_covers_all_catalog_domains(self) -> None:
        rows = ds._seed_payload()
        doms = {r["domain_id"] for r in rows}
        self.assertEqual(doms, set(DOMAINS))
        self.assertGreaterEqual(len(rows), len(DOMAINS))

    def test_seed_unique_keys(self) -> None:
        rows = ds._seed_payload()
        keys = [
            (r["domain_id"], r.get("skin_id") or "", r.get("script_id") or "default", int(r["step_no"]))
            for r in rows
        ]
        self.assertEqual(len(keys), len(set(keys)))

    def test_shop_has_demo_script_steps(self) -> None:
        steps = ds.list_script_steps("DOM-SHOP")
        self.assertGreaterEqual(len(steps), 2)
        self.assertTrue(all(s.get("title") for s in steps))

    def test_apply_injects_demo_script(self) -> None:
        schema = {"domain": "DOM-LIBRARY"}
        out = ds.apply_demo_script_to_schema(schema, "DOM-LIBRARY")
        self.assertIn("demoScript", out)
        self.assertEqual(out["demoScript"]["id"], "default")
        self.assertGreaterEqual(len(out["demoScript"]["steps"]), 1)

    def test_build_domain_schema_has_demo_script(self) -> None:
        from app.bake.domain_schema import build_domain_schema

        schema = build_domain_schema("测试图书", "DOM-LIBRARY")
        self.assertIn("demoScript", schema)
        self.assertTrue(schema["demoScript"]["steps"])

    def test_gap_when_domain_missing(self) -> None:
        report = ds.gap_report("DOM-SHOP", rows=[])
        self.assertEqual(report["gap_count"], 1)
        filled = ds.gap_report("DOM-SHOP")
        self.assertEqual(filled["gap_count"], 0)

    def test_no_hardcoded_put_in_service(self) -> None:
        from pathlib import Path

        src = Path(ds.__file__).read_text(encoding="utf-8")
        self.assertNotIn('put("DOM-', src)
        self.assertIn("load_seed_json", src)


if __name__ == "__main__":
    unittest.main()
