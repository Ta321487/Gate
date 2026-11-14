"""出包门禁快照：按 Job 落库，历史不覆盖。

与控制台「质量门禁」表同源（P0–P3 行 + 清单）；不含编译/Playwright 巨文。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

# 与 frontend useProjectDetail.gateRows 键序对齐
GATE_ROW_KEYS: tuple[str, ...] = (
    "p0a",
    "p0b",
    "p1",
    "p2",
    "p3a",
    "p3b",
    "p3t",
    "p3s",
    "p3n",
    "p3ac",
    "p3lean",
    "p3layout",
    "p3controls",
    "p3q",
    "p3copy",
    "p3c",
    "p3d",
    "accept",
)

GATE_ROW_LEVELS: dict[str, str] = {
    "p0a": "P0",
    "p0b": "P0",
    "p1": "P1",
    "p2": "P2",
    "p3a": "P3",
    "p3b": "P3",
    "p3t": "P3",
    "p3s": "P3",
    "p3n": "P3",
    "p3ac": "P3",
    "p3lean": "P3",
    "p3layout": "P3",
    "p3controls": "P3",
    "p3q": "P3",
    "p3copy": "P3",
    "p3c": "P3",
    "p3d": "P3",
    "accept": "P3",
}

_DESC_CAP = 4000


def _cap_desc(desc: Any) -> str:
    desc_s = str(desc) if desc is not None else ""
    if len(desc_s) > _DESC_CAP:
        return desc_s[: _DESC_CAP - 1] + "…"
    return desc_s


def _slim_gate_item(item: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if "ok" in item:
        out["ok"] = bool(item.get("ok"))
    if "warn" in item:
        out["warn"] = bool(item.get("warn"))
    if item.get("label") is not None:
        out["label"] = str(item.get("label") or "")
    if "desc" in item and item.get("desc") is not None:
        out["desc"] = _cap_desc(item.get("desc"))
    return out


def gate_rows_from_map(gate_map: dict[str, Any]) -> list[dict[str, Any]]:
    """生成与控制台质量门禁表同形的行列表。"""
    rows: list[dict[str, Any]] = []
    for k in GATE_ROW_KEYS:
        item = gate_map.get(k)
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "key": k,
                "level": GATE_ROW_LEVELS.get(k, "P3"),
                "label": str(item.get("label") or k),
                "ok": bool(item.get("ok")),
                "warn": bool(item.get("warn")),
                "desc": _cap_desc(item.get("desc")),
            }
        )
    return rows


def build_gate_report(
    gates: dict[str, Any] | None,
    checklist: list[Any] | None = None,
) -> dict[str, Any]:
    """从 evaluate 结果或 project.gates 生成可落库快照。

    结构（表行级，非巨文）：
    - overall / zip_allowed
    - rows：控制台门禁表（与 UI 同形）
    - checklist：清单实装行
    - gates：按键瘦身后的门禁（仅 ok/warn/label/desc）
    """
    raw = gates if isinstance(gates, dict) else {}
    if checklist is None:
        cl_src = raw.get("checklist")
        checklist = list(cl_src) if isinstance(cl_src, list) else []
    elif not isinstance(checklist, list):
        checklist = []

    slim_gates: dict[str, Any] = {}
    for k, v in raw.items():
        if k == "checklist":
            continue
        if k in ("overall", "zip_allowed"):
            slim_gates[k] = bool(v)
            continue
        if isinstance(v, dict):
            slim_gates[k] = _slim_gate_item(v)
        else:
            slim_gates[k] = v
    rows = gate_rows_from_map(slim_gates)
    return {
        "overall": bool(slim_gates.get("overall")),
        "zip_allowed": bool(slim_gates.get("zip_allowed")),
        "rows": rows,
        "checklist": deepcopy(checklist),
        "gates": slim_gates,
    }


def attach_gate_report(
    job: Any,
    gates: dict[str, Any] | None,
    checklist: list[Any] | None = None,
) -> dict[str, Any]:
    """写入本 Job 的门禁快照（新 Job 新行，不覆盖历史任务）。"""
    report = build_gate_report(gates, checklist)
    job.gate_report = report
    try:
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(job, "gate_report")
    except Exception:  # noqa: BLE001
        pass
    return report
