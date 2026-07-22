"""论文测试用例：menus 驱动，5～9 列模板投影；LLM 仅润色文案。"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.bake.schema.testcases import (
    DEFAULT_TESTCASE_FIELDS,
    apply_testcase_label_patch,
    normalize_testcase_fields,
    sanitize_testcase_label_patch,
    testcase_model,
)


class TestcaseTests(unittest.TestCase):
    def _schema(self, stem: str) -> dict:
        path = Path(__file__).resolve().parents[0] / "golden" / "schema" / f"{stem}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_normalize_fields(self) -> None:
        self.assertEqual(normalize_testcase_fields(6), 6)
        self.assertEqual(normalize_testcase_fields("9"), 9)
        self.assertEqual(normalize_testcase_fields(99), DEFAULT_TESTCASE_FIELDS)

    def test_hospital_has_login_and_menu_cases(self) -> None:
        model = testcase_model(self._schema("DOM-HOSPITAL"), fields=6)
        self.assertEqual(model["fields"], 6)
        self.assertGreater(model["count"], 5)
        ids = [r["id"] for r in model["rows"]]
        self.assertTrue(any(i.startswith("TC-LOGIN-") for i in ids))
        titles = [c["title"] for c in model["columns"]]
        self.assertEqual(
            titles,
            ["编号", "测试项", "操作步骤", "输入数据", "预期结果", "实际结果"],
        )
        blob = model["markdown"]
        self.assertNotIn("电子病历", blob)
        self.assertNotIn("医保", blob)

    def test_field_templates(self) -> None:
        schema = self._schema("DOM-SHOP")
        for n, expect_n in ((5, 5), (7, 7), (8, 8), (9, 9)):
            model = testcase_model(schema, fields=n)
            self.assertEqual(len(model["columns"]), expect_n)
            self.assertEqual(len(model["rows"][0]), expect_n)
        m5 = testcase_model(schema, fields=5)
        self.assertEqual(m5["columns"][1]["title"], "测试功能")
        self.assertEqual(m5["columns"][-1]["title"], "测试结果")
        m9 = testcase_model(schema, fields=9)
        self.assertEqual(m9["columns"][1]["title"], "测试模块")
        self.assertIn("前置条件", [c["title"] for c in m9["columns"]])

    def test_only_delivered_menus(self) -> None:
        schema = {
            "title": "最小系统",
            "labels": {"appName": "最小系统"},
            "roles": {"user": {"label": "用户"}, "admin": {"label": "管理员"}},
            "entities": {"archive": {"label": "事项"}},
            "menus": {
                "user": [{"key": "profile", "label": "个人资料"}],
                "admin": [{"key": "users", "label": "用户管理"}],
            },
            "capabilities": ["org_users"],
        }
        model = testcase_model(schema, fields=6)
        blob = " ".join(r["item"] for r in model["rows"])
        self.assertIn("个人资料", blob)
        self.assertIn("用户", blob)
        self.assertNotIn("购物车", blob)
        self.assertNotIn("挂号", blob)

    def test_sanitize_rejects_invented_ids(self) -> None:
        clean = sanitize_testcase_label_patch(
            {
                "cases": {
                    "TC-LOGIN-001": {"steps": "①打开登录页 ②输入账号 ③登录"},
                    "TC-HACK-999": {"steps": "发明功能"},
                    "TC-LOGIN-002": {"item": "不许改测试项", "expected": "提示错误"},
                }
            },
            {"TC-LOGIN-001", "TC-LOGIN-002"},
        )
        cases = clean["cases"]
        self.assertIn("TC-LOGIN-001", cases)
        self.assertNotIn("TC-HACK-999", cases)
        self.assertNotIn("item", cases.get("TC-LOGIN-002", {}))
        self.assertEqual(cases["TC-LOGIN-002"]["expected"], "提示错误")

    def test_apply_patch_only_prose(self) -> None:
        rows = [
            {
                "id": "TC-LOGIN-001",
                "module": "登录模块",
                "item": "正确用户名密码登录",
                "precondition": "旧前置",
                "steps": "旧步骤",
                "input": "旧输入",
                "expected": "旧预期",
                "actual": "与预期一致",
                "verdict": "通过",
            }
        ]
        out = apply_testcase_label_patch(
            rows,
            {
                "cases": {
                    "TC-LOGIN-001": {
                        "steps": "①打开登录页 ②输入用户名密码 ③点击登录",
                        "expected": "登录成功进入首页",
                    }
                }
            },
        )
        self.assertEqual(out[0]["item"], "正确用户名密码登录")
        self.assertEqual(out[0]["module"], "登录模块")
        self.assertIn("打开登录页", out[0]["steps"])
        self.assertEqual(out[0]["expected"], "登录成功进入首页")


if __name__ == "__main__":
    unittest.main()
