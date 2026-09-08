"""COPY / H22：学生可见面禁止「演示」业务措辞抽检。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES
from app.bake.gates.semantic import _DEMO_VISIBLE

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "skeletons" / "baseline"


class CopyH22Tests(unittest.TestCase):
    def test_wallet_e_sign_labels(self) -> None:
        self.assertEqual(CAPABILITIES["wallet"]["label"], "账户余额")
        self.assertNotIn("演示", CAPABILITIES["wallet"]["label"])
        self.assertEqual(CAPABILITIES["e_sign"]["label"], "本地签章")
        self.assertNotIn("演示", CAPABILITIES["e_sign"]["label"])

    def test_cart_pay_password_placeholder(self) -> None:
        cart = (BASELINE / "frontend/src/views/user/Cart.vue").read_text(encoding="utf-8")
        self.assertNotIn("演示密码", cart)
        self.assertIn("支付密码，任意不少于 4 位", cart)

    def test_grade_notice_no_demo_lib(self) -> None:
        sql = (
            ROOT / "backend/app/bake/sql/templates/DOM-GRADE.sql"
        ).read_text(encoding="utf-8")
        self.assertNotIn("演示库", sql)
        self.assertIn("预置课程", sql)

    def test_semantic_patterns_cover_common_phrases(self) -> None:
        for s in (
            "演示密码",
            "演示余额",
            "演示通行码",
            "本期演示",
            "演示库",
            "本地签章演示",
            "演示支付",
            "演示物流",
            "演示数据",
            "演示账号",
        ):
            self.assertIsNotNone(_DEMO_VISIBLE.search(s), s)
        # 合法业务词：实验演示 / 演示教具 不在扩展黑名单（无「演示X」坏词）
        self.assertIsNone(_DEMO_VISIBLE.search("实验演示分类浏览"))
        self.assertIsNone(_DEMO_VISIBLE.search("演示教具分类检索"))


if __name__ == "__main__":
    unittest.main()
