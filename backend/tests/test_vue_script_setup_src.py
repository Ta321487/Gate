"""拆分页 <script setup src> 须随学生包 Vite 垫片出厂，禁止只冒烟有、出包无。"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE_FE = ROOT / "skeletons" / "baseline" / "frontend"


class VueScriptSetupSrcPluginTests(unittest.TestCase):
    def test_baseline_ships_plugin_and_wires_vite(self) -> None:
        plugin = BASE_FE / "vue-script-setup-src.js"
        vite = BASE_FE / "vite.config.js"
        self.assertTrue(plugin.is_file(), plugin)
        self.assertTrue(vite.is_file(), vite)
        plugin_txt = plugin.read_text(encoding="utf-8")
        self.assertIn("addWatchFile", plugin_txt, "改 .setup.js 须触发 .vue 重编")
        vite_txt = vite.read_text(encoding="utf-8")
        self.assertIn("vue-script-setup-src", vite_txt)
        self.assertIn("vueScriptSetupSrc()", vite_txt)
        # 插件数组里垫片须在 vue() 之前（勿误匹配 import vue）
        import re

        m = re.search(r"plugins\s*:\s*\[([^\]]+)\]", vite_txt)
        self.assertTrue(m, "vite.config 缺 plugins 数组")
        plugins = m.group(1)
        self.assertIn("vueScriptSetupSrc()", plugins)
        self.assertIn("vue()", plugins)
        self.assertLess(
            plugins.index("vueScriptSetupSrc()"),
            plugins.index("vue()"),
            "垫片须在 @vitejs/plugin-vue 之前",
        )

    def test_split_pages_still_use_setup_src(self) -> None:
        """范式未改时垫片不可删；Profile 为探针。"""
        profile = (BASE_FE / "src" / "views" / "Profile.vue").read_text(encoding="utf-8")
        self.assertIn('<script setup src="./Profile.setup.js"></script>', profile)
        self.assertTrue((BASE_FE / "src" / "views" / "Profile.setup.js").is_file())


if __name__ == "__main__":
    unittest.main()
