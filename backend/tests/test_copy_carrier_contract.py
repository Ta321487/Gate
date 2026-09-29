"""载体口径判据：同一句话放对载体，放错即红。

口径（2026-09-27 定，见 docs/delivery-audit-rules.md / HANDOFF「专项交接：话术层」）：

- **学生可见面**（产物 schema 的 labels/轮播/菜单/种子 + baseline 前端页面）**只描述本系统动作**，
  不写硬件否定句（「不对接闸机」这类划界语属于工厂说明书腔，`FACTORY_UI_FORBIDDEN` 已禁）；
- **工厂侧**（能力表 desc、功能模块 docstring、审计/答辩口径）**必须写**划界语，
  否则「不做硬件」就没有落点，答辩时容易被误当成已支持。

本文件把这三条各钉成一条测试：页面禁 → 必须红；工厂侧缺 → 必须红。
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BASELINE_FE = REPO / "skeletons" / "baseline" / "frontend" / "src"

# 硬件纠葛词：出现在学生可见面即「把工厂划界语写进了页面」
_HARDWARE_WORDS = ("闸机", "人脸识别", "指纹", "GPS", "真门禁", "硬件联动")

_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
_LINE_COMMENT_RE = re.compile(r"(?m)^\s*//.*$")


def visible_copy_text(source: str) -> str:
    """剥掉注释后的“可见文案面”：注释里可以写口径，页面文案里不许写。"""
    text = _HTML_COMMENT_RE.sub(" ", source or "")
    text = _BLOCK_COMMENT_RE.sub(" ", text)
    return _LINE_COMMENT_RE.sub(" ", text)


def _strings(node) -> list[str]:
    out: list[str] = []
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, dict):
        for v in node.values():
            out.extend(_strings(v))
    elif isinstance(node, (list, tuple)):
        for v in node:
            out.extend(_strings(v))
    return out


class CopyCarrierContractTests(unittest.TestCase):
    def test_student_visible_schema_copy_has_no_hardware_scope(self):
        from app.bake.schema.templates import SCHEMA_BUILDERS

        for domain, builder in SCHEMA_BUILDERS.items():
            schema = builder("测试课题")
            for text in _strings(
                [
                    schema.get("labels") or {},
                    schema.get("portalBanners") or [],
                    schema.get("menus") or {},
                    schema.get("seeds") or {},
                ]
            ):
                for word in _HARDWARE_WORDS:
                    self.assertNotIn(
                        word, text, f"{domain} 学生可见面出现硬件划界语：{text}"
                    )

    def test_baseline_frontend_pages_have_no_hardware_scope(self):
        for path in sorted(BASELINE_FE.rglob("*")):
            if not path.is_file() or path.suffix not in (".vue", ".js"):
                continue
            text = visible_copy_text(path.read_text(encoding="utf-8", errors="ignore"))
            for word in _HARDWARE_WORDS:
                self.assertNotIn(
                    word, text, f"{path.relative_to(REPO).as_posix()} 可见文案出现硬件划界语"
                )

    def test_student_copy_has_no_factory_speak(self):
        """学生可见面不得出现工厂说明书腔（FACTORY_UI_FORBIDDEN）——全域 + SQL 公告 + 前端。"""
        from app.bake.domain_schema import FACTORY_UI_FORBIDDEN
        from app.bake.domain_vocab import seed_notices
        from app.bake.engine import domain_sql
        from app.bake.schema.templates import SCHEMA_BUILDERS

        bad: list[str] = []
        for domain, builder in sorted(SCHEMA_BUILDERS.items()):
            schema = builder("测试课题")
            for text in _strings(
                [
                    schema.get("labels") or {},
                    schema.get("seeds") or {},
                    schema.get("portalBanners") or [],
                    schema.get("menus") or {},
                ]
            ):
                for token in FACTORY_UI_FORBIDDEN:
                    if token in text:
                        bad.append(f"{domain} schema[{token}] {text[:40]}")
                        break
            for title, body in seed_notices(domain_sql(domain, "thesis_test")):
                for token in FACTORY_UI_FORBIDDEN:
                    if token in f"{title}{body}":
                        bad.append(f"{domain} 种子公告[{token}] {title}")
                        break
        for path in sorted(BASELINE_FE.rglob("*.vue")):
            text = visible_copy_text(path.read_text(encoding="utf-8", errors="ignore"))
            for token in FACTORY_UI_FORBIDDEN:
                if token in text:
                    bad.append(f"{path.name}[{token}]")
                    break
        self.assertEqual(
            bad[:12], [], "学生可见面不得出现工厂说明书腔：" + "；".join(bad[:12])
        )

    def test_factory_side_keeps_boundary_wording(self):
        caps_text = (REPO / "backend/app/bake/capabilities.py").read_text(encoding="utf-8")
        self.assertIn("不对接闸机", caps_text)
        module = __import__("app.bake.features.code_qr", fromlist=["code_qr"])
        self.assertIn("不对接闸机", module.__doc__ or "")
        rules = (REPO / "docs/delivery-audit-rules.md").read_text(encoding="utf-8")
        self.assertIn("不对接闸机硬件", rules)


if __name__ == "__main__":
    unittest.main()
