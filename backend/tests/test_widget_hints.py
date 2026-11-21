"""工厂控件语义台：种子、匹配、学生投影、与 form_controls_widget 对齐。"""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from app.bake import form_controls_widget as fcw
from app.services import widget_hints as wh

_REPO = Path(__file__).resolve().parents[2]
_BASELINE_RULES = (
    _REPO / "skeletons" / "baseline" / "frontend" / "src" / "utils" / "fieldWidgetRules.js"
)
_LEGACY_JSON = (
    _REPO / "skeletons" / "baseline" / "frontend" / "src" / "utils" / "widgetHints.json"
)

# 台匹配 ↔ 投影匹配应对齐的探针（含 seed 典型标签）
_EQUIV_PROBES: tuple[tuple[str, str, str], ...] = (
    ("number", "needTrain", "是否需培训（1是0否）"),
    ("number", "flag", "启用标志（1是0否）"),
    ("number", "price", "单价（元）"),
    ("number", "fee", "挂号费"),
    ("string", "load", "承重"),
    ("string", "note", "备注"),
    ("string", "desc", "商品描述"),
    ("string", "title", "标题"),
    ("number", "qty", "数量"),
)


class WidgetHintsUnit(unittest.TestCase):
    def setUp(self) -> None:
        wh.invalidate_cache()
        wh.bootstrap_from_seed()

    def test_seed_unique_and_nonempty(self) -> None:
        rows = wh._seed_payload()
        keys = [r["rule_key"] for r in rows]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertGreaterEqual(len(rows), 4)

    def test_widget_and_scope_labels_cover_all(self) -> None:
        for kind in wh.WIDGET_KINDS:
            self.assertIn(kind, wh.WIDGET_LABELS_ZH)
            self.assertTrue(wh.WIDGET_LABELS_ZH[kind])
        for scope in wh.MATCH_SCOPES:
            self.assertIn(scope, wh.MATCH_SCOPE_LABELS_ZH)
        for typ in wh.WHEN_TYPES:
            if typ:
                self.assertIn(typ, wh.WHEN_TYPE_LABELS_ZH)

    def test_match_bool_label_to_switch(self) -> None:
        self.assertEqual(
            wh.match_widget_hint(
                field_type="number",
                key="needTrain",
                label="是否需培训（1是0否）",
            ),
            "switch",
        )

    def test_match_money_label(self) -> None:
        self.assertEqual(
            wh.match_widget_hint(field_type="number", key="price", label="单价（元）"),
            "money",
        )

    def test_match_numeric_string_exact(self) -> None:
        self.assertEqual(
            wh.match_widget_hint(field_type="string", key="load", label="承重"),
            "number",
        )

    def test_match_textarea_label(self) -> None:
        self.assertEqual(
            wh.match_widget_hint(field_type="string", key="note", label="备注"),
            "textarea",
        )

    def test_archive_field_widget_uses_hints(self) -> None:
        self.assertEqual(
            fcw.archive_field_widget(
                {"key": "needTrain", "type": "number", "label": "是否需培训（1是0否）"}
            ),
            "switch",
        )
        self.assertEqual(
            fcw.archive_field_widget({"key": "price", "type": "number", "label": "单价（元）"}),
            "money",
        )
        self.assertEqual(
            fcw.archive_field_widget({"key": "remark", "type": "string", "label": "备注"}),
            "textarea",
        )

    def test_project_student_rules_no_factory_vocab(self) -> None:
        rules = wh.project_student_rules()
        self.assertGreaterEqual(len(rules), 4)
        blob = json.dumps(rules, ensure_ascii=False)
        for banned in ("match_scope", "match_pattern", "when_type", "label_regex"):
            self.assertNotIn(banned, blob)
        self.assertTrue(any(r.get("labelHasAny") or r.get("labelIsAny") for r in rules))

    def test_factory_vs_student_projection_equivalent(self) -> None:
        for field_type, key, label in _EQUIV_PROBES:
            with self.subTest(field_type=field_type, key=key, label=label):
                factory = wh.match_widget_hint(field_type=field_type, key=key, label=label)
                student = wh.match_student_widget_hint(
                    field_type=field_type, key=key, label=label
                )
                self.assertEqual(factory, student)

    def test_write_field_widget_rules_js(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td)
            # 旧厂形残留应被清掉
            legacy = dest / "frontend" / "src" / "utils" / "widgetHints.json"
            legacy.parent.mkdir(parents=True, exist_ok=True)
            legacy.write_text("[]\n", encoding="utf-8")
            path = wh.write_field_widget_rules(dest)
            self.assertIsNotNone(path)
            assert path is not None
            text = path.read_text(encoding="utf-8")
            self.assertIn("export const FIELD_WIDGET_RULES", text)
            self.assertNotIn("match_scope", text)
            self.assertFalse(legacy.exists())

    def test_apply_to_schema_uses_student_projection(self) -> None:
        schema = wh.apply_widget_hints_to_schema({})
        self.assertIn("fieldWidgetRules", schema)
        self.assertNotIn("widgetHints", schema)
        self.assertGreaterEqual(len(schema["fieldWidgetRules"]), 4)

    def test_gap_when_rule_missing(self) -> None:
        rows = [r for r in wh._seed_payload() if r["rule_key"] != "money_label"]
        report = wh.gap_report(rows=rows)
        keys = {g["rule_key"] for g in report["gaps"]}
        self.assertIn("money_label", keys)

    def test_baseline_js_matches_projection(self) -> None:
        self.assertTrue(_BASELINE_RULES.is_file(), "缺 fieldWidgetRules.js")
        self.assertFalse(_LEGACY_JSON.exists(), "不应再保留 widgetHints.json")
        text = _BASELINE_RULES.read_text(encoding="utf-8")
        m = re.search(r"export const FIELD_WIDGET_RULES\s*=\s*(\[[\s\S]*\])\s*$", text)
        self.assertIsNotNone(m, "无法解析 FIELD_WIDGET_RULES")
        assert m is not None
        data = json.loads(m.group(1))
        self.assertEqual(data, wh.project_student_rules())

    def test_no_hardcoded_put(self) -> None:
        src = Path(wh.__file__).read_text(encoding="utf-8")
        self.assertIn("load_seed_json", src)
        self.assertNotIn('put("DOM-', src)
        self.assertIn("project_student_rules", src)


if __name__ == "__main__":
    unittest.main()
