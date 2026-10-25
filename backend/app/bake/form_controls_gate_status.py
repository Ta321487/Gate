"""可交互控件闸 · C5 工厂摘要（控制台可读）。

真源：docs/form-controls.md §5 C5。
只读基线：C1～C3 契约扫；出包另挂 p3controls。
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.bake.form_controls_contract import (
    BASELINE_KNOWN_CONTROLS,
    PATTERN_IDS,
    scan_form_controls,
)


def form_controls_gate_snapshot(root: Path | None = None) -> dict[str, Any]:
    """返回工厂可读的控件闸摘要。"""
    findings = scan_form_controls(root)
    unexpected = [f for f in findings if f.key() not in BASELINE_KNOWN_CONTROLS]
    known = [f for f in findings if f.key() in BASELINE_KNOWN_CONTROLS]
    ok = not unexpected

    by_pattern = Counter(f.pattern_id for f in findings)
    unexpected_by = Counter(f.pattern_id for f in unexpected)
    known_by = Counter(f.pattern_id for f in known)

    parts: list[str] = []
    if ok:
        parts.append(
            "控件契约通过"
            + (f"（已登记例外 {len(known)}）" if known else "")
        )
    else:
        parts.append(f"控件契约未通过 {len(unexpected)} 项")
    parts.append("出包另挂门禁 p3controls")
    summary = " · ".join(parts)

    def _row(f: Any) -> dict[str, str]:
        return {
            "pattern_id": f.pattern_id,
            "vue": f.vue,
            "message": f.message,
            "detail": f.detail,
        }

    return {
        "ok": ok,
        "summary": summary,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "patterns": list(PATTERN_IDS),
        "contract": {
            "ok": ok,
            "finding_count": len(unexpected),
            "known_debt_count": len(known),
            "hit_count": len(findings),
            "by_pattern": dict(by_pattern),
            "unexpected_by_pattern": dict(unexpected_by),
            "known_by_pattern": dict(known_by),
            "findings": [_row(f) for f in unexpected[:40]],
            "known_debt": [_row(f) for f in known[:30]],
        },
        "bake": {
            "gate_key": "p3controls",
            "fail_code": "BAKE_FORM_CONTROLS",
            "summary": "出包对本包 frontend/src 跑同一套契约；红则禁 ZIP",
        },
    }
