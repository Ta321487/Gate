"""出包侧控件检查 p3controls：对本包 frontend/src 跑 C1～C3 契约。

真源：docs/form-controls.md §5 C4。
已登记例外与基线共用 BASELINE_KNOWN_CONTROLS；不为消红改当面页。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.bake.form_controls_contract import (
    BASELINE_KNOWN_CONTROLS,
    scan_form_controls,
)


def evaluate_workspace_form_controls_gate(workspace: Path) -> dict[str, Any]:
    """评测学生包 workspace 的可交互控件契约。"""
    fe = Path(workspace) / "frontend" / "src"
    if not fe.is_dir():
        return {
            "ok": False,
            "label": "控件检查",
            "desc": "缺少 frontend/src，无法执行出包控件检查",
        }

    findings = scan_form_controls(src=fe)
    unexpected = [f for f in findings if f.key() not in BASELINE_KNOWN_CONTROLS]
    known_hit = sum(1 for f in findings if f.key() in BASELINE_KNOWN_CONTROLS)

    ok = not unexpected
    if ok:
        desc = (
            f"本包控件检查通过（扫描命中 {len(findings)}；"
            f"已登记例外 {known_hit}）"
        )
    else:
        preview = "; ".join(str(f) for f in unexpected[:8])
        desc = f"控件契约 {len(unexpected)}：{preview}"
        if len(unexpected) > 8:
            desc += f" …共 {len(unexpected)} 条"

    return {
        "ok": ok,
        "label": "控件检查",
        "desc": desc,
        "detail": {
            "finding_count": len(findings),
            "unexpected": len(unexpected),
            "known_hit": known_hit,
            "preview": [str(f) for f in unexpected[:20]],
        },
    }
