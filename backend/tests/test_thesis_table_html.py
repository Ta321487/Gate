"""论文材料表 HTML：校模板三线+轻网格口径。"""

from __future__ import annotations

import unittest

from app.bake.schema.thesis_table_html import (
    THICK,
    THIN,
    kv_rows_to_html_table,
    rows_to_html_table,
)


class ThesisTableHtmlTests(unittest.TestCase):
    def test_grid_uses_thick_header_and_no_border1(self) -> None:
        html = rows_to_html_table(
            [
                ["功能编号", "功能名称"],
                ["1", "字典表同步接口"],
                ["2", "号段查询接口"],
            ]
        )
        self.assertIn('border="0"', html)
        self.assertNotIn('border="1"', html)
        self.assertIn(THICK, html)
        self.assertIn(THIN, html)
        self.assertIn("功能编号", html)
        self.assertIn("号段查询接口", html)
        # 表头行粗底线；末行粗底线
        self.assertGreaterEqual(html.count(f"border-bottom:{THICK}"), 2)

    def test_kv_outer_thick_no_header_midline_as_header_row(self) -> None:
        html = kv_rows_to_html_table(
            [
                ("用例名称", "登录"),
                ("执行者", "用户"),
                ("简要说明", "进入系统"),
            ]
        )
        self.assertIn('border="0"', html)
        self.assertIn("用例名称", html)
        self.assertIn("登录", html)
        self.assertIn(f"border-top:{THICK}", html)
        self.assertIn(f"border-bottom:{THICK}", html)


if __name__ == "__main__":
    unittest.main()
