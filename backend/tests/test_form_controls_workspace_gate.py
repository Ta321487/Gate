"""出包侧控件闸 p3controls：对本包 frontend 跑 C1～C3 契约。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.bake.gates.form_controls_workspace import (
    evaluate_workspace_form_controls_gate,
)
from app.bake.gates.keys import GATE_MONOTONE_KEYS

_REPO = Path(__file__).resolve().parents[2]


class FormControlsWorkspaceGateTests(unittest.TestCase):
    def test_gate_key_registered(self) -> None:
        self.assertIn("p3controls", GATE_MONOTONE_KEYS)

    def test_missing_frontend_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws"
            ws.mkdir()
            res = evaluate_workspace_form_controls_gate(ws)
            self.assertFalse(res["ok"])
            self.assertIn("frontend/src", res["desc"])

    def test_baseline_as_workspace_passes(self) -> None:
        baseline = _REPO / "skeletons" / "baseline"
        self.assertTrue((baseline / "frontend" / "src").is_dir())
        res = evaluate_workspace_form_controls_gate(baseline)
        self.assertTrue(res["ok"], res.get("desc"))

    def test_new_allow_create_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws"
            src = ws / "frontend" / "src"
            (src / "views").mkdir(parents=True)
            (src / "layouts").mkdir()
            (src / "components").mkdir()
            (src / "views" / "BadSelect.vue").write_text(
                """
<template>
  <el-select v-model="form.category" allow-create filterable>
    <el-option label="A" value="A" />
  </el-select>
</template>
""",
                encoding="utf-8",
            )
            res = evaluate_workspace_form_controls_gate(ws)
            self.assertFalse(res["ok"], res.get("desc"))
            self.assertIn("控件", res["desc"])


if __name__ == "__main__":
    unittest.main()
