"""详情属性适用表：软皮登记；学生包只带 shopCatalogKind，不进 schema。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.domain_schema import scrub_schema_student_copy
from app.bake.features.detail_attrs import (
    niche_detail_attr_when,
    resolve_shop_catalog_kind,
)
from app.bake.shop_retail_niches import get_retail_niche

REPO = Path(__file__).resolve().parents[2]
WHEN_JS = (
    REPO
    / "skeletons"
    / "baseline"
    / "frontend"
    / "src"
    / "utils"
    / "detailAttrWhen.js"
)


class DetailAttrWhenTests(unittest.TestCase):
    def test_fitness_pack_has_when_table(self) -> None:
        when = niche_detail_attr_when("fitness")
        self.assertIn("loadCap", when)
        self.assertIn("resistance", when)
        self.assertTrue(any("哑铃" in x for x in when["loadCap"]))
        self.assertTrue(any("弹力带" in x for x in when["resistance"]))

    def test_fitness_title_resolves_catalog_kind(self) -> None:
        kind = resolve_shop_catalog_kind("方木健身用品电商平台", "")
        self.assertEqual(kind, "retail_fitness")

    def test_scrub_strips_detail_attr_when_from_schema(self) -> None:
        schema = scrub_schema_student_copy(
            {
                "detailAttrWhen": {"loadCap": {"categoryAny": ["哑铃"]}},
                "labels": {},
            }
        )
        self.assertNotIn("detailAttrWhen", schema)

    def test_baseline_js_mirrors_fitness_pack(self) -> None:
        js = WHEN_JS.read_text(encoding="utf-8")
        self.assertIn("WHEN_BY_CATALOG", js)
        self.assertIn("retail_fitness", js)
        pack = get_retail_niche("fitness")
        for key, needles in pack.detail_attr_when.items():
            self.assertIn(key, js)
            for n in needles:
                self.assertIn(n, js, f"基线 JS 缺皮表词 {n}")


if __name__ == "__main__":
    unittest.main()
