"""审批/填报组 L4：单据页总管 vs 承办专员 lead。"""

from __future__ import annotations

from typing import Any

from app.bake.domains import domain_group_of

# gid=approve：总管监督全盘；一线材料审核与办结
_APPROVE_TICKET_LEADS: dict[str, tuple[str, str]] = {
    "DOM-SEAL": (
        "查看全盘用章申请，维护规则，必要时介入处理。",
        "受理用章、核验材料与办结。",
    ),
    "DOM-EXPENSE": (
        "查看全盘报销与多级审批，必要时介入处理。",
        "初审材料、推进审批与完结。",
    ),
    "DOM-LABSAFE": (
        "查看全盘准入申请，必要时介入处理。",
        "核验安全材料、批准准入与办结。",
    ),
    "DOM-FLEET": (
        "查看全盘用车申请，必要时介入处理。",
        "调度审批、派车与办结。",
    ),
    "DOM-CERT": (
        "查看全盘证明申请，必要时介入处理。",
        "核验材料、开具与办结。",
    ),
    "DOM-PROMO": (
        "查看全盘宣传方案，必要时介入处理。",
        "审核方案、推进与办结。",
    ),
    "DOM-FITOUT": (
        "查看全盘装修备案，必要时介入处理。",
        "核验备案材料与办结。",
    ),
    "DOM-ACAD": (
        "查看全盘教务申请，必要时介入处理。",
        "材料审核、催办与办结。",
    ),
    "DOM-TRIP": (
        "查看全盘出差申请，必要时介入处理。",
        "审批出差、催办与销结。",
    ),
    "DOM-CREDIT": (
        "查看全盘学分认定，必要时介入处理。",
        "材料认定、催办与办结。",
    ),
    "DOM-LABOR": (
        "查看全盘劳动时长，必要时介入处理。",
        "核验时长、催办与办结。",
    ),
    "DOM-EVAL": (
        "查看全盘评教数据，必要时介入处理。",
        "催评、汇总与办结。",
    ),
    "DOM-MORAL": (
        "查看全盘综测申报，必要时介入处理。",
        "材料审核、催办与办结。",
    ),
    "DOM-AWARD": (
        "查看全盘成果登记，必要时介入处理。",
        "核验登记、催办与办结。",
    ),
    "DOM-PROCURE": (
        "查看全盘申购，必要时介入处理。",
        "审批申购、催办与办结。",
    ),
    "DOM-CLUB": (
        "查看全盘社团材料，必要时介入处理。",
        "材料审核、催办与办结。",
    ),
    "DOM-PROJ": (
        "查看全盘项目申报，必要时介入处理。",
        "材料审核、催办与办结。",
    ),
    "DOM-ETHIC": (
        "查看全盘伦理审查，必要时介入处理。",
        "秘书核验、催办与办结。",
    ),
    "DOM-PARTY": (
        "查看全盘组织材料，必要时介入处理。",
        "材料审核、催办与办结。",
    ),
    "DOM-CONTRACT": (
        "查看全盘合同审批，必要时介入处理。",
        "合同审核、催办与办结。",
    ),
    "DOM-CARPASS": (
        "查看全盘车证备案，必要时介入处理。",
        "核验备案、催办与办结。",
    ),
    "DOM-VISITOR": (
        "查看全盘访客预约，必要时介入处理。",
        "接待核验、发卡与办结。",
    ),
    "DOM-CHECKIN": (
        "查看全楼归寝登记，必要时介入处理。",
        "查寝登记、催签与办结。",
    ),
}

_FALLBACK = (
    "查看全盘审批单据，必要时介入处理。",
    "材料审核、催办与办结。",
)


def ensure_approve_role_leads(
    schema: dict[str, Any] | None,
    *,
    domain: str,
) -> dict[str, Any] | None:
    """approve 组补 ticketsAdminLead / ticketsStaffLead（已有则不覆盖）。"""
    if not isinstance(schema, dict):
        return schema
    if domain_group_of(domain) != "approve":
        return schema
    admin_lead, staff_lead = _APPROVE_TICKET_LEADS.get(domain) or _FALLBACK
    labels = schema.setdefault("labels", {})
    if not isinstance(labels, dict):
        labels = {}
        schema["labels"] = labels
    labels.setdefault("ticketsAdminLead", admin_lead)
    labels.setdefault("ticketsStaffLead", staff_lead)
    return schema
