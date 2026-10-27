# -*- coding: utf-8 -*-
"""钉住列表卡主信号：骨架禁止「作者 · 未分类」同构灰墙。"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BROWSE = (
    ROOT
    / "skeletons"
    / "baseline"
    / "frontend"
    / "src"
    / "views"
    / "user"
    / "ArchiveBrowse.vue"
)
BROWSE_SETUP = (
    ROOT
    / "skeletons"
    / "baseline"
    / "frontend"
    / "src"
    / "views"
    / "user"
    / "ArchiveBrowse.setup.js"
)
HOME = (
    ROOT
    / "skeletons"
    / "baseline"
    / "frontend"
    / "src"
    / "views"
    / "user"
    / "PortalHome.vue"
)
MAIN = ROOT / "skeletons" / "baseline" / "frontend" / "src" / "main.js"
SHELL = ROOT / "backend" / "app" / "bake" / "shell_face.py"
CHROME = ROOT / "skeletons" / "baseline" / "frontend" / "src" / "styles" / "chrome.css"


class ArchiveCardSignalTests(unittest.TestCase):
    def test_browse_uses_primary_signal_helper(self) -> None:
        # 拆分后函数在 setup，模板只调用
        vue = BROWSE.read_text(encoding="utf-8")
        setup = BROWSE_SETUP.read_text(encoding="utf-8")
        self.assertIn("function primarySignalOf", setup)
        self.assertIn("primarySignalOf(row)", vue)
        self.assertIn("cover-fallback", vue)
        self.assertNotIn(
            "formatAuthor(row.author) }} ·",
            vue,
            "主信号不得再拼「作者 · 分类」同构墙",
        )

    def test_cards_home_not_function_grid(self) -> None:
        text = HOME.read_text(encoding="utf-8")
        self.assertIn("cards-hero", text)
        self.assertIn("cards-rail", text)
        self.assertNotIn('aria-label="功能入口"', text)

    def test_main_applies_shell_cover(self) -> None:
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("cover: '--portal-cover'", text)
        self.assertIn("--portal-bg-glow", text)
        # 行业配色整轴：壳色不得盖 bg/surface/ink（浅色/夜间/影院一视同仁）
        self.assertIn("禁止再用壳色的浅 bg/surface/ink", text)
        self.assertNotIn("bg: '--portal-bg'", text)
        self.assertNotIn("surface: '--portal-surface'", text)
        self.assertNotIn("ink: '--portal-ink'", text)
        self.assertIn("brand: '--portal-brand'", text)
        self.assertIn("accent: '--portal-accent'", text)

    def test_shell_face_emits_cover(self) -> None:
        text = SHELL.read_text(encoding="utf-8")
        self.assertIn('"cover"', text)
        self.assertIn('"glow"', text)

    def test_chrome_kills_autofill_inner_box(self) -> None:
        text = CHROME.read_text(encoding="utf-8")
        self.assertIn(":-webkit-autofill", text)
        self.assertIn("1000px", text)
        self.assertIn(":has(input:-webkit-autofill)", text)


if __name__ == "__main__":
    unittest.main()
