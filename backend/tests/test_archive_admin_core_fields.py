"""管理端档案表单：主通道语义不得再进 extraFields。"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SETUP = (
    REPO
    / "skeletons"
    / "baseline"
    / "frontend"
    / "src"
    / "views"
    / "admin"
    / "ArchiveAdmin.setup.js"
)


class ArchiveAdminCoreFieldsTests(unittest.TestCase):
    def test_core_keys_swallow_category_aliases(self) -> None:
        text = SETUP.read_text(encoding="utf-8")
        self.assertIn("CORE_FIELD_KEYS", text)
        for key in (
            "category",
            "categoryId",
            "categoryIds",
            "tagIds",
            "tagId",
            "stock",
            "coverUrl",
        ):
            self.assertIn(f"'{key}'", text, f"CORE 缺 {key}")
        # extraFields 须显式跳过 CORE + hidden + 适用表裁剪
        self.assertIn("CORE_FIELD_KEYS.has(f.key)", text)
        self.assertIn("t === 'hidden'", text)
        self.assertIn("isDetailAttrApplicable", text)
        self.assertIn("formCategoryNames", text)
        # 列表禁再出分类 ID 串（专用列已显示名称）
        self.assertIn("listExtraFields", text)
        self.assertIn("multi-select", text)
        self.assertIn("lab === '分类'", text)


if __name__ == "__main__":
    unittest.main()
