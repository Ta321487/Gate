"""出包侧布局检查 p3layout：对本包 frontend/src 执行台账对账与结构契约。

真源：docs/ui-layout-prebake-gate.md §5。
已剪枝交付包跳过工厂全量菜单与路由对账；已登记例外与基线共用 BASELINE_KNOWN_*。
全表视觉检测不在本门禁执行。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.bake.layout_contract import (
    BASELINE_KNOWN_CONTRACTS,
    scan_layout_contracts,
)
from app.bake.layout_inventory import (
    BASELINE_KNOWN_ISSUES,
    generate_layout_inventory,
    issue_key,
    reconcile_layout_inventory,
)


def evaluate_workspace_layout_gate(workspace: Path) -> dict[str, Any]:
    """评测学生包 workspace 的布局检查（静态对账与结构契约）。"""
    fe = Path(workspace) / "frontend" / "src"
    if not fe.is_dir():
        return {
            "ok": False,
            "label": "布局检查",
            "desc": "缺少 frontend/src，无法执行出包布局检查",
        }

    rows = generate_layout_inventory(src=fe)
    issues = reconcile_layout_inventory(
        rows, src=fe, skip_menu_route_reconcile=True
    )
    inv_bad = [i for i in issues if issue_key(i) not in BASELINE_KNOWN_ISSUES]

    findings = scan_layout_contracts(src=fe)
    ctr_bad = [f for f in findings if f.key() not in BASELINE_KNOWN_CONTRACTS]

    parts: list[str] = []
    if inv_bad:
        parts.append(f"台账对账 {len(inv_bad)}：" + "; ".join(str(i) for i in inv_bad[:6]))
    if ctr_bad:
        parts.append(
            f"结构契约 {len(ctr_bad)}：" + "; ".join(str(f) for f in ctr_bad[:6])
        )

    ok = not inv_bad and not ctr_bad
    if ok:
        desc = (
            f"本包布局检查通过（台账行 {len(rows)}；"
            f"已登记例外：对账 {sum(1 for i in issues if issue_key(i) in BASELINE_KNOWN_ISSUES)}"
            f"、结构 {sum(1 for f in findings if f.key() in BASELINE_KNOWN_CONTRACTS)}）"
        )
    else:
        desc = " · ".join(parts)
        if len(inv_bad) + len(ctr_bad) > 12:
            desc += f" …共 {len(inv_bad) + len(ctr_bad)} 条"

    return {
        "ok": ok,
        "label": "布局检查",
        "desc": desc,
        "detail": {
            "row_count": len(rows),
            "inventory_unexpected": len(inv_bad),
            "contract_unexpected": len(ctr_bad),
            "inventory_preview": [str(i) for i in inv_bad[:20]],
            "contract_preview": [str(f) for f in ctr_bad[:20]],
        },
    }
