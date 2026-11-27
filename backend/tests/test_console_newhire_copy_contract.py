"""第一次用上手 · 主路径文案契约（两人用 · 自然产品句）。

禁作坊绰号当主路径可见句；不硬钉「履约」类大词。
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend" / "src"

# 主路径可见面（模板字符串）；注释 / script 变量名不在此扫全文件时用 strip
MAIN_PATH_FILES = [
    FE / "views" / "OpsHome.vue",
    FE / "views" / "Projects.vue",
    FE / "views" / "projectDetail" / "MatchTab.vue",
    FE / "views" / "projectDetail" / "GenerateTab.vue",
    FE / "components" / "DeliveryWorkbench.vue",
    FE / "components" / "DeliveryReadinessBar.vue",
    FE / "deliveryReadiness.js",
]

# 主路径禁用（作坊腔 / 假大厂腔）；Help 术语表与折叠区另册
FORBIDDEN_MAIN = [
    "合卷",
    "验圈",
    "填岛",
    "工厂清洗文案",
    "本岗可处理",
    "请升级工程",
    "工单流转",
    "SLA",
    # 教人盯页面 / 教人操作腔
    "可离开本页",
    "勿重复点",
    "回来看进度",
    "你可以先",
    "不要指望再点一次",
    "按右侧主操作即可",
]


def _template_chunks(src: str) -> str:
    """粗取 <template>...</template>，无则整文件（.js）。"""
    m = re.search(r"<template>([\s\S]*?)</template>", src)
    return m.group(1) if m else src


class ConsoleNewhireCopyContractTest(unittest.TestCase):
    def test_main_path_forbids_workshop_and_fake_enterprise(self):
        for path in MAIN_PATH_FILES:
            self.assertTrue(path.is_file(), path)
            chunk = _template_chunks(path.read_text(encoding="utf-8"))
            # deliveryReadiness.js 可读「合卷」作 reason 兼容匹配，不算 UI 按钮文案
            if path.name == "deliveryReadiness.js":
                for bad in (
                    "填岛",
                    "工厂清洗文案",
                    "本岗可处理",
                    "请升级工程",
                    "工单流转",
                    "你可以先",
                    "不要指望再点一次",
                    "不要假装再下载就能过",
                ):
                    self.assertNotIn(bad, chunk, f"{path.name} 含禁用词 {bad}")
                self.assertIn("需要改程序", chunk)
                self.assertIn("清洗文案", chunk)
                self.assertIn("从失败步骤重试", chunk)
                continue
            for bad in FORBIDDEN_MAIN:
                self.assertNotIn(bad, chunk, f"{path.name} 主路径含禁用词 {bad}")

    def test_scrub_button_plain_label(self):
        wb = (FE / "components" / "DeliveryWorkbench.vue").read_text(encoding="utf-8")
        pane = (FE / "components" / "DeliveryReviewPane.vue").read_text(encoding="utf-8")
        self.assertIn("清洗文案", wb)
        self.assertNotIn("工厂清洗文案", _template_chunks(wb))
        self.assertIn("清洗文案", pane)
        self.assertNotIn("工厂清洗文案", _template_chunks(pane))

    def test_ops_empty_cta_and_help_anchors(self):
        ops = (FE / "views" / "OpsHome.vue").read_text(encoding="utf-8")
        self.assertIn("去项目建项", ops)
        self.assertIn("第一次怎么出单", ops)
        help_src = (FE / "views" / "Help.vue").read_text(encoding="utf-8")
        self.assertIn("anchor: '本机怎么启动'", help_src)
        self.assertIn("anchor: '第一次怎么出单'", help_src)

    def test_match_checklist_present(self):
        src = (FE / "views" / "projectDetail" / "MatchTab.vue").read_text(encoding="utf-8")
        self.assertIn("确认前快速核对", src)
        self.assertIn("我已看过用法", src)
        self.assertIn("我已对照开题看过业务类型", src)

    def test_projects_first_run_hint(self):
        src = (FE / "views" / "Projects.vue").read_text(encoding="utf-8")
        self.assertIn("生成测试开题", src)
        self.assertIn("第一次", src)

    def test_launcher_has_env_doctor(self):
        launcher = (ROOT / "scripts" / "launcher.ps1").read_text(encoding="utf-8")
        self.assertIn("function Show-EnvDoctor", launcher)
        self.assertIn('"N"', launcher)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("第一次用", readme)
        self.assertIn("拉仓开工", readme)
        self.assertIn("环境检查", readme)


if __name__ == "__main__":
    unittest.main()
