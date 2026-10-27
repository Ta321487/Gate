"""详情属性出字段：量纲类须 number，禁 string 文本框。"""

from __future__ import annotations

import unittest

from app.bake.features.detail_attrs import (
    apply_detail_attrs_to_spec,
    detail_attr_fields,
)


class DetailAttrsFieldTypesTests(unittest.TestCase):
    def test_load_cap_resistance_are_number(self) -> None:
        by_label = {f["label"]: f for f in detail_attr_fields(["材质", "承重", "阻力", "重量"])}
        self.assertEqual(by_label["材质"]["type"], "string")
        self.assertEqual(by_label["承重"]["type"], "number")
        self.assertEqual(by_label["阻力"]["type"], "number")
        self.assertEqual(by_label["重量"]["type"], "number")

    def test_rebake_upgrades_existing_string_numeric(self) -> None:
        spec = {
            "domain": "DOM-SHOP",
            "title": "测",
            "capabilities": ["archive", "detail_attrs"],
            "schema": {
                "capabilities": ["archive", "detail_attrs"],
                "entities": {
                    "archive": {
                        "fields": [
                            {"key": "loadCap", "label": "承重", "type": "string"},
                            {"key": "resistance", "label": "阻力", "type": "string"},
                            {"key": "material", "label": "材质", "type": "string"},
                        ]
                    }
                },
            },
        }
        out = apply_detail_attrs_to_spec(spec, "展示承重、阻力等参数")
        fields = {
            f["key"]: f
            for f in ((out.get("schema") or {}).get("entities") or {})
            .get("archive", {})
            .get("fields")
            or []
            if isinstance(f, dict)
        }
        self.assertEqual(fields["loadCap"]["type"], "number")
        self.assertEqual(fields["resistance"]["type"], "number")
        self.assertEqual(fields["material"]["type"], "string")


if __name__ == "__main__":
    unittest.main()
