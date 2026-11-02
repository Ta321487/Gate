"""报修/工单组 L4：单据页总管 vs 楼管/调度/运维 lead。"""

from __future__ import annotations

from typing import Any

from app.bake.domains import domain_group_of

# gid=ticket：总管监督派单与主数据；一线受理跟进办结
_TICKET_GROUP_LEADS: dict[str, tuple[str, str]] = {
    "DOM-DORM": (
        "查看全楼报修工单，维护楼栋与类型，必要时介入处理。",
        "受理报修、派单跟进与办结。",
    ),
    "DOM-PROPERTY": (
        "查看全盘报修投诉，维护分区与类型，必要时介入处理。",
        "受理报修、调度派单与办结。",
    ),
    "DOM-IT": (
        "查看全站故障工单，维护分类，必要时介入处理。",
        "受理故障、接单跟进与办结。",
    ),
}

_FALLBACK = (
    "查看全站工单，维护分类，必要时介入处理。",
    "受理工单、跟进与办结。",
)


def ensure_repair_role_leads(
    schema: dict[str, Any] | None,
    *,
    domain: str,
) -> dict[str, Any] | None:
    """ticket 组补 ticketsAdminLead / ticketsStaffLead（已有则不覆盖）。"""
    if not isinstance(schema, dict):
        return schema
    if domain_group_of(domain) != "ticket":
        return schema
    admin_lead, staff_lead = _TICKET_GROUP_LEADS.get(domain) or _FALLBACK
    labels = schema.setdefault("labels", {})
    if not isinstance(labels, dict):
        labels = {}
        schema["labels"] = labels
    labels.setdefault("ticketsAdminLead", admin_lead)
    labels.setdefault("ticketsStaffLead", staff_lead)
    return schema
