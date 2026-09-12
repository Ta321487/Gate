"""DeepSeek 模型目录 / 别名。"""

from __future__ import annotations

import unittest

from app.llm.client import resolve_model
from app.llm.model_catalog import (
    DEEPSEEK_DEFAULT_MODEL,
    deepseek_model_options_payload,
    resolve_deepseek_model,
)


class DeepseekModelCatalogTests(unittest.TestCase):
    def test_default_is_official_flash(self) -> None:
        self.assertEqual(DEEPSEEK_DEFAULT_MODEL, "deepseek-flash")
        self.assertEqual(resolve_deepseek_model(""), "deepseek-flash")
        self.assertEqual(resolve_model("", provider="deepseek"), "deepseek-flash")

    def test_legacy_aliases(self) -> None:
        for old in (
            "deepseek-chat",
            "deepseek-reasoner",
            "deepseek-v4-flash",
            "deepseek-v4-flash-vision-exp",
        ):
            self.assertEqual(resolve_deepseek_model(old), "deepseek-flash", msg=old)

    def test_options_include_official_id(self) -> None:
        ids = {o["id"] for o in deepseek_model_options_payload()}
        self.assertIn("deepseek-flash", ids)


if __name__ == "__main__":
    unittest.main()
