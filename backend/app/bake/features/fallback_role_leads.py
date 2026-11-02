"""兜底组 L4：DOM-GENERIC 按壳路径拆总管 vs 办理员 lead。"""

from __future__ import annotations

from typing import Any

from app.bake.domains import domain_group_of

# 审核流：总管监督规则；一线审核办结
_TICKET_LEADS = (
    "查看全盘申请，维护规则，必要时介入处理。",
    "审核申请、催办与办结。",
)

# 交易流：总管监督全盘；一线确认履约（勿把发货写进总管）
_ORDER_LEADS = (
    "查看全盘订单与售后，必要时介入处理。",
    "确认履约、发货或自提与售后办理。",
)

# 预约流：总管监督；一线确认办结
_RESERVE_LEADS = (
    "查看全盘预约，维护规则，必要时介入处理。",
    "办理预约确认、催到与办结。",
)


def ensure_fallback_role_leads(
    schema: dict[str, Any] | None,
    *,
    domain: str,
) -> dict[str, Any] | None:
    """fallback 组按实体路径补 Admin/Staff lead（已有则不覆盖）。"""
    if not isinstance(schema, dict):
        return schema
    if domain_group_of(domain) != "fallback":
        return schema
    labels = schema.setdefault("labels", {})
    if not isinstance(labels, dict):
        labels = {}
        schema["labels"] = labels
    ents = schema.get("entities") if isinstance(schema.get("entities"), dict) else {}

    if "ticket" in ents:
        admin_lead, staff_lead = _TICKET_LEADS
        labels.setdefault("ticketsAdminLead", admin_lead)
        labels.setdefault("ticketsStaffLead", staff_lead)
    if "order" in ents:
        admin_lead, staff_lead = _ORDER_LEADS
        labels.setdefault("ordersAdminLead", admin_lead)
        labels.setdefault("ordersStaffLead", staff_lead)
    if "reservation" in ents:
        admin_lead, staff_lead = _RESERVE_LEADS
        labels.setdefault("reservationsAdminLead", admin_lead)
        labels.setdefault("reservationsStaffLead", staff_lead)
    return schema
