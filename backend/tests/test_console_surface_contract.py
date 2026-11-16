"""运营台构图层契约（收卡片墙 · console-product-surface）：开工台主区 / 详情壳标记。"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend" / "src"


class ConsoleSurfaceContractTest(unittest.TestCase):
    def test_ops_home_today_main_no_stat_card_wall(self):
        src = (FE / "views" / "OpsHome.vue").read_text(encoding="utf-8")
        self.assertIn("今日要处理", src)
        self.assertIn("surface-strip", src)
        self.assertIn("surface-main", src)
        self.assertIn("surface-tray", src)
        self.assertIn("surface-env-line", src)
        # 六格 stats 卡墙已收；勿回退
        self.assertNotIn('class="stats ops-stats', src)
        self.assertNotIn("环境与额度", src)

    def test_detail_shell_surface_marker(self):
        src = (FE / "views" / "ProjectDetail.vue").read_text(encoding="utf-8")
        self.assertIn('class="surface-detail"', src)
        self.assertIn("detail-stage-body", src)

    def test_artifacts_no_duplicate_panel_title(self):
        src = (FE / "views" / "projectDetail" / "ArtifactsTab.vue").read_text(encoding="utf-8")
        self.assertIn("DeliveryWorkbench", src)
        # 阶段轨已点名，禁止再套「质检交付」panel 头
        self.assertNotIn("<h3>质检交付</h3>", src)

    def test_global_surface_utilities(self):
        css = (FE / "styles.css").read_text(encoding="utf-8")
        self.assertIn(".surface-strip", css)
        self.assertIn(".surface-main", css)
        self.assertIn(".surface-tray", css)
        self.assertIn(".surface-toolbar", css)
        self.assertIn(".panel-quiet", css)
        self.assertIn(".surface-detail .detail-stage-body", css)
        # 全局 panel 扁平：头栏不再厚底 surface-2 墙
        self.assertIn("border-radius: 4px", css)

    def test_projects_list_tray(self):
        src = (FE / "views" / "Projects.vue").read_text(encoding="utf-8")
        self.assertIn("surface-tray", src)
        self.assertIn("projects-list-tray", src)
        self.assertIn("surface-toolbar", src)

    def test_jobs_toolbar_tray(self):
        src = (FE / "views" / "Jobs.vue").read_text(encoding="utf-8")
        self.assertIn("surface-toolbar", src)
        self.assertIn("jobs-tray", src)
        self.assertNotIn("<h3>任务列表</h3>", src)

    def test_detail_tabs_quiet_panels(self):
        materials = (FE / "views" / "projectDetail" / "MaterialsTab.vue").read_text(encoding="utf-8")
        self.assertIn("surface-main-hd", materials)
        self.assertNotIn('class="materials-pane panel"', materials)
        match = (FE / "views" / "projectDetail" / "MatchTab.vue").read_text(encoding="utf-8")
        self.assertIn("panel-quiet", match)
        gen = (FE / "views" / "projectDetail" / "GenerateTab.vue").read_text(encoding="utf-8")
        self.assertIn("panel-quiet", gen)
        runtime = (FE / "views" / "projectDetail" / "RuntimeTab.vue").read_text(encoding="utf-8")
        self.assertIn("panel-quiet", runtime)

    def test_workbench_no_nested_panel_chrome(self):
        src = (FE / "components" / "DeliveryWorkbench.vue").read_text(encoding="utf-8")
        self.assertIn("workbench-gates", src)
        self.assertNotIn('class="workbench-gates panel"', src)
        self.assertNotIn("border-radius:8px", src)

    def test_system_paths_advanced_fold(self):
        src = (FE / "views" / "System.vue").read_text(encoding="utf-8")
        self.assertIn("高级：路径 / 库", src)
        self.assertIn("sys-advanced", src)

    def test_help_surface_page(self):
        src = (FE / "views" / "Help.vue").read_text(encoding="utf-8")
        self.assertIn("surface-page", src)

    def test_zh_lexicon_stripe_structure(self):
        """配置/字典列表页 §3.5：工具条 + stats + tabs + panel 表 + 右抽屉 + 分页。"""
        src = (FE / "views" / "ZhLexicon.vue").read_text(encoding="utf-8")
        self.assertIn("surface-toolbar", src)
        self.assertIn('class="stats', src)
        self.assertIn('type="line"', src)
        self.assertIn("panel-quiet", src)
        self.assertIn("n-drawer", src)
        self.assertIn("pager-row", src)
        self.assertIn("empty-title", src)
        self.assertIn("退出编辑", src)
        self.assertIn("ZH_MAX_LEN", src)
        self.assertIn("zhDupWarn", src)
        self.assertIn("show-count", src)
        self.assertIn("domainSelectLabel", src)
        self.assertNotIn("仅全局", src)
        self.assertNotIn("按域筛选", src)
        # 数字条只展示；切视图只走 n-tabs（禁 stats 双切）
        self.assertNotIn('role="button"', src)
        self.assertNotIn("<h3>词条列表</h3>", src)
        self.assertNotIn("<h3>待补中文</h3>", src)

    def test_ops_accent_presets(self):
        theme = (FE / "theme.js").read_text(encoding="utf-8")
        app = (FE / "App.vue").read_text(encoding="utf-8")
        self.assertIn("ACCENT_PRESETS", theme)
        self.assertIn("gf-ops-accent", theme)
        self.assertIn("id: 'harbor'", theme)
        self.assertIn("id: 'berry'", theme)
        self.assertIn("applyAccent", theme)
        self.assertIn("accent-swatches", app)
        self.assertIn("applyAccent", app)


if __name__ == "__main__":
    unittest.main()
