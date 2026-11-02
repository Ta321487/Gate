"""内容/媒资/社区组 L4：审核下架（站长）vs 一线版主/运营 lead。"""

from __future__ import annotations

from typing import Any

from app.bake.domains import domain_group_of

# gid=content：总管全盘审核下架；一线审核回复/整理媒资
_CONTENT_TICKET_LEADS: dict[str, tuple[str, str]] = {
    "DOM-FORUM": (
        "查看全盘主帖与回复，维护版规，必要时下架与介入处理。",
        "审核回复、处理违规与催办。",
    ),
    "DOM-MEDIA": (
        "查看全盘片单，维护上下架与规则，必要时介入处理。",
        "整理媒资、处理上下架与催办。",
    ),
    "DOM-MUSIC": (
        "查看全盘曲库，维护上下架与规则，必要时介入处理。",
        "整理曲目、处理上下架与催办。",
    ),
    "DOM-BLOG": (
        "查看全盘博文，维护上下架与规则，必要时介入处理。",
        "审核稿件、处理上下架与催办。",
    ),
    "DOM-DOCLIB": (
        "查看全盘资料，维护权限与上下架，必要时介入处理。",
        "核验资料、处理下载审核与催办。",
    ),
}

_FALLBACK = (
    "查看全盘内容，维护规则，必要时下架与介入处理。",
    "审核内容、处理违规与催办。",
)


def ensure_content_role_leads(
    schema: dict[str, Any] | None,
    *,
    domain: str,
) -> dict[str, Any] | None:
    """content 组补 ticketsAdminLead / ticketsStaffLead（已有则不覆盖）。"""
    if not isinstance(schema, dict):
        return schema
    if domain_group_of(domain) != "content":
        return schema
    admin_lead, staff_lead = _CONTENT_TICKET_LEADS.get(domain) or _FALLBACK
    labels = schema.setdefault("labels", {})
    if not isinstance(labels, dict):
        labels = {}
        schema["labels"] = labels
    labels.setdefault("ticketsAdminLead", admin_lead)
    labels.setdefault("ticketsStaffLead", staff_lead)
    return schema
