"""运营控制台等待态契约（产品化 I2 + 短加载统一）。

钉：验收长任务有阶段提示与刷新可恢复；短加载走 ContentLoading。
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend" / "src"
PANE = FE / "components" / "DeliveryReviewPane.vue"
LONG_OP = FE / "components" / "LongOpWait.vue"
SESSION = FE / "utils" / "longOpSession.js"
HELP = FE / "views" / "Help.vue"
PROJECTS = FE / "views" / "Projects.vue"
JOBS = FE / "views" / "Jobs.vue"
RUNTIME = FE / "views" / "projectDetail" / "RuntimeTab.vue"
ARTIFACTS = FE / "views" / "projectDetail" / "ArtifactsTab.vue"
MATURITY = ROOT / "docs" / "product-form-maturity.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# 等待态禁「教人怎么盯页面」腔（两人用 · 自然产品句）
TUTOR_WAIT_FORBIDDEN = (
    "可离开本页",
    "回来后会自动",
    "回来看进度",
    "勿重复点",
    "勿重复点击",
    "可停在本页",
    "状态会自动刷新",
    "超时请刷新对齐",
    "你可以先",
    "不要指望再点一次",
    "按右侧主操作即可",
    "不会当成正式订单",
    "方便核对",
)


class ConsoleWaitStateContractTest(unittest.TestCase):
    def test_long_op_wait_component_exists(self):
        src = _read(LONG_OP)
        self.assertIn("仍在运行", src)
        self.assertIn("elapsedLabel", src)
        self.assertIn("phases", src)

    def test_wait_copy_not_tutorial(self):
        paths = [
            LONG_OP,
            PANE,
            ARTIFACTS,
            RUNTIME,
            FE / "views" / "projectDetail" / "pdRuntimeFmt.js",
            FE / "utils" / "uploadJobUi.js",
            FE / "views" / "ThesisAbsorb.vue",
            FE / "deliveryReadiness.js",
            FE / "deliveryStages.js",
            FE / "views" / "Projects.vue",
            FE / "views" / "projectDetail" / "GenerateTab.vue",
            FE / "views" / "projectDetail" / "MatchTab.vue",
            FE / "components" / "DeliveryReadinessBar.vue",
        ]
        for path in paths:
            src = _read(path)
            for bad in TUTOR_WAIT_FORBIDDEN:
                self.assertNotIn(bad, src, f"{path.name} 含教人腔「{bad}」")

    def test_long_op_session_mark_peek_clear(self):
        src = _read(SESSION)
        self.assertIn("export function markLongOp", src)
        self.assertIn("export function peekLongOp", src)
        self.assertIn("export function clearLongOp", src)
        self.assertIn("gf-long-op:", src)

    def test_delivery_review_verify_has_phases_and_recover(self):
        pane = _read(PANE)
        self.assertIn("LongOpWait", pane)
        self.assertIn("正在验收", pane)
        self.assertIn("peekLongOp", pane)
        self.assertIn("markLongOp", pane)
        self.assertIn("recoverAlign", pane)
        self.assertIn("立即对齐状态", pane)
        self.assertIn("keepSession", pane)
        # 超时保留会话，成功则 clear
        self.assertIn("clearLongOp(props.projectId)", pane)

    def test_runtime_and_thesis_use_long_op_wait(self):
        rt = _read(RUNTIME)
        self.assertIn("LongOpWait", rt)
        self.assertIn("启停进行中", rt)
        self.assertIn("rtSettling", rt)
        art = _read(ARTIFACTS)
        self.assertIn("LongOpWait", art)
        self.assertIn("正在对账论文图", art)
        thesis = _read(FE / "views" / "ThesisAbsorb.vue")
        self.assertIn("LongOpWait", thesis)
        self.assertIn("正在抽取", thesis)
        self.assertIn("detailExtractStartedAt", thesis)
        # 长抽取禁止 ContentLoading 冒充（短拉数仍可用 ContentLoading）
        self.assertNotRegex(
            thesis,
            r"detail\.status\s*===\s*'extracting'[\s\S]{0,200}ContentLoading",
        )

    def test_short_loads_use_content_loading(self):
        help_src = _read(HELP)
        self.assertIn("ContentLoading", help_src)
        self.assertIn("正在加载对照表", help_src)
        self.assertNotIn("正在加载对照表…</p>", help_src)
        projects = _read(PROJECTS)
        self.assertIn("ContentLoading", projects)
        self.assertIn("正在解析并分堆", projects)
        jobs = _read(JOBS)
        self.assertIn("ContentLoading", jobs)
        self.assertNotIn("<n-spin", jobs)

    def test_maturity_i2_checked(self):
        md = _read(MATURITY)
        self.assertRegex(
            md,
            r"\|\s*I2\s*\|\s*验圈进度\s*\|\s*✅",
        )


if __name__ == "__main__":
    unittest.main()
