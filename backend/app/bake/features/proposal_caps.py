"""开题扫词 → 能力并集：attach_accept 与 domain_sql 共用，避免 schema/SQL 双轨漂移。"""

from __future__ import annotations

from typing import Any


def merge_proposal_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
) -> list[str]:
    """按开题正文合并可选能力（忠诚度 / 留言 / 收藏 / UX / 评价 / 打卡记录）。"""
    from app.bake.features.archive_log import merge_archive_log_capabilities
    from app.bake.features.favorites import merge_favorites_capabilities
    from app.bake.features.guestbook import merge_guestbook_capabilities
    from app.bake.features.loyalty import merge_loyalty_capabilities
    from app.bake.features.order_extras import merge_order_extras_capabilities
    from app.bake.features.ux_scan import merge_ux_capabilities
    from app.services.proposal import strip_non_dev_sections

    body = strip_non_dev_sections(proposal_text or "")
    req = list(caps or [])
    req = merge_loyalty_capabilities(req, body)
    req = merge_guestbook_capabilities(
        req,
        body,
        domain=domain,
        archetype=archetype,
        archetypes=archetypes,
    )
    req = merge_favorites_capabilities(req, body, domain=domain)
    req = merge_ux_capabilities(req, body)
    req = merge_order_extras_capabilities(req, body)
    req = merge_archive_log_capabilities(req, body, domain=domain)
    return req
