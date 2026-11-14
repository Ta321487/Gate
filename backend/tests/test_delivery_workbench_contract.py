"""质检交付单页契约（产品化 P3）。"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "frontend" / "src" / "views" / "projectDetail" / "ArtifactsTab.vue"
WORKBENCH = ROOT / "frontend" / "src" / "components" / "DeliveryWorkbench.vue"
DETAIL_JS = ROOT / "frontend" / "src" / "views" / "projectDetail" / "useProjectDetail.js"


class DeliveryWorkbenchContractTest(unittest.TestCase):
    def test_workbench_composes_gates_and_review(self):
        src = WORKBENCH.read_text(encoding="utf-8")
        self.assertIn("DeliveryReviewPane", src)
        self.assertIn("gateRows", src)
        self.assertIn("清洗文案", src)
        self.assertNotIn("工厂清洗文案", src)
        # 主下载只在就绪条；工作台不再并列「下载 ZIP」钮
        self.assertNotIn(">下载 ZIP<", src)
        self.assertIn("上方就绪条", src)
        self.assertIn("id=\"delivery-workbench\"", src.replace("'", '"') or src)
        self.assertIn("delivery-workbench", src)
        # 渐进披露：门禁表默认进折叠，首屏用摘要 pill
        self.assertIn("门禁与清单明细", src)
        self.assertIn("detailDefaultOpen", src)
        self.assertIn("n-collapse", src)
        pane = (ROOT / "frontend" / "src" / "components" / "DeliveryReviewPane.vue").read_text(
            encoding="utf-8"
        )
        # 失败场景合并阻断卡；门禁全文进弹层，不堆多条 n-alert、不把页撑长
        self.assertIn("hasBlockSurface", pane)
        self.assertIn("查看门禁全文", pane)
        self.assertIn("showGateDetails", pane)
        self.assertIn("n-modal", pane)
        self.assertIn("gate-full-desc", pane)
        self.assertIn("overflow-wrap: anywhere", pane)
        self.assertNotIn("pill-btn", pane)
        self.assertNotIn('title="清单已收敛，但质量门禁未过"', pane)
        self.assertNotIn('title="须重跑生成时：先结束复审"', pane)

    def test_artifacts_hosts_workbench_not_split_tabs(self):
        src = ARTIFACTS.read_text(encoding="utf-8")
        self.assertIn("DeliveryWorkbench", src)
        self.assertNotIn('name="review"', src)
        self.assertNotIn('name="gates"', src)
        self.assertIn("pane === 'delivery'", src)
        self.assertIn("论文材料", src)
        # 产物排障块已删：ZIP=就绪条；配置=匹配；拆解=生成；路径=页头技术标识
        self.assertNotIn("更多 · 产物文件", src)
        self.assertNotIn("更多 · 对照材料", src)

    def test_go_artifacts_maps_legacy_gates_review(self):
        src = DETAIL_JS.read_text(encoding="utf-8")
        self.assertIn("v === 'gates' || v === 'review' || v === 'delivery'", src)
        self.assertIn("delivery-workbench", src)


if __name__ == "__main__":
    unittest.main()
