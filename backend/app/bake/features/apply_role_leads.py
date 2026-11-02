"""报名/申请组 L4：单据页总管 vs 助理/管理员 lead。"""

from __future__ import annotations

from typing import Any

from app.bake.domains import domain_group_of

# gid=apply：总管监督名额与规则；一线审核报名/认领/选课
_APPLY_TICKET_LEADS: dict[str, tuple[str, str]] = {
    "DOM-ACTIVITY": (
        "查看全盘活动报名，维护名额与规则，必要时介入处理。",
        "审核报名、签到催办与取消处理。",
    ),
    "DOM-LOST": (
        "查看全盘招领认领，必要时介入处理。",
        "核验认领材料、通过与驳回。",
    ),
    "DOM-COURSE": (
        "查看全盘选课申请，维护名额与规则，必要时介入处理。",
        "审核选课、退选与催办。",
    ),
    "DOM-TOUR": (
        "查看全盘线路报名，维护名额与规则，必要时介入处理。",
        "确认报名、催办与取消处理。",
    ),
}

_FALLBACK = (
    "查看全盘报名申请，必要时介入处理。",
    "审核报名、催办与办结。",
)


def ensure_apply_role_leads(
    schema: dict[str, Any] | None,
    *,
    domain: str,
) -> dict[str, Any] | None:
    """apply 组补 ticketsAdminLead / ticketsStaffLead（已有则不覆盖）。"""
    if not isinstance(schema, dict):
        return schema
    if domain_group_of(domain) != "apply":
        return schema
    admin_lead, staff_lead = _APPLY_TICKET_LEADS.get(domain) or _FALLBACK
    labels = schema.setdefault("labels", {})
    if not isinstance(labels, dict):
        labels = {}
        schema["labels"] = labels
    labels.setdefault("ticketsAdminLead", admin_lead)
    labels.setdefault("ticketsStaffLead", staff_lead)
    return schema
