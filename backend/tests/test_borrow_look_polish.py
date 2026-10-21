"""借用组观感再磨（详情借阅文案）护栏。

钉住：独立详情按 borrowSurfaceStyle 换主按钮与须知文案，禁止一律「申请办理」。
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DETAIL = (
    REPO
    / "skeletons"
    / "baseline"
    / "frontend"
    / "src"
    / "views"
    / "user"
    / "ArchiveItemDetail.vue"
)


class BorrowLookPolishTests(unittest.TestCase):
    def test_detail_borrow_copy(self) -> None:
        text = DETAIL.read_text(encoding="utf-8")
        for needle in (
            "borrowSurfaceOn",
            "borrowSurface",
            "'立即借阅'",
            "'申请床位'",
            "'申请取件'",
            "'申请借用'",
            "'借阅说明'",
            "'取件说明'",
            "'床位说明'",
            "'借用说明'",
            "我的借阅",
            "我的借用",
            "openApply",
        ):
            self.assertIn(needle, text, f"ArchiveItemDetail 缺 {needle}")
        # 须知优先于笼统「办理说明」分支
        self.assertLess(
            text.find("borrowSurfaceOn.value"),
            text.find("return '办理说明'"),
        )


if __name__ == "__main__":
    unittest.main()
