"""运营台只读代码预览：共享 CodePreview，SQL/JSON 轻量高亮。"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend" / "src"


class TestCodePreviewContract(unittest.TestCase):
    def test_shared_highlighter_and_component(self):
        hl = (FE / "codeHighlight.js").read_text(encoding="utf-8")
        self.assertIn("export function highlightCode", hl)
        self.assertIn("highlightSql", hl)
        self.assertIn("highlightJson", hl)
        self.assertIn("escapeHtml", hl)
        # 禁引入重型 IDE
        self.assertNotIn("monaco", hl.lower())
        self.assertNotIn("codemirror", hl.lower())
        self.assertNotIn("highlight.js", hl.lower())
        self.assertNotIn("prism", hl.lower())

        comp = (FE / "components" / "CodePreview.vue").read_text(encoding="utf-8")
        self.assertIn("highlightCode", comp)
        self.assertIn('class="spec-preview code-preview"', comp)
        self.assertIn("v-html", comp)

        css = (FE / "styles.css").read_text(encoding="utf-8")
        self.assertIn(".code-preview .tok-kw { color: var(--tok-kw); }", css)
        self.assertIn(".code-preview .tok-cmt", css)
        # 浅/深主题各自有一套 token，禁止写死单色
        self.assertIn("--tok-kw:", css)
        self.assertGreaterEqual(css.count("--tok-kw:"), 2)
        self.assertIn('html[data-theme="dark"]', css)
        self.assertNotIn(".code-preview .tok-kw { color: #7dd3fc; }", css)

    def test_hosts_use_code_preview(self):
        absorb = (FE / "views" / "ThesisAbsorb.vue").read_text(encoding="utf-8")
        self.assertIn("CodePreview", absorb)
        self.assertIn('lang="sql"', absorb)
        self.assertIn(":code=\"detail.draft_schema_sql\"", absorb)
        # 勿回退成裸 pre 渲 SQL
        self.assertNotIn(">{{ detail.draft_schema_sql }}</pre>", absorb)

        modals = (FE / "views" / "projectDetail" / "DetailModals.vue").read_text(encoding="utf-8")
        self.assertIn("CodePreview", modals)
        self.assertIn('lang="json"', modals)
        self.assertIn(":code=\"specText\"", modals)
        self.assertNotIn(">{{ specText }}</pre>", modals)

    def test_non_code_previews_stay_plain(self):
        """开题草稿 / 助手稿 / 日志保持明文，不上 CodePreview。"""
        absorb = (FE / "views" / "ThesisAbsorb.vue").read_text(encoding="utf-8")
        self.assertIn("detail.feed_markdown", absorb)
        self.assertIn("detail.opening_draft", absorb)
        # 这两块仍是 pre，不是 CodePreview
        self.assertIn("<pre class=\"spec-preview ta-pair-pre\">{{ detail.feed_markdown }}</pre>", absorb)
        self.assertIn("<pre class=\"spec-preview ta-pair-pre\">{{ detail.opening_draft }}</pre>", absorb)

        runtime = (FE / "views" / "projectDetail" / "RuntimeTab.vue").read_text(encoding="utf-8")
        self.assertIn('class="log-box"', runtime)
        self.assertNotIn("CodePreview", runtime)


if __name__ == "__main__":
    unittest.main()
