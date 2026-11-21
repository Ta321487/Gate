"""工厂错误码中文台：种子、schema 注入、JSON 写出、缺口。"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.services import error_copy as ec


class ErrorCopyUnit(unittest.TestCase):
    def setUp(self) -> None:
        ec.invalidate_cache()
        ec.bootstrap_from_seed()

    def test_seed_covers_expected_codes(self) -> None:
        seed_codes = {r["error_code"] for r in ec._seed_payload()}
        expected = {c for c, _ in ec.EXPECTED_ERROR_CODES}
        self.assertEqual(seed_codes, expected)
        keys = [r["error_code"] for r in ec._seed_payload()]
        self.assertEqual(len(keys), len(set(keys)))

    def test_resolve_prefers_explicit_message(self) -> None:
        self.assertEqual(
            ec.resolve_message("NOT_FOUND", fallback="订单不存在"),
            "订单不存在",
        )
        self.assertEqual(ec.resolve_message("UNAUTHORIZED"), "请先登录")

    def test_apply_injects_error_copy(self) -> None:
        schema = {"domain": "DOM-SHOP"}
        out = ec.apply_error_copy_to_schema(schema)
        self.assertIn("errorCopy", out)
        self.assertEqual(out["errorCopy"]["FORBIDDEN"]["message"], "没有权限")
        self.assertEqual(out["errorCopy"]["FORBIDDEN"]["code"], 40300)

    def test_build_domain_schema_has_error_copy(self) -> None:
        from app.bake.domain_schema import build_domain_schema

        schema = build_domain_schema("测试商城", "DOM-SHOP")
        self.assertIn("errorCopy", schema)
        self.assertIn("INTERNAL", schema["errorCopy"])

    def test_write_error_messages_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td)
            path = ec.write_error_messages_json(dest)
            self.assertIsNotNone(path)
            assert path is not None
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data.get("OK"), "成功")
            self.assertEqual(data.get("CAPTCHA_INVALID"), "验证码不正确")

    def test_gap_when_code_missing(self) -> None:
        rows = [r for r in ec._seed_payload() if r["error_code"] != "INTERNAL"]
        report = ec.gap_report(rows=rows)
        codes = {g["error_code"] for g in report["gaps"]}
        self.assertIn("INTERNAL", codes)
        self.assertNotIn("OK", codes)

    def test_java_fallback_matches_seed(self) -> None:
        """骨架内置回落与种子同文，避免双真源漂移。"""
        root = Path(__file__).resolve().parents[2]
        java = (
            root
            / "skeletons"
            / "baseline"
            / "backend"
            / "src"
            / "main"
            / "java"
            / "com"
            / "thesis"
            / "common"
            / "ErrorMessages.java"
        ).read_text(encoding="utf-8")
        for r in ec._seed_payload():
            code = r["error_code"]
            msg = r["message_zh"]
            self.assertIn(f'"{code}"', java)
            self.assertIn(f'"{msg}"', java)

    def test_no_hardcoded_put(self) -> None:
        src = Path(ec.__file__).read_text(encoding="utf-8")
        self.assertIn("load_seed_json", src)
        self.assertNotIn('put("DOM-', src)


if __name__ == "__main__":
    unittest.main()
