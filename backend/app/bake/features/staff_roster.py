"""周排班 staff_roster：开题扫词才挂；无域默认。

按员工+日期维护班次；预约页展示当日当班；派单可选看当班标记。
不做智能排课、自动最优班、考勤打卡硬件。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

STAFF_ROSTER_CAP = "staff_roster"

_TERMS = ("排班", "周排班", "值班表", "技师排班", "维修排班", "员工排班")


def scan_staff_roster(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _TERMS)


def merge_staff_roster_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
) -> list[str]:
    del domain
    out = list(caps or [])
    if STAFF_ROSTER_CAP in out:
        return out
    if not scan_staff_roster(proposal_text or ""):
        return out
    out.append(STAFF_ROSTER_CAP)
    return out


def attach_staff_roster_menus(schema: dict[str, Any]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    admin = menus.setdefault("admin", [])
    ensure_menu(
        admin,
        "staff_roster",
        {"key": "staff_roster", "label": "排班管理", "superOnly": False},
        before_key="users",
    )
    labels = schema.setdefault("labels", {})
    labels.setdefault("staffRosterPageTitle", "排班管理")
    labels.setdefault(
        "staffRosterPageLead",
        "按员工与日期维护班次；预约页可查看当日当班人员。",
    )
    labels.setdefault("staffRosterOnDutyHint", "当日当班")
    ents = schema.setdefault("entities", {})
    ents.setdefault(
        "staffRoster",
        {"key": "staff_roster", "label": "排班", "labelPlural": "排班"},
    )


def apply_staff_roster_to_spec(
    spec: dict[str, Any], proposal_text: str = ""
) -> dict[str, Any]:
    text = proposal_text or ""
    caps = merge_staff_roster_capabilities(
        list(spec.get("capabilities") or []),
        text,
        domain=spec.get("domain"),
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if STAFF_ROSTER_CAP in caps:
        attach_staff_roster_menus(schema)
        from app.bake.gate_contracts import merge_staff_roster_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_staff_roster_gate(gate, caps)
        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "排班" not in names:
            features.append({"name": "排班", "status": "module"})
        spec["features"] = features
    spec["schema"] = schema
    return spec
