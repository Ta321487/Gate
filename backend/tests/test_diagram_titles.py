"""工厂论文图题模板：种子、域覆盖、出图消费。"""

from __future__ import annotations

import unittest

from app.services import diagram_titles as dt


class DiagramTitlesUnit(unittest.TestCase):
    def setUp(self) -> None:
        dt.invalidate_cache()
        dt.bootstrap_from_seed()

    def test_seed_covers_all_kinds(self) -> None:
        rows = dt._seed_payload()
        kinds = {r["diagram_kind"] for r in rows if r.get("domain_id") == "*"}
        self.assertTrue(dt.DIAGRAM_KINDS.issubset(kinds), kinds)

    def test_resolve_wildcard(self) -> None:
        title = dt.resolve_figure_title("class", domain="DOM-REPAIR", name="报修系统")
        self.assertEqual(title, "报修系统类图")

    def test_named_domain_overrides(self) -> None:
        rows = [
            {
                "diagram_kind": "class",
                "domain_id": "*",
                "title_tpl": "{name}类图",
                "sort": 1,
                "source": "migrated",
            },
            {
                "diagram_kind": "class",
                "domain_id": "DOM-SHOP",
                "title_tpl": "{name}系统类图",
                "sort": 1,
                "source": "migrated",
            },
        ]
        title = dt.resolve_figure_title(
            "class", domain="DOM-SHOP", name="商城", rows=rows
        )
        self.assertEqual(title, "商城系统类图")
        other = dt.resolve_figure_title(
            "class", domain="DOM-LIBRARY", name="图书", rows=rows
        )
        self.assertEqual(other, "图书类图")

    def test_apply_to_schema(self) -> None:
        out = dt.apply_diagram_titles_to_schema(
            {"title": "小羽自习室", "labels": {"systemName": "小羽自习室"}},
            "DOM-GENERIC",
        )
        bag = out["diagramTitleTemplates"]
        self.assertEqual(bag["class"], "小羽自习室类图")
        self.assertEqual(bag["modules"], "小羽自习室功能模块图")

    def test_figure_title_from_schema_prefers_bag(self) -> None:
        schema = {"diagramTitleTemplates": {"architecture": "定制架构图"}}
        self.assertEqual(
            dt.figure_title_from_schema(schema, "architecture", name="X"),
            "定制架构图",
        )

    def test_apply_to_spec(self) -> None:
        spec = {"domain": "DOM-LIBRARY", "schema": {"title": "图书系统"}}
        out = dt.apply_diagram_titles_to_spec(spec)
        self.assertIn("diagramTitleTemplates", out["schema"])
        self.assertIn("类图", out["schema"]["diagramTitleTemplates"]["class"])

    def test_gap_flags_missing_kind(self) -> None:
        trimmed = [r for r in dt._seed_payload() if r.get("diagram_kind") != "er"]
        report = dt.gap_report(rows=trimmed)
        kinds = {g["diagram_kind"] for g in report["gaps"]}
        self.assertIn("er", kinds)

    def test_kind_labels_cover_all(self) -> None:
        for kind in dt.DIAGRAM_KINDS:
            self.assertIn(kind, dt.KIND_LABELS_ZH)

    def test_no_hardcoded_dom_put(self) -> None:
        from pathlib import Path

        src = Path(dt.__file__).read_text(encoding="utf-8")
        self.assertNotIn('put("DOM-', src)
        self.assertIn("load_seed_json", src)


if __name__ == "__main__":
    unittest.main()
