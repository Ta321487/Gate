"""第 6 步诊断小卡契约（delivery-diagnosis-orchestration D1）。"""

from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FE_DIAG = ROOT / "frontend" / "src" / "deliveryDiagnosis.js"
PANE = ROOT / "frontend" / "src" / "components" / "DeliveryReviewPane.vue"
GEN = ROOT / "frontend" / "src" / "views" / "projectDetail" / "GenerateTab.vue"
READY = ROOT / "frontend" / "src" / "deliveryReadiness.js"
DOC = ROOT / "docs" / "delivery-diagnosis-orchestration.md"


class DeliveryDiagnosisContractTest(unittest.TestCase):
    def test_builder_and_pane_host_step6_only(self):
        diag = FE_DIAG.read_text(encoding="utf-8")
        self.assertIn("buildDeliveryDiagnosis", diag)
        self.assertIn("下载是结果不是病因", diag)
        # 总判拼接不得以「暂不可下载」起句
        self.assertNotIn('verdict = "暂不可下载', diag)
        self.assertNotIn("verdict: '暂不可下载", diag)
        self.assertNotIn("verdict = '暂不可下载", diag)

        pane = PANE.read_text(encoding="utf-8")
        self.assertIn("buildDeliveryDiagnosis", pane)
        self.assertIn('data-testid="delivery-diagnosis"', pane)
        self.assertIn("diag-card", pane)
        self.assertIn("delivery-qa-block", pane)
        self.assertIn("failAnalysisHref", pane)
        # 深浅色跟全局 token
        self.assertIn("--banner-warn-bg", pane)
        self.assertIn("--banner-fail-bg", pane)
        self.assertIn("var(--surface)", pane)
        self.assertIn("var(--teal)", pane)
        self.assertNotIn("background: #fff;", pane)
        self.assertNotIn("rgba(180, 120, 32", pane)
        # 旧阻断墙已替换
        self.assertNotIn("hasBlockSurface", pane)
        self.assertNotIn("block-panel", pane)
        self.assertNotIn("质量门禁未过 · 暂不可下载", pane)
        # 卡内仅一枚 type=primary（下一步）
        self.assertEqual(pane.count('type="primary"'), 1)

        gen = GEN.read_text(encoding="utf-8")
        self.assertNotIn("buildDeliveryDiagnosis", gen)
        self.assertNotIn("diag-card", gen)

        ready = READY.read_text(encoding="utf-8")
        self.assertIn("去质检交付", ready)
        self.assertNotIn("title: gateFail ? '门禁未过' : '暂不可下载'", ready)

        self.assertTrue(DOC.is_file())
        self.assertIn("家在第六步", DOC.read_text(encoding="utf-8"))

    @unittest.skipUnless(shutil.which("node"), "需要 node")
    def test_node_diagnosis_matrix(self):
        eval_js = ROOT / "backend" / "tests" / "fixtures" / "delivery_diagnosis_eval.mjs"
        self.assertTrue(eval_js.is_file(), eval_js)
        proc = subprocess.run(
            ["node", str(eval_js)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(ROOT),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        data = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertTrue(data.get("ok"))
        self.assertGreaterEqual(int(data.get("tideLayers") or 0), 3)


if __name__ == "__main__":
    unittest.main()
