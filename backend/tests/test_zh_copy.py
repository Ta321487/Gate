"""中文句：数字/字母两侧不留空格。"""

from __future__ import annotations

import unittest

from app.bake.schema.zh_copy import squeeze_cjk_alnum_spaces


class ZhCopyTests(unittest.TestCase):
    def test_table_no_and_latin(self) -> None:
        self.assertEqual(squeeze_cjk_alnum_spaces("表 3.1 所示"), "表3.1所示")
        self.assertEqual(
            squeeze_cjk_alnum_spaces("见表 3.1 所示。"),
            "见表3.1所示。",
        )
        self.assertEqual(
            squeeze_cjk_alnum_spaces("共设计 12 张数据表"),
            "共设计12张数据表",
        )
        self.assertEqual(
            squeeze_cjk_alnum_spaces("使用 Vue 与 Spring Boot"),
            "使用Vue与Spring Boot",
        )

    def test_idempotent_and_keep_cjk_phrase(self) -> None:
        s = "观众使用账号密码登录本系统。"
        self.assertEqual(squeeze_cjk_alnum_spaces(s), s)
        self.assertEqual(
            squeeze_cjk_alnum_spaces(squeeze_cjk_alnum_spaces("表 4.2")),
            "表4.2",
        )


if __name__ == "__main__":
    unittest.main()
