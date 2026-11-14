"""运营控制台交付就绪指示契约（产品化 P1 / P7 / A5 / A6）。"""

from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FE_READY = ROOT / "frontend" / "src" / "deliveryReadiness.js"
FE_OPS = ROOT / "frontend" / "src" / "opsShared.js"
FE_BAR = ROOT / "frontend" / "src" / "components" / "DeliveryReadinessBar.vue"
FE_DETAIL = ROOT / "frontend" / "src" / "views" / "ProjectDetail.vue"
EVAL_MJS = Path(__file__).resolve().parent / "fixtures" / "delivery_readiness_eval.mjs"


class DeliveryReadinessContractTest(unittest.TestCase):
    def test_downloadable_rule_matches_ops_shared(self):
        ready = FE_READY.read_text(encoding="utf-8")
        ops = FE_OPS.read_text(encoding="utf-8")
        # 同一口径：有 download_blocked_reason 则以其空否为准，否则 zip_ready
        self.assertIn("if ('download_blocked_reason' in row)", ready)
        self.assertIn("return !row.download_blocked_reason", ready)
        self.assertIn("return !!row.zip_ready", ready)
        self.assertIn("if ('download_blocked_reason' in row)", ops)
        self.assertIn("return !row.download_blocked_reason", ops)

    def test_detail_hosts_readiness_bar(self):
        src = FE_DETAIL.read_text(encoding="utf-8")
        self.assertIn("DeliveryReadinessBar", src)
        self.assertIn('@review="goArtifacts(\'delivery\')"', src)
        self.assertIn("@download=\"downloadZip\"", src)
        # 页头不再并列 primary 下载（主操作进就绪条）
        self.assertNotIn("下载并发出</n-button>", src)

    def test_bar_shows_at_most_three_blockers_template(self):
        src = FE_BAR.read_text(encoding="utf-8")
        self.assertIn("ready.blockers", src)
        self.assertIn("downloadImpact", src)
        self.assertIn("ready.primary.label", src)

    def test_bar_demotes_download_off_artifacts_tab(self):
        src = FE_BAR.read_text(encoding="utf-8")
        self.assertIn("activeTab", src)
        self.assertIn("demoteDownloadOnTab", src)
        detail = FE_DETAIL.read_text(encoding="utf-8")
        self.assertIn(':active-tab="tab"', detail)

    def test_bar_hides_same_stage_nav_primary(self):
        src = FE_BAR.read_text(encoding="utf-8")
        self.assertIn("sameStageAsPrimary", src)
        self.assertIn("请在下方确认匹配", src)
        self.assertIn("请在下方一键生成", src)

    def test_builder_caps_blockers_at_three(self):
        src = FE_READY.read_text(encoding="utf-8")
        self.assertIn("blockers.length >= 3", src)

    def test_recovery_hint_split_self_vs_code(self):
        src = FE_READY.read_text(encoding="utf-8")
        self.assertIn("recoveryHint", src)
        self.assertIn("你可以先", src)
        self.assertIn("需要改程序", src)
        self.assertIn("label: '清洗文案'", src)
        bar = FE_BAR.read_text(encoding="utf-8")
        self.assertIn("ready.recoveryHint", bar)

    @unittest.skipUnless(shutil.which("node"), "需要 node")
    def test_node_phase_matrix(self):
        cases = [
            {
                "status": "needs_confirm",
                "match_confirmed": False,
                "download_blocked_reason": "质量检查未通过 · 暂不可下载交付包",
            },
            {
                "status": "generating",
                "match_confirmed": True,
                "download_blocked_reason": "生成中 · 请等待打包完成后再下载",
            },
            {
                "status": "generated",
                "match_confirmed": True,
                "download_blocked_reason": "工程已变更 · 请完成验收并重新打包后再下载",
                "delivery_review": {"zip_stale": True, "review": {"status": "active"}},
            },
            {
                "status": "generated",
                "match_confirmed": True,
                "download_blocked_reason": None,
                "zip_ready": True,
                "delivery_mark": "ready",
            },
            {
                "status": "generated",
                "match_confirmed": True,
                "download_blocked_reason": "质量检查未通过 · 暂不可下载交付包",
                "gates": {"p3copy": {"ok": False, "desc": "工厂腔"}},
                "delivery_review": {"blocking_gates": [{"label": "文案"}, {"label": "语义"}, {"label": "精简"}, {"label": "多余"}]},
            },
        ]
        proc = subprocess.run(
            ["node", str(EVAL_MJS)],
            input=json.dumps(cases, ensure_ascii=False),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            cwd=str(ROOT),
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        out = json.loads(proc.stdout or "[]")
        self.assertEqual(len(out), 5)
        self.assertEqual(out[0]["phase"], "match")
        self.assertEqual(out[0]["primaryKey"], "match")
        self.assertFalse(out[0]["canDownload"])
        self.assertEqual(out[1]["phase"], "generating")
        self.assertEqual(out[2]["phase"], "repack")
        self.assertEqual(out[2]["primaryKey"], "review")
        self.assertEqual(out[3]["phase"], "download")
        self.assertEqual(out[3]["primaryKey"], "downloadDeliver")
        self.assertTrue(out[3]["canDownload"])
        self.assertEqual(out[4]["phase"], "scrub")
        self.assertLessEqual(out[4]["blockerCount"], 3)


if __name__ == "__main__":
    unittest.main()
