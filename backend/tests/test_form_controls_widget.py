"""C3：archiveFieldWidget 语义表钉死（Python 对齐 JS）。"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from app.bake.form_controls_widget import (
    WIDGET_CASES,
    WIDGET_KINDS,
    archive_field_widget,
)

_REPO = Path(__file__).resolve().parents[2]
_JS = (
    _REPO
    / "skeletons"
    / "baseline"
    / "frontend"
    / "src"
    / "utils"
    / "archiveFieldWidget.js"
)
_CONTROL = (
    _REPO
    / "skeletons"
    / "baseline"
    / "frontend"
    / "src"
    / "components"
    / "ArchiveFieldControl.vue"
)


class FormControlsWidgetC3Tests(unittest.TestCase):
    def test_cases_cover_expected_kinds(self) -> None:
        got = {exp for _, _, exp in WIDGET_CASES}
        # text/hidden 必有；其余主控件至少各一例
        for kind in (
            "hidden",
            "switch",
            "select",
            "datetime",
            "date",
            "time",
            "number",
            "money",
            "url",
            "textarea",
            "richtext",
            "text",
        ):
            self.assertIn(kind, got, f"WIDGET_CASES 缺 {kind}")
        self.assertTrue(got <= WIDGET_KINDS)

    def test_widget_cases(self) -> None:
        for field, ctx, expected in WIDGET_CASES:
            with self.subTest(field=field, ctx=ctx, expected=expected):
                self.assertEqual(
                    archive_field_widget(field, **ctx),
                    expected,
                )

    def test_js_decision_order_still_present(self) -> None:
        """改 JS 漏同步 Python 时先红这里。"""
        text = _JS.read_text(encoding="utf-8")
        needles = [
            "type === 'hidden'",
            "key === 'stock'",
            "type === 'boolean'",
            "type === 'select'",
            "type === 'datetime'",
            "type === 'date'",
            "type === 'time'",
            "type === 'url'",
            "type === 'textarea'",
            "type === 'richtext'",
            "type === 'number'",
            "isArchiveMoneyField",
            "承重|阻力|重量|时长|份量|容量|净含量|面积|租金",
            "摘要|备注|说明|特征|简介|描述",
        ]
        for n in needles:
            self.assertIn(n, text, f"archiveFieldWidget.js 缺 {n}")

    def test_archive_field_control_covers_widgets(self) -> None:
        """控制组件须渲染映射返回的主控件（text 为兜底；hidden 由父级跳过）。"""
        text = _CONTROL.read_text(encoding="utf-8")
        for kind in (
            "switch",
            "select",
            "datetime",
            "date",
            "time",
            "money",
            "number",
            "url",
            "textarea",
            "richtext",
        ):
            self.assertRegex(
                text,
                rf"widget\s*===\s*['\"]{re.escape(kind)}['\"]",
                f"ArchiveFieldControl 缺分支 {kind}",
            )


if __name__ == "__main__":
    unittest.main()
