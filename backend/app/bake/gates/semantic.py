"""交付语义门禁：学生可见面、场景身份等静态检查（补 checklist 启发式盲区）。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# 学生可见 Vue/JS 扫描范围（不含注释里的工厂说明）
_STUDENT_SCAN_DIRS = (
    "frontend/src/views",
    "frontend/src/components",
    "frontend/src/layouts",
)
_DEMO_VISIBLE = re.compile(r"[「『\"']演示[」』\"']|>演示<|演示数据|演示账号")
_SKIP_SCAN = frozenset({"node_modules", "target", ".git"})

# 校园场景常见身份字段；企业/社区开题若仍出现则告警
_CAMPUS_ONLY_PROFILE = frozenset({"学号", "学院", "班级", "宿舍"})
_ENTERPRISE_ONLY_PROFILE = frozenset({"工号", "部门", "岗位"})


def _read_text(path: Path, limit: int = 120_000) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:limit]
    except OSError:
        return ""


def _strip_vue_comments(text: str) -> str:
    text = re.sub(r"<!--[\s\S]*?-->", "", text)
    text = re.sub(r"//.*?$", "", text, flags=re.MULTILINE)
    text = re.sub(r"/\*[\s\S]*?\*/", "", text)
    return text


def _scan_demo_wording(workspace: Path) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for rel in _STUDENT_SCAN_DIRS:
        base = workspace / rel
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in (".vue", ".js", ".ts"):
                continue
            raw = _read_text(path)
            body = _strip_vue_comments(raw)
            for m in _DEMO_VISIBLE.finditer(body):
                line = body[: m.start()].count("\n") + 1
                hits.append(
                    {
                        "file": path.relative_to(workspace).as_posix(),
                        "line": str(line),
                        "snippet": body[max(0, m.start() - 12) : m.end() + 12].strip(),
                    }
                )
                if len(hits) >= 8:
                    return hits
    return hits


def _scene_profile_mismatch(workspace: Path, spec: dict[str, Any]) -> list[str]:
    """schema.scene 与注册资料字段 label 粗对齐。"""
    schema = spec.get("schema") if isinstance(spec.get("schema"), dict) else {}
    scene = str(schema.get("scene") or spec.get("scene") or "").strip().lower()
    if not scene:
        return []

    pf_path = workspace / "backend" / "src" / "main" / "resources" / "profile-fields.json"
    if not pf_path.is_file():
        # 回退读 ProfileFields 生成的前端资源
        pf_path = workspace / "frontend" / "src" / "utils" / "profileFields.js"
    blob = _read_text(pf_path, 80_000)
    if not blob:
        return []

    issues: list[str] = []
    if scene in ("enterprise", "company", "corp"):
        for term in _CAMPUS_ONLY_PROFILE:
            if term in blob:
                issues.append(f"企业场景资料页仍含「{term}」")
    elif scene in ("campus", "school", "university"):
        for term in _ENTERPRISE_ONLY_PROFILE:
            if term in blob and "学生" not in blob[max(0, blob.find(term) - 20) : blob.find(term) + 20]:
                issues.append(f"校园场景资料页仍含「{term}」")
    return issues[:6]


def evaluate_semantic_gates(workspace: Path, spec: dict[str, Any]) -> dict[str, Any]:
    """返回 p3s 语义门禁子项。"""
    demo_hits = _scan_demo_wording(workspace)
    profile_issues = _scene_profile_mismatch(workspace, spec)
    demo_ok = not demo_hits
    profile_ok = not profile_issues

    desc_parts: list[str] = []
    if not demo_ok:
        desc_parts.append(f"学生可见面含「演示」字样 {len(demo_hits)} 处")
    if not profile_ok:
        desc_parts.append("；".join(profile_issues[:3]))

    return {
        "p3s": {
            "ok": demo_ok and profile_ok,
            "label": "交付语义 · 可见面与场景",
            "desc": "；".join(desc_parts) if desc_parts else "未见明显演示字样与场景穿帮",
            "detail": {
                "demo_hits": demo_hits[:8],
                "profile_issues": profile_issues,
            },
        }
    }


def merge_semantic_into_gates(gates: dict[str, Any], workspace: Path, spec: dict[str, Any]) -> None:
    """就地合并 p3s，并同步 overall / zip_allowed。"""
    sem = evaluate_semantic_gates(workspace, spec).get("p3s") or {}
    gates["p3s"] = sem
    from app.bake.gates.keys import GATE_CORE_KEYS

    core_keys = [k for k in GATE_CORE_KEYS if isinstance(gates.get(k), dict)]
    all_ok = all(bool(gates[k].get("ok")) for k in core_keys)
    gates["overall"] = all_ok
    if not all_ok:
        gates["zip_allowed"] = False
