"""语义门禁 p3s 静态扫描。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.bake.gates.semantic import evaluate_semantic_gates


class SemanticGateTests(unittest.TestCase):
    def _workspace(self, tmp: str) -> Path:
        ws = Path(tmp) / "ws"
        (ws / "frontend" / "src" / "views").mkdir(parents=True)
        (ws / "backend" / "src" / "main" / "resources").mkdir(parents=True)
        return ws

    def test_demo_wording_fails(self):
        with tempfile.TemporaryDirectory() as td:
            ws = self._workspace(td)
            (ws / "frontend" / "src" / "views" / "Home.vue").write_text(
                "<template><span>演示数据</span></template>",
                encoding="utf-8",
            )
            spec = {"schema": {"scene": "campus"}}
            res = evaluate_semantic_gates(ws, spec)
            self.assertFalse(res["p3s"]["ok"])
            self.assertIn("演示", res["p3s"]["desc"])

    def test_clean_student_view_passes(self):
        with tempfile.TemporaryDirectory() as td:
            ws = self._workspace(td)
            (ws / "frontend" / "src" / "views" / "Home.vue").write_text(
                "<template><span>图书检索</span></template>",
                encoding="utf-8",
            )
            (ws / "backend" / "src" / "main" / "resources" / "profile-fields.json").write_text(
                '{"fields":[{"label":"学号"}]}',
                encoding="utf-8",
            )
            spec = {"schema": {"scene": "campus"}}
            res = evaluate_semantic_gates(ws, spec)
            self.assertTrue(res["p3s"]["ok"])

    def test_enterprise_scene_profile_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            ws = self._workspace(td)
            (ws / "backend" / "src" / "main" / "resources" / "profile-fields.json").write_text(
                '{"fields":[{"label":"学号"},{"label":"学院"}]}',
                encoding="utf-8",
            )
            spec = {"schema": {"scene": "enterprise"}}
            res = evaluate_semantic_gates(ws, spec)
            self.assertFalse(res["p3s"]["ok"])
            detail = res["p3s"]["detail"]
            self.assertTrue(detail.get("profile_issues"))


if __name__ == "__main__":
    unittest.main()
