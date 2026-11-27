"""工厂 Swagger：tags 挂在 APIRouter 上；禁止 default；禁止事后改写 OpenAPI。"""

from __future__ import annotations

import unittest
from collections import Counter
from pathlib import Path


class OpenApiTagsContract(unittest.TestCase):
    def test_no_openapi_retag_patch(self) -> None:
        main = (Path(__file__).resolve().parents[1] / "app" / "main.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("_retag_openapi_paths", main)
        self.assertNotIn("custom_openapi", main)
        self.assertIn('APIRouter(tags=["论文材料"])', (
            Path(__file__).resolve().parents[1]
            / "app"
            / "api"
            / "projects"
            / "schema.py"
        ).read_text(encoding="utf-8"))
        self.assertIn('APIRouter(tags=["终稿吸收"])', (
            Path(__file__).resolve().parents[1]
            / "app"
            / "api"
            / "system_thesis_absorb.py"
        ).read_text(encoding="utf-8"))

    def test_runtime_tags_split_and_no_default(self) -> None:
        from app.main import app

        app.openapi_schema = None
        schema = app.openapi()
        tags: Counter[str] = Counter()
        for _path, methods in (schema.get("paths") or {}).items():
            for method, op in methods.items():
                if method.startswith("x-") or not isinstance(op, dict):
                    continue
                for name in op.get("tags") or ["default"]:
                    tags[name] += 1

        self.assertEqual(tags.get("default", 0), 0)
        self.assertEqual(tags.get("资产台", 0), 0)
        self.assertGreater(tags.get("终稿吸收", 0), 0)
        self.assertGreater(tags.get("词表", 0), 0)
        self.assertLess(tags.get("终稿吸收", 0), 20)
        self.assertGreater(tags.get("论文材料", 0), 0)
        self.assertGreater(tags.get("质检交付", 0), 0)
        self.assertLess(tags.get("项目", 0), 40)
        self.assertGreater(tags.get("项目", 0), 0)


if __name__ == "__main__":
    unittest.main()
