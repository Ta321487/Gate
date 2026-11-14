"""运营控制台阶段机 / 导航降维契约（产品化 P2 / B1 / B2）。"""

from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FE_STAGES = ROOT / "frontend" / "src" / "deliveryStages.js"
FE_OPS = ROOT / "frontend" / "src" / "opsShared.js"
FE_DETAIL = ROOT / "frontend" / "src" / "views" / "ProjectDetail.vue"
EVAL_MJS = Path(__file__).resolve().parent / "fixtures" / "delivery_stages_eval.mjs"


def _node(payload: dict):
    proc = subprocess.run(
        ["node", str(EVAL_MJS)],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        cwd=str(ROOT),
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return json.loads(proc.stdout or "null")


class DeliveryStagesContractTest(unittest.TestCase):
    def test_ops_shared_reexports_default_tab(self):
        ops = FE_OPS.read_text(encoding="utf-8")
        self.assertIn("defaultTabForStatus", ops)
        self.assertIn("deliveryStages", ops)
        # 旧默认「generated → runtime」不得残留
        self.assertNotIn("case 'running':\n      return 'runtime'", ops)

    def test_detail_stage_rail_and_tool_tab(self):
        src = FE_DETAIL.read_text(encoding="utf-8")
        self.assertIn("DeliveryStageRail", src)
        self.assertIn("MaterialsTab", src)
        self.assertIn("ArtifactsTab", src)
        self.assertIn("canEnterDetailTab", src)
        # 产品形态：阶段轨唯一主导航，不再并列一级 n-tabs
        self.assertNotIn("<n-tabs", src)
        self.assertNotIn('name="logs"', src)
        self.assertNotIn('name="overrides"', src)
        self.assertNotIn(">微调</n-button>", src)
        self.assertIn("技术标识", src)
        # 手调在论文材料轨，不在工具子切换
        tools = (FE_DETAIL.parent / "projectDetail" / "useProjectDetail.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("openThesisOverrides", tools)
        self.assertIn("thesisSurface", tools)

    def test_stage_defs_order(self):
        src = FE_STAGES.read_text(encoding="utf-8")
        for label in ("材料", "匹配", "生成", "论文材料", "答辩 PPT", "质检交付"):
            self.assertIn(label, src)
        # 预览改为轨旁，不再占主步 label 位
        self.assertNotIn("{ key: 'preview'", src)

    @unittest.skipUnless(shutil.which("node"), "需要 node")
    def test_b2_default_tab_generated_to_thesis(self):
        out = _node(
            {
                "kind": "defaultTab",
                "statuses": [
                    "needs_confirm",
                    "ready",
                    "generating",
                    "generated",
                    "running",
                    "failed",
                ],
            }
        )
        self.assertEqual(
            out,
            ["match", "generate", "generate", "thesis", "thesis", "thesis"],
        )

    @unittest.skipUnless(shutil.which("node"), "需要 node")
    def test_b1_lock_generate_before_match(self):
        out = _node(
            {
                "kind": "canEnter",
                "cases": [
                    {
                        "p": {"match_confirmed": False, "status": "needs_confirm"},
                        "tab": "generate",
                    },
                    {
                        "p": {
                            "match_confirmed": True,
                            "status": "generated",
                            "workspace_path": "/tmp/x",
                        },
                        "tab": "artifacts",
                    },
                ],
            }
        )
        self.assertFalse(out[0]["ok"])
        self.assertTrue(out[1]["ok"])

    @unittest.skipUnless(shutil.which("node"), "需要 node")
    def test_stage_states_match_then_bake(self):
        out = _node(
            {
                "kind": "stages",
                "cases": [
                    {
                        "p": {
                            "id": "1",
                            "match_confirmed": False,
                            "status": "needs_confirm",
                            "source_filename": "a.docx",
                        },
                        "activeTab": "match",
                    },
                    {
                        "p": {
                            "id": "1",
                            "match_confirmed": True,
                            "status": "generated",
                            "workspace_path": "/ws",
                        },
                        "activeTab": "artifacts",
                    },
                ],
            }
        )
        first = {s["key"]: s for s in out[0]}
        self.assertEqual(first["match"]["state"], "current")
        self.assertTrue(first["generate"]["locked"])
        self.assertTrue(first["delivery"]["locked"])
        second = {s["key"]: s for s in out[1]}
        self.assertEqual(second["match"]["state"], "done")
        self.assertEqual(second["generate"]["state"], "done")
        self.assertEqual(second["thesis"]["state"], "todo")
        self.assertEqual(second["delivery"]["state"], "current")
        self.assertFalse(second["thesis"]["locked"])

    @unittest.skipUnless(shutil.which("node"), "需要 node")
    def test_default_delivery_artifact_view(self):
        out = _node(
            {
                "kind": "artifactView",
                "projects": [
                    {"delivery_review": {"review": {"status": "active"}}},
                    {"download_blocked_reason": "质量检查未通过"},
                    {},
                ],
            }
        )
        # 论文材料主轨：二级默认「论文材料」卡
        self.assertEqual(out, ["thesis", "thesis", "thesis"])


if __name__ == "__main__":
    unittest.main()
