"""整厂产品形态契约（§2.4.5）：详情阶段轨唯一导航；配置页标明非履约；列表下载非抢色 primary。"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend" / "src"


class ConsoleProductFormContractTest(unittest.TestCase):
    def test_detail_no_line_tabs_stage_rail_only(self):
        src = (FE / "views" / "ProjectDetail.vue").read_text(encoding="utf-8")
        self.assertIn("DeliveryStageRail", src)
        self.assertIn("MaterialsTab", src)
        self.assertNotIn("<n-tabs", src)
        self.assertIn("技术标识", src)

    def test_delivery_no_artifact_dump_wall(self):
        src = (FE / "views" / "projectDetail" / "ArtifactsTab.vue").read_text(encoding="utf-8")
        # 质检交付不再挂「更多 · 产物」排障墙
        self.assertNotIn("更多 · 产物文件", src)
        self.assertNotIn("更多 · 对照材料", src)
        self.assertIn("pane === 'delivery'", src)
        self.assertIn("pane: { type: String, default: 'delivery' }", src)
        detail = (FE / "views" / "ProjectDetail.vue").read_text(encoding="utf-8")
        self.assertIn("workspace_path", detail)
        self.assertIn("复制工程目录", detail)
        self.assertIn('pane="thesis"', detail)
        self.assertIn("PptTab", detail)
        rail = (FE / "components" / "DeliveryStageRail.vue").read_text(encoding="utf-8")
        self.assertIn("预览", rail)
        self.assertIn(">日志</button>", rail)
        self.assertNotIn(">工具</button>", rail)
        # 出包手调挂在论文材料，不进轨旁日志
        detail_full = (FE / "views" / "ProjectDetail.vue").read_text(encoding="utf-8")
        self.assertNotIn(">微调</n-button>", detail_full)
        self.assertNotIn("OverridesTab", detail_full)
        thesis = (FE / "views" / "projectDetail" / "ArtifactsTab.vue").read_text(encoding="utf-8")
        self.assertIn("OverridesTab", thesis)
        self.assertIn("openThesisOverrides", thesis)
        self.assertIn("手调文字", thesis)
        self.assertGreaterEqual(thesis.count("overrideSection:"), 8)

    def test_ops_home_no_fix_locus_wall(self):
        src = (FE / "views" / "OpsHome.vue").read_text(encoding="utf-8")
        self.assertNotIn("ops-row-sub mono\">{{ p.fix_locus }}", src)
        self.assertIn("点开失败分析查看相关位置", src)

    def test_config_pages_marked_non_fulfillment(self):
        for rel, needle in (
            ("views/Llm.vue", "非履约主路径"),
            ("views/Unsplash.vue", "非履约主路径"),
            ("views/System.vue", "非履约主路径"),
        ):
            src = (FE / rel).read_text(encoding="utf-8")
            self.assertIn(needle, src, rel)

    def test_projects_row_download_not_primary(self):
        src = (FE / "views" / "Projects.vue").read_text(encoding="utf-8")
        # 行内下载须 secondary，避免与建项主 CTA 抢 primary
        marker = "onClick: (e) => { e.stopPropagation(); downloadRowZip(row) }"
        self.assertIn(marker, src)
        idx = src.find(marker)
        window = src[max(0, idx - 120) : idx]
        self.assertIn("secondary: true", window)

    def test_projects_arch_human_label_not_raw_codes(self):
        src = (FE / "views" / "Projects.vue").read_text(encoding="utf-8")
        self.assertIn("formatArchDomParts", src)
        self.assertIn("arch-id-hint", src)
        ops = (FE / "opsShared.js").read_text(encoding="utf-8")
        self.assertIn("hit?.name || hit?.label", ops)
        self.assertIn("formatArchDomParts", ops)


if __name__ == "__main__":
    unittest.main()
