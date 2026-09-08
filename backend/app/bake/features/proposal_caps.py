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
    from app.bake.features.audit_log import merge_audit_log_capabilities
    from app.bake.features.message_template import merge_message_template_capabilities
    from app.bake.features.code_qr import merge_code_qr_capabilities
    from app.bake.features.staff_roster import merge_staff_roster_capabilities
    from app.bake.features.room_equipment import merge_room_equipment_capabilities
    from app.bake.features.book_hold import merge_book_hold_capabilities
    from app.bake.features.post_mute import merge_post_mute_capabilities
    from app.bake.features.book_suggest import merge_book_suggest_capabilities
    from app.bake.features.product_spec import merge_product_spec_capabilities
    from app.bake.features.core_cap_scan import (
        merge_loan_deadline_capabilities,
        merge_loan_renew_capabilities,
        merge_recommend_capabilities,
        merge_time_conflict_capabilities,
    )
    from app.bake.features.ticket_flow_opts import merge_waitlist_capabilities
    from app.bake.features.dm import merge_dm_capabilities
    from app.bake.features.exam import merge_exam_capabilities
    from app.bake.features.survey import merge_survey_capabilities
    from app.bake.features.vote import merge_vote_capabilities
    from app.bake.features.doclib import merge_doclib_capabilities
    from app.bake.features.timebank import merge_timebank_capabilities
    from app.bake.features.seat_select import merge_seat_select_capabilities
    from app.bake.features.stock_io import merge_stock_io_capabilities
    from app.bake.features.stock_scrap import merge_stock_scrap_capabilities
    from app.bake.features.e_sign import merge_e_sign_capabilities
    from app.bake.features.favorites import (
        merge_content_report_capabilities,
        merge_favorites_capabilities,
        merge_post_like_capabilities,
    )
    from app.bake.features.guestbook import merge_guestbook_capabilities
    from app.bake.features.ai_assistant import merge_ai_assistant_capabilities
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
    req = merge_stock_scrap_capabilities(req, body, domain=domain)
    req = merge_e_sign_capabilities(req, body, domain=domain)
    req = merge_guestbook_capabilities(
        req,
        body,
        domain=domain,
        archetype=archetype,
        archetypes=archetypes,
    )
    # 开关 force 在 apply_ai_assistant_to_spec；此处只靠开题扫词
    req = merge_ai_assistant_capabilities(req, body, force=False)
    req = merge_dm_capabilities(req, body, domain=domain)
    req = merge_favorites_capabilities(req, body, domain=domain)
    req = merge_post_like_capabilities(req, body, domain=domain)
    req = merge_content_report_capabilities(req, body, domain=domain)
    req = merge_ux_capabilities(req, body)
    req = merge_order_extras_capabilities(req, body)
    req = merge_archive_log_capabilities(req, body, domain=domain)
    req = merge_audit_log_capabilities(req, body, domain=domain)
    req = merge_message_template_capabilities(req, body, domain=domain)
    req = merge_code_qr_capabilities(req, body, domain=domain)
    req = merge_staff_roster_capabilities(req, body, domain=domain)
    req = merge_room_equipment_capabilities(req, body, domain=domain)
    req = merge_book_hold_capabilities(req, body, domain=domain)
    req = merge_post_mute_capabilities(req, body, domain=domain)
    req = merge_book_suggest_capabilities(req, body, domain=domain)
    req = merge_product_spec_capabilities(req, body, domain=domain)
    req = merge_recommend_capabilities(req, body)
    req = merge_time_conflict_capabilities(req, body)
    req = merge_loan_deadline_capabilities(req, body)
    req = merge_loan_renew_capabilities(req, body, domain=domain)
    req = merge_waitlist_capabilities(req, body, domain=domain)
    return req
