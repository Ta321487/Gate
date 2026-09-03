"""工作区旁路路径与主题种子。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.models import Project

from . import PPT_DIR_NAME, PPT_SUBDIR

THEMES = ("scholar", "ink", "grove")
LAYOUTS = ("band", "center", "footer")
MASTERS = ("none", "college_demo")

PPT_PIPELINE_STEPS = [
    ("collect", "收集证据（开题 + 菜单/栈 + 模块图/E-R/用例）"),
    ("fill", "填页 Unit（LLM 只整形，校验锁源）"),
    ("screenshots", "采集界面截图（主路径半自动）"),
    ("check", "瞎写/结构检查"),
    ("write", "写 deck.json（嵌入图引用）"),
]

PPT_UNIT_DEFS = [
    ("ppt.cover", "封面"),
    ("ppt.toc", "目录"),
    ("ppt.background", "背景与需求"),
    ("ppt.tech", "技术选型"),
    ("ppt.arch", "系统架构"),
    ("ppt.modules", "功能模块"),
    ("ppt.er", "E-R 图"),
    ("ppt.demo", "实现与演示"),
    ("ppt.test", "测试"),
    ("ppt.summary", "总结与致谢"),
]


def workspace_path(project: Project) -> Path | None:
    if not project.workspace_path:
        return None
    ws = Path(project.workspace_path)
    return ws if ws.is_dir() else None


def ppt_root(project: Project) -> Path | None:
    ws = workspace_path(project)
    if not ws:
        return None
    return ws / PPT_DIR_NAME / PPT_SUBDIR


def ensure_ppt_dirs(project: Project) -> Path:
    root = ppt_root(project)
    if root is None:
        raise ValueError("尚未生成工作区 · 请先完成一键生成")
    for sub in ("badge", "figures/shots", "export", "debug"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def seed_theme_for_project(project_id: str) -> dict[str, str]:
    pid = str(project_id or "0")
    h = 0
    for ch in pid:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return {
        "theme": THEMES[h % len(THEMES)],
        "layout_family": LAYOUTS[(h >> 3) % len(LAYOUTS)],
        "master": "none",
    }


def empty_cover() -> dict[str, Any]:
    return {
        "school": "",
        "college": "",
        "class_name": "",
        "student_name": "",
        "student_id": "",
        "advisor": "",
        "badge_data_url": None,
    }


def cover_complete(cover: dict[str, Any] | None) -> bool:
    if not isinstance(cover, dict):
        return False
    texts = [
        cover.get("school"),
        cover.get("college"),
        cover.get("class_name"),
        cover.get("student_name"),
        cover.get("student_id"),
        cover.get("advisor"),
    ]
    return all(str(t or "").strip() for t in texts) and bool(cover.get("badge_data_url"))


def default_steps() -> list[dict[str, Any]]:
    return [{"key": k, "title": t, "status": "pending", "meta": ""} for k, t in PPT_PIPELINE_STEPS]


def default_units() -> list[dict[str, Any]]:
    return [{"key": k, "title": t, "status": "queued", "meta": ""} for k, t in PPT_UNIT_DEFS]


def normalize_theme(value: str | None, project_id: str) -> str:
    v = str(value or "").strip()
    if v in THEMES:
        return v
    return seed_theme_for_project(project_id)["theme"]


def normalize_layout(value: str | None, project_id: str) -> str:
    v = str(value or "").strip()
    if v in LAYOUTS:
        return v
    return seed_theme_for_project(project_id)["layout_family"]


def normalize_master(value: str | None) -> str:
    v = str(value or "").strip()
    return v if v in MASTERS else "none"
