"""出包侧布局闸 p3layout：对本包 frontend 对账+结构。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.bake.gates.layout_workspace import evaluate_workspace_layout_gate


_REPO = Path(__file__).resolve().parents[2]


class LayoutWorkspaceGateTests(unittest.TestCase):
    def test_missing_frontend_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws"
            ws.mkdir()
            res = evaluate_workspace_layout_gate(ws)
            self.assertFalse(res["ok"])
            self.assertIn("frontend/src", res["desc"])

    def test_baseline_as_workspace_passes(self) -> None:
        """共享基线目录布局即 skeletons/baseline（含 frontend/src）。"""
        baseline = _REPO / "skeletons" / "baseline"
        self.assertTrue((baseline / "frontend" / "src").is_dir())
        res = evaluate_workspace_layout_gate(baseline)
        self.assertTrue(res["ok"], res.get("desc"))

    def test_absolute_primary_cta_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws"
            src = ws / "frontend" / "src"
            (src / "views").mkdir(parents=True)
            (src / "layouts").mkdir()
            (src / "components").mkdir()
            (src / "router").mkdir()
            (src / "router" / "index.js").write_text(
                "export default { routes: [] }\n",
                encoding="utf-8",
            )
            (src / "views" / "Broken.vue").write_text(
                """
<template>
  <el-button type="primary" style="position:absolute;top:0;right:0">提交</el-button>
</template>
""",
                encoding="utf-8",
            )
            res = evaluate_workspace_layout_gate(ws)
            self.assertFalse(res["ok"], res.get("desc"))
            self.assertTrue(
                "结构" in res["desc"] or "台账" in res["desc"] or "unrouted" in res["desc"].lower()
                or "契约" in res["desc"]
                or "对账" in res["desc"],
                res.get("desc"),
            )


if __name__ == "__main__":
    unittest.main()
