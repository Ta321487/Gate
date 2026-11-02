"""跟进组 L4：单据页总管 vs 辅导员/专员 lead。"""

from __future__ import annotations

from typing import Any

from app.bake.domains import domain_group_of

# gid=follow：总管监督全盘；一线审阅/跟进/催办
_FOLLOW_TICKET_LEADS: dict[str, tuple[str, str]] = {
    "DOM-INTERN": (
        "查看全员周报与实习岗位，必要时介入处理。",
        "审阅周报、催交与退回修改。",
    ),
    "DOM-CRM": (
        "查看全盘客户跟进，必要时介入处理。",
        "登记跟进、催办与完结。",
    ),
    "DOM-EVENT": (
        "查看全盘事件上报，必要时介入处理。",
        "随访打卡、催办与完结。",
    ),
    "DOM-ATTEND": (
        "查看全员考勤与请假，必要时介入处理。",
        "审批请假、催办与销假。",
    ),
    "DOM-FUND": (
        "查看全盘资助申请，必要时介入处理。",
        "材料审核、公示与发放登记。",
    ),
    "DOM-RECRUIT": (
        "查看全盘投递与岗位，必要时介入处理。",
        "简历筛选、面试安排与流程办结。",
    ),
    "DOM-GRADE": (
        "查看全盘成绩相关申请，必要时介入处理。",
        "教务确认、催办与办结。",
    ),
    "DOM-LISTING": (
        "查看全盘房源意向，必要时介入处理。",
        "带看跟进、催办与成交登记。",
    ),
}

_FALLBACK = (
    "查看全盘跟进单据，必要时介入处理。",
    "跟进催办与办结。",
)


def ensure_follow_role_leads(
    schema: dict[str, Any] | None,
    *,
    domain: str,
) -> dict[str, Any] | None:
    """follow 组补 ticketsAdminLead / ticketsStaffLead（已有则不覆盖）。"""
    if not isinstance(schema, dict):
        return schema
    if domain_group_of(domain) != "follow":
        return schema
    admin_lead, staff_lead = _FOLLOW_TICKET_LEADS.get(domain) or _FALLBACK
    labels = schema.setdefault("labels", {})
    if not isinstance(labels, dict):
        labels = {}
        schema["labels"] = labels
    labels.setdefault("ticketsAdminLead", admin_lead)
    labels.setdefault("ticketsStaffLead", staff_lead)
    return schema
