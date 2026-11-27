"""论文图 SVG 共用小工具：一处实现，多图模块引用。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.bake.schema.diagram_svg_util import fmt1, read_json_dict, svg_esc, text_w_cjk


class DiagramSvgUtilTest(unittest.TestCase):
    def test_svg_esc_quotes(self):
        self.assertIn("&quot;", svg_esc('a"b'))
        self.assertIn("&lt;", svg_esc("<x>"))

    def test_fmt1(self):
        self.assertEqual(fmt1(1), "1.0")
        self.assertEqual(fmt1(12.34), "12.3")

    def test_text_w_cjk(self):
        self.assertGreater(text_w_cjk("中文", 12), text_w_cjk("ab", 12))

    def test_read_json_missing_modes(self):
        missing = Path(tempfile.gettempdir()) / "gf-no-such-json-util.json"
        self.assertIsNone(read_json_dict(missing))
        self.assertEqual(read_json_dict(missing, missing={}), {})

    def test_schema_modules_alias_shared(self):
        """关键图模块不得再各写一套 _esc/_f/_read_json 正文。"""
        root = Path(__file__).resolve().parents[1] / "app" / "bake" / "schema"
        util = (root / "diagram_svg_util.py").read_text(encoding="utf-8")
        self.assertIn("def svg_esc", util)
        self.assertIn("def fmt1", util)
        self.assertIn("def read_json_dict", util)
        for name in (
            "sequence.py",
            "architecture.py",
            "activity.py",
            "class_model.py",
            "modules.py",
            "er_svg.py",
            "usecases.py",
        ):
            src = (root / name).read_text(encoding="utf-8")
            with self.subTest(mod=name):
                self.assertIn("diagram_svg_util", src)
                self.assertNotIn("def _esc(s: str)", src)


if __name__ == "__main__":
    unittest.main()
