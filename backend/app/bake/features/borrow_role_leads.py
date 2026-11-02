"""借用组 L4：单据页总管 vs 馆员/店员 lead。"""

from __future__ import annotations

from typing import Any

from app.bake.domains import domain_group_of

# gid=borrow 组员；文案跟角色树：总管监督/额度，一线审批核销
_BORROW_TICKET_LEADS: dict[str, tuple[str, str]] = {
    "DOM-LIBRARY": (
        "查看全馆借阅与读者额度，必要时介入处理。",
        "办理借还审核、催还与柜台取还。",
    ),
    "DOM-EQUIP": (
        "查看全室借用与额度，必要时介入处理。",
        "审批借用、发放归还验收与催还。",
    ),
    "DOM-ASSET": (
        "查看全库领用与额度，必要时介入处理。",
        "审批领用、出库核销与归还确认。",
    ),
    "DOM-PARCEL": (
        "查看全站取件单，必要时介入处理。",
        "核销出库、催取与现场取件办理。",
    ),
    "DOM-BED": (
        "查看全楼床位申请，必要时介入处理。",
        "审批调宿、办理入住与床位核销。",
    ),
}

_FALLBACK = (
    "查看全站单据与额度，必要时介入处理。",
    "审批、核销与现场办结。",
)


def ensure_borrow_role_leads(
    schema: dict[str, Any] | None,
    *,
    domain: str,
) -> dict[str, Any] | None:
    """borrow 组补 ticketsAdminLead / ticketsStaffLead（已有则不覆盖）。"""
    if not isinstance(schema, dict):
        return schema
    if domain_group_of(domain) != "borrow":
        return schema
    admin_lead, staff_lead = _BORROW_TICKET_LEADS.get(domain) or _FALLBACK
    labels = schema.setdefault("labels", {})
    if not isinstance(labels, dict):
        labels = {}
        schema["labels"] = labels
    labels.setdefault("ticketsAdminLead", admin_lead)
    labels.setdefault("ticketsStaffLead", staff_lead)
    return schema
