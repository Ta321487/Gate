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
    """按开题正文合并可选能力（忠诚度 / 留言 / 私信 / 收藏 / UX / 评价 / 打卡 / 推荐·冲突·逾期）。"""
    from app.bake.features.archive_log import merge_archive_log_capabilities
    from app.bake.features.core_cap_scan import (
        merge_loan_deadline_capabilities,
        merge_recommend_capabilities,
        merge_time_conflict_capabilities,
    )
    from app.bake.features.dm import merge_dm_capabilities
    from app.bake.features.exam import merge_exam_capabilities
    from app.bake.features.survey import merge_survey_capabilities
    from app.bake.features.vote import merge_vote_capabilities
    from app.bake.features.doclib import merge_doclib_capabilities
    from app.bake.features.timebank import merge_timebank_capabilities
    from app.bake.features.seat_select import merge_seat_select_capabilities
    from app.bake.features.stock_io import merge_stock_io_capabilities
    from app.bake.features.e_sign import merge_e_sign_capabilities
    from app.bake.features.e_sign import merge_e_sign_capabilities
    from app.bake.features.favorites import merge_favorites_capabilities
    from app.bake.features.guestbook import merge_guestbook_capabilities
    from app.bake.features.loyalty import merge_loyalty_capabilities
    from app.bake.features.order_extras import merge_order_extras_capabilities
    from app.bake.features.ux_scan import merge_ux_capabilities
    from app.services.proposal import strip_non_dev_sections

    body = strip_non_dev_sections(proposal_text or "")
    req = list(caps or [])
    req = merge_loyalty_capabilities(req, body)
    req = merge_exam_capabilities(req, body, domain=domain)
    req = merge_survey_capabilities(req, body, domain=domain)
    req = merge_vote_capabilities(req, body, domain=domain)
    req = merge_doclib_capabilities(req, body, domain=domain)
    req = merge_timebank_capabilities(req, body, domain=domain)
    req = merge_seat_select_capabilities(req, body, domain=domain)
    req = merge_stock_io_capabilities(req, body, domain=domain)
    req = merge_e_sign_capabilities(req, body, domain=domain)
    req = merge_guestbook_capabilities(
        req,
        body,
        domain=domain,
        archetype=archetype,
        archetypes=archetypes,
    )
    req = merge_dm_capabilities(req, body, domain=domain)
    req = merge_favorites_capabilities(req, body, domain=domain)
    req = merge_ux_capabilities(req, body)
    req = merge_order_extras_capabilities(req, body)
    req = merge_archive_log_capabilities(req, body, domain=domain)
    req = merge_recommend_capabilities(req, body)
    req = merge_time_conflict_capabilities(req, body)
    req = merge_loan_deadline_capabilities(req, body)
    return req
