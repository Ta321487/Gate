"""工厂 LLM 硬原则合同：不确定→确定性（docs/llm-determinism.md）。

审类：确定性闸文案/穷尽纪律必须在 Agent 提示与无 LLM 路径里可见；
生成类：unit_flow 模块须声明校验回退。
"""

from __future__ import annotations

from pathlib import Path

from app.llm import agents_qa, agents_thesis_diagrams
from app.llm.unit_flow import runner as unit_runner


def test_qa_sys_is_structural_primary_exhaustive():
    sys = agents_qa._SYS
    assert "穷尽" in sys
    assert "structural" in sys.lower() or "结构闸" in sys
    assert "不要重复" in sys or "禁止重复" in sys


def test_thesis_audit_sys_is_exhaustive_deterministic_first():
    sys = agents_thesis_diagrams._SYS
    assert "穷尽" in sys
    assert "deterministic" in sys.lower() or "确定性" in sys
    assert "auth" in sys.lower()  # 禁止登录误报不在菜单


def test_fallback_qa_mode_is_deterministic_not_empty_fuse():
    """无 LLM 时结构闸仍是主审，mode=deterministic。"""
    report = agents_qa._fallback_qa(
        {
            "domain": "DOM-GENERIC",
            "title": "测",
            "menuKeys": {"user": [], "admin": []},
            "entityKeys": [],
            "entities": {},
            "labels": {},
            "seeds": {},
            "files": {},
            "schema": {},
            "capabilities": [],
            "accept": {},
            "proposal": "",
        }
    )
    assert report.get("mode") == "deterministic"
    assert report.get("structural_primary") is True
    assert report.get("llm_used") is False
    assert "findings" in report


def test_unit_flow_runner_documents_generate_fallback():
    doc = unit_runner.__doc__ or ""
    assert "确定性" in doc or "fallback" in doc.lower()
    assert "llm-determinism" in doc or "不确定" in doc


def test_principle_doc_exists():
    root = Path(__file__).resolve().parents[2]
    path = root / "docs" / "llm-determinism.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "不确定" in text and "确定性" in text
    rule = root / ".cursor" / "rules" / "llm-determinism.mdc"
    assert rule.is_file()
