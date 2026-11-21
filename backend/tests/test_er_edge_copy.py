"""工厂表关系叙事：种子、注入 schema、缺口。"""

from __future__ import annotations

import unittest

from app.services import er_edge_copy as eec


class ErEdgeCopyUnit(unittest.TestCase):
    def setUp(self) -> None:
        eec.invalidate_cache()
        eec.bootstrap_from_seed()

    def test_seed_unique(self) -> None:
        rows = eec._seed_payload()
        keys = [eec._pair_key(r["table_a"], r["table_b"]) for r in rows]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertGreaterEqual(len(rows), 4)
        pairs = {(r["table_a"], r["table_b"]) for r in rows}
        self.assertIn(("biz_order", "biz_order_item"), pairs)

    def test_apply_writes_bag_and_list(self) -> None:
        out = eec.apply_er_edge_copy_to_schema({})
        self.assertIn("erEdgeCopy", out)
        self.assertIn("erEdgeCopyList", out)
        self.assertIn("biz_order|biz_order_item", out["erEdgeCopy"])
        self.assertTrue(out["erEdgeCopy"]["biz_order|biz_order_item"])
        self.assertTrue(any(x["table_a"] == "biz_order" for x in out["erEdgeCopyList"]))

    def test_apply_to_spec(self) -> None:
        spec = {"schema": {}}
        out = eec.apply_er_edge_copy_to_spec(spec)
        self.assertIn("erEdgeCopy", out["schema"])
        self.assertGreaterEqual(len(out["schema"]["erEdgeCopyList"]), 4)

    def test_gap_when_trimmed(self) -> None:
        seed = eec._seed_payload()
        trimmed = [
            r
            for r in seed
            if not (r.get("table_a") == "biz_order" and r.get("table_b") == "biz_order_item")
        ]
        report = eec.gap_report(rows=trimmed)
        pairs = {(g["table_a"], g["table_b"]) for g in report["gaps"]}
        self.assertIn(("biz_order", "biz_order_item"), pairs)

    def test_skips_empty_sentence(self) -> None:
        rows = [
            {
                "table_a": "a",
                "table_b": "b",
                "sentence_zh": "",
                "sort": 1,
                "source": "migrated",
            },
            {
                "table_a": "sys_user",
                "table_b": "biz_ticket",
                "sentence_zh": "一名用户可提交多张单据。",
                "sort": 2,
                "source": "migrated",
            },
        ]
        out = eec.apply_er_edge_copy_to_schema({}, rows=rows)
        self.assertNotIn("a|b", out["erEdgeCopy"])
        self.assertIn("sys_user|biz_ticket", out["erEdgeCopy"])

    def test_no_hardcoded_dom_put(self) -> None:
        from pathlib import Path

        src = Path(eec.__file__).read_text(encoding="utf-8")
        self.assertNotIn('put("DOM-', src)
        self.assertIn("load_seed_json", src)


if __name__ == "__main__":
    unittest.main()
