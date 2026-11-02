"""互动/匹配组 L4：总管监督 vs 一线联谊/秘书/对接/核销 lead。"""

from __future__ import annotations

from typing import Any

from app.bake.domains import domain_group_of

# gid=interact：总管监督规则与调剂；一线审核牵线/志愿/对接/核销
_INTERACT_TICKET_LEADS: dict[str, tuple[str, str]] = {
    "DOM-DATING": (
        "查看全盘牵线申请，维护规范，必要时介入处理。",
        "审核牵线、反馈结果与催办。",
    ),
    "DOM-MUTUAL-TUTOR": (
        "查看全盘导师志愿与调剂，维护规则，必要时介入处理。",
        "协助确认、调剂与催办。",
    ),
    "DOM-MUTUAL-TOPIC": (
        "查看全盘选题志愿与调剂，维护规则，必要时介入处理。",
        "协助确认、调剂与催办。",
    ),
    "DOM-MUTUAL-TEAM": (
        "查看全盘组队志愿与调剂，维护规则，必要时介入处理。",
        "协助确认、调剂与催办。",
    ),
    "DOM-CARPOOL": (
        "查看全盘行程对接，维护规则，必要时介入处理。",
        "协助确认、调剂与催办。",
    ),
    "DOM-TIMEBANK": (
        "查看全盘时长核销，维护规则，必要时介入处理。",
        "审核扣减、核销与催办。",
    ),
    "DOM-EXAM": (
        "查看全盘试卷与阅卷进度，维护规则，必要时介入处理。",
        "阅卷、催交与成绩复核。",
    ),
    "DOM-SURVEY": (
        "查看全盘问卷回收，维护规则，必要时介入处理。",
        "发布回收、催答与统计。",
    ),
    "DOM-VOTE": (
        "查看全盘评选投票，维护规则，必要时介入处理。",
        "维护场次、催投与公示。",
    ),
}

_FALLBACK = (
    "查看全盘互动申请，维护规则，必要时介入处理。",
    "审核申请、催办与办结。",
)


def ensure_interact_role_leads(
    schema: dict[str, Any] | None,
    *,
    domain: str,
) -> dict[str, Any] | None:
    """interact 组补 ticketsAdminLead / ticketsStaffLead（已有则不覆盖）。"""
    if not isinstance(schema, dict):
        return schema
    if domain_group_of(domain) != "interact":
        return schema
    admin_lead, staff_lead = _INTERACT_TICKET_LEADS.get(domain) or _FALLBACK
    labels = schema.setdefault("labels", {})
    if not isinstance(labels, dict):
        labels = {}
        schema["labels"] = labels
    labels.setdefault("ticketsAdminLead", admin_lead)
    labels.setdefault("ticketsStaffLead", staff_lead)
    return schema
