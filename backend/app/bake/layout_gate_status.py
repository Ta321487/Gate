"""起包前布局检查 · D5 工厂摘要（控制台可读）。

真源：docs/ui-layout-prebake-gate.md §3.1 / §4 D5。
只读基线：台账对账与结构契约；全表视觉检测不在本摘要触发（status=not_run）。
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.bake.layout_contract import (
    BASELINE_KNOWN_CONTRACTS,
    scan_layout_contracts,
)
from app.bake.layout_inventory import (
    BASELINE_KNOWN_ISSUES,
    generate_layout_inventory,
    inventory_coverage,
    issue_key,
    reconcile_layout_inventory,
)


def layout_gate_snapshot(root: Path | None = None) -> dict[str, Any]:
    """返回工厂可读的布局闸摘要（廉价；不含 Playwright 全表）。"""
    rows = generate_layout_inventory(root)
    issues = reconcile_layout_inventory(rows, root=root)
    inv_unexpected = [i for i in issues if issue_key(i) not in BASELINE_KNOWN_ISSUES]
    inv_known = [i for i in issues if issue_key(i) in BASELINE_KNOWN_ISSUES]
    inv_ok = not inv_unexpected

    findings = scan_layout_contracts(root)
    ctr_unexpected = [f for f in findings if f.key() not in BASELINE_KNOWN_CONTRACTS]
    ctr_known = [f for f in findings if f.key() in BASELINE_KNOWN_CONTRACTS]
    ctr_ok = not ctr_unexpected

    by_kind = Counter(r.kind for r in rows)
    overall_ok = inv_ok and ctr_ok

    parts: list[str] = []
    if inv_ok:
        parts.append(
            "台账对账通过"
            + (f"（已登记例外 {len(inv_known)}）" if inv_known else "")
        )
    else:
        parts.append(f"台账对账未通过 {len(inv_unexpected)} 项")
    if ctr_ok:
        parts.append(
            "结构契约通过"
            + (f"（已登记例外 {len(ctr_known)}）" if ctr_known else "")
        )
    else:
        parts.append(f"结构契约未通过 {len(ctr_unexpected)} 项")
    parts.append("视觉全表由自动化测试执行（本摘要不触发）")
    summary = " · ".join(parts)

    return {
        "ok": overall_ok,
        "summary": summary,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "inventory": {
            "ok": inv_ok,
            "row_count": len(rows),
            "by_kind": dict(by_kind),
            "coverage": inventory_coverage(rows, root=root),
            "issue_count": len(inv_unexpected),
            "known_debt_count": len(inv_known),
            "issues": [
                {"code": i.code, "message": i.message, "detail": i.detail}
                for i in inv_unexpected[:40]
            ],
            "known_debt": [
                {"code": i.code, "message": i.message, "detail": i.detail}
                for i in inv_known[:20]
            ],
        },
        "contract": {
            "ok": ctr_ok,
            "finding_count": len(ctr_unexpected),
            "known_debt_count": len(ctr_known),
            "findings": [
                {
                    "pattern_id": f.pattern_id,
                    "defect_class": f.defect_class,
                    "vue": f.vue,
                    "message": f.message,
                    "detail": f.detail,
                }
                for f in ctr_unexpected[:40]
            ],
            "known_debt": [
                {
                    "pattern_id": f.pattern_id,
                    "defect_class": f.defect_class,
                    "vue": f.vue,
                    "message": f.message,
                    "detail": f.detail,
                }
                for f in ctr_known[:20]
            ],
        },
        "smoke": {
            "ok": None,
            "status": "not_run",
            "summary": "全表视觉检测不在本接口执行；请运行 tests/test_layout_smoke.py::test_full_table_coverage",
        },
    }
