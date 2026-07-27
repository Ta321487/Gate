"""域实体命名单一真源：档案表 / 单据表 / 外键列。

domains.runtime、ticket_columns、SQL bake 均应对齐本表；勿再平行手抄。
注意：EVENT 档案表为 event_case，但单据外键历史名为 event_id（非 event_case_id）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DomainEntity:
    """薄域主数据与单据表命名。"""

    archive_table: str | None = None
    ticket_table: str | None = None
    # None = standalone（无档案外键）；缺省非 standalone 时用 item_id
    item_fk: str | None = None
    ticket_mode: str | None = None  # archive | standalone
    standalone: bool = False


# 全具名域 + GENERIC；表名须与 SQL 模板 / schema archive_key·ticket_key 一致
DOMAIN_ENTITIES: dict[str, DomainEntity] = {
    "DOM-LIBRARY": DomainEntity("book", "borrow", "book_id", "archive"),
    "DOM-EQUIP": DomainEntity("equip", "loan", "equip_id", "archive"),
    "DOM-ASSET": DomainEntity("asset", "requisition", "asset_id", "archive"),
    "DOM-CRM": DomainEntity("customer", "follow_up", "customer_id", "archive"),
    "DOM-EVENT": DomainEntity("event_case", "event_report", "event_id", "archive"),
    "DOM-ATTEND": DomainEntity("staff_person", "leave_req", "staff_person_id", "archive"),
    "DOM-FUND": DomainEntity("fund_program", "fund_apply", "fund_program_id", "archive"),
    "DOM-LABSAFE": DomainEntity("lab_room", "access_apply", "lab_room_id", "archive"),
    "DOM-RECRUIT": DomainEntity("job_post", "job_apply", "job_post_id", "archive"),
    "DOM-DATING": DomainEntity("dating_profile", "match_apply", "dating_profile_id", "archive"),
    "DOM-GRADE": DomainEntity("course_item", "grade_apply", "course_item_id", "archive"),
    "DOM-INTERN": DomainEntity("intern_post", "week_report", "intern_post_id", "archive"),
    "DOM-PARCEL": DomainEntity("parcel", "parcel_claim", "parcel_id", "archive"),
    "DOM-SEAL": DomainEntity("seal_item", "seal_apply", "seal_item_id", "archive"),
    "DOM-FLEET": DomainEntity("fleet_vehicle", "fleet_apply", "fleet_vehicle_id", "archive"),
    "DOM-CERT": DomainEntity("cert_type", "cert_apply", "cert_type_id", "archive"),
    "DOM-PROMO": DomainEntity("promo_matter", "promo_apply", "promo_matter_id", "archive"),
    "DOM-FITOUT": DomainEntity("fitout_site", "fitout_apply", "fitout_site_id", "archive"),
    "DOM-ACAD": DomainEntity("acad_matter", "acad_apply", "acad_matter_id", "archive"),
    "DOM-TRIP": DomainEntity("trip_matter", "trip_apply", "trip_matter_id", "archive"),
    "DOM-EXPENSE": DomainEntity("expense_project", "expense_apply", "expense_project_id", "archive"),
    "DOM-CREDIT": DomainEntity("credit_item", "credit_apply", "credit_item_id", "archive"),
    "DOM-LABOR": DomainEntity("labor_item", "labor_apply", "labor_item_id", "archive"),
    "DOM-EVAL": DomainEntity("eval_course", "eval_sheet", "eval_course_id", "archive"),
    "DOM-MORAL": DomainEntity("moral_item", "moral_apply", "moral_item_id", "archive"),
    "DOM-AWARD": DomainEntity("award_item", "award_apply", "award_item_id", "archive"),
    "DOM-BED": DomainEntity("bed", "bed_apply", "bed_id", "archive"),
    "DOM-CHECKIN": DomainEntity("dorm_room", "checkin_apply", "dorm_room_id", "archive"),
    "DOM-MUTUAL-TUTOR": DomainEntity("tutor", "tutor_wish", "tutor_id", "archive"),
    "DOM-MUTUAL-TOPIC": DomainEntity("thesis_topic", "topic_wish", "thesis_topic_id", "archive"),
    "DOM-MUTUAL-TEAM": DomainEntity("team_profile", "team_wish", "team_profile_id", "archive"),
    "DOM-VISITOR": DomainEntity("visit_zone", "visitor_apply", "visit_zone_id", "archive"),
    "DOM-CARPASS": DomainEntity("pass_zone", "carpass_apply", "pass_zone_id", "archive"),
    "DOM-LISTING": DomainEntity("listing", "listing_follow", "listing_id", "archive"),
    "DOM-PROCURE": DomainEntity("procure_item", "procure_apply", "procure_item_id", "archive"),
    "DOM-CLUB": DomainEntity("club_item", "club_apply", "club_item_id", "archive"),
    "DOM-PROJ": DomainEntity("proj_item", "proj_apply", "proj_item_id", "archive"),
    "DOM-ETHIC": DomainEntity("ethic_item", "ethic_apply", "ethic_item_id", "archive"),
    "DOM-PARTY": DomainEntity("party_stage", "party_apply", "party_stage_id", "archive"),
    "DOM-CONTRACT": DomainEntity("contract_type", "contract_apply", "contract_type_id", "archive"),
    "DOM-INSTRUMENT": DomainEntity("instrument", "instrument_loan", "instrument_id", "archive"),
    "DOM-EXAM": DomainEntity("exam_subject", None, "exam_subject_id"),
    "DOM-SURVEY": DomainEntity("survey_form", None, "survey_form_id"),
    "DOM-VOTE": DomainEntity("vote_campaign", None, "vote_campaign_id"),
    "DOM-DOCLIB": DomainEntity("doc_item", None, "doc_item_id"),
    "DOM-CARPOOL": DomainEntity("trip_route", "carpool_intent", "trip_route_id", "archive"),
    "DOM-TIMEBANK": DomainEntity("tb_service", "tb_redeem", "book_id", "archive"),
    "DOM-CINEMA": DomainEntity("cinema_show", None, "item_id"),
    "DOM-ACTIVITY": DomainEntity("activity", "signup", "activity_id", "archive"),
    "DOM-LOST": DomainEntity("lost_item", "claim", "lost_item_id", "archive"),
    "DOM-COURSE": DomainEntity("course", "enrollment", "course_id", "archive"),
    "DOM-FORUM": DomainEntity("post", "reply", "post_id", "archive"),
    "DOM-MEDIA": DomainEntity("media", None, "media_id"),
    "DOM-MUSIC": DomainEntity("track", None, "track_id"),
    "DOM-BLOG": DomainEntity("article", None, "article_id"),
    "DOM-SHOP": DomainEntity("product", None, "item_id"),
    "DOM-FOOD": DomainEntity("dish", None, "item_id"),
    "DOM-HOSPITAL": DomainEntity("doctor", None, "item_id"),
    "DOM-PARKING": DomainEntity("space", None, "item_id"),
    "DOM-MEETING": DomainEntity("room", None, "item_id"),
    "DOM-SALON": DomainEntity("service", None, "item_id"),
    "DOM-HOTEL": DomainEntity("room_type", None, "item_id"),
    "DOM-DORM": DomainEntity(None, "repair", None, "standalone", standalone=True),
    "DOM-PROPERTY": DomainEntity(None, "ticket", None, "standalone", standalone=True),
    "DOM-IT": DomainEntity(None, "ticket", None, "standalone", standalone=True),
    "DOM-GENERIC": DomainEntity(None, None, "item_id"),
}

TICKET_STANDALONE_DOMAINS = frozenset(
    d for d, e in DOMAIN_ENTITIES.items() if e.standalone
)


def entity_for(domain: str) -> DomainEntity | None:
    return DOMAIN_ENTITIES.get((domain or "").strip())


def ticket_item_fk_for(domain: str) -> str | None:
    """archive 模式返回外键列名；standalone 返回 None；未知域默认 item_id。"""
    d = (domain or "").strip()
    ent = DOMAIN_ENTITIES.get(d)
    if ent is None:
        return "item_id"
    if ent.standalone:
        return None
    return ent.item_fk if ent.item_fk is not None else "item_id"


def archive_table_for(domain: str) -> str | None:
    ent = entity_for(domain)
    return ent.archive_table if ent else None


def ticket_table_for(domain: str) -> str | None:
    ent = entity_for(domain)
    return ent.ticket_table if ent else None


def bind_runtime_tables(domains: dict[str, Any]) -> None:
    """用本表覆盖 domains[*].runtime 的表名 / ticket_mode（单一真源）。"""
    for dom, meta in domains.items():
        ent = DOMAIN_ENTITIES.get(dom)
        if not ent or not isinstance(meta, dict):
            continue
        rt = meta.setdefault("runtime", {})
        if not isinstance(rt, dict):
            continue
        if ent.ticket_mode:
            rt["ticket_mode"] = ent.ticket_mode
        if ent.archive_table:
            rt["archive_item_table"] = ent.archive_table
        if ent.ticket_table:
            rt["ticket_table"] = ent.ticket_table
