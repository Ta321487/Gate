"""档案主表 author/isbn 物理列按域语义化（API 仍用逻辑键 author/isbn）。"""

from __future__ import annotations

from typing import Any

from app.bake.sql.ddl_edit import (
    map_create_table,
    rewrite_col_def,
    rewrite_insert_col_names,
    valid_ident,
)

# logical → (physical_name, ddl_type)
ArchiveCol = tuple[str, str]

# domain -> (author_phys, author_ddl, isbn_phys, isbn_ddl)
ARCHIVE_COLUMN_SPEC: dict[str, tuple[ArchiveCol, ArchiveCol]] = {
    "DOM-LIBRARY": (
        ("author", "VARCHAR(100)"),
        ("isbn", "VARCHAR(32)"),
    ),
    "DOM-EQUIP": (
        ("brand_model", "VARCHAR(100)"),
        ("asset_no", "VARCHAR(64)"),
    ),
    "DOM-ASSET": (
        ("spec_model", "VARCHAR(100)"),
        ("asset_no", "VARCHAR(64)"),
    ),
    "DOM-CRM": (
        ("contact_name", "VARCHAR(100)"),
        ("contact_note", "VARCHAR(255)"),
    ),
    "DOM-EVENT": (
        ("handler_name", "VARCHAR(100)"),
        ("case_summary", "VARCHAR(255)"),
    ),
    "DOM-ATTEND": (
        ("scope_note", "VARCHAR(100)"),
        ("apply_note", "VARCHAR(255)"),
    ),
    "DOM-FUND": (
        ("own_unit", "VARCHAR(100)"),
        ("quota_note", "VARCHAR(255)"),
    ),
    "DOM-LABSAFE": (
        ("building_lead", "VARCHAR(100)"),
        ("safety_note", "VARCHAR(255)"),
    ),
    "DOM-RECRUIT": (
        ("hire_dept", "VARCHAR(100)"),
        ("salary_note", "VARCHAR(255)"),
    ),
    "DOM-DATING": (
        ("city_name", "VARCHAR(100)"),
        ("intent_note", "VARCHAR(255)"),
    ),
    "DOM-GRADE": (
        ("teacher_name", "VARCHAR(100)"),
        ("course_code", "VARCHAR(255)"),
    ),
    "DOM-INTERN": (
        ("mentor_name", "VARCHAR(100)"),
        ("org_note", "VARCHAR(255)"),
    ),
    "DOM-PARCEL": (
        ("station_name", "VARCHAR(100)"),
        ("pickup_code", "VARCHAR(255)"),
    ),
    "DOM-SEAL": (
        ("keeper_dept", "VARCHAR(100)"),
        ("seal_scope", "VARCHAR(255)"),
    ),
    "DOM-FLEET": (
        ("driver_name", "VARCHAR(100)"),
        ("vehicle_note", "VARCHAR(255)"),
    ),
    "DOM-CERT": (
        ("issue_dept", "VARCHAR(100)"),
        ("purpose_note", "VARCHAR(255)"),
    ),
    "DOM-PROMO": (
        ("apply_unit", "VARCHAR(100)"),
        ("post_place", "VARCHAR(255)"),
    ),
    "DOM-FITOUT": (
        ("contractor", "VARCHAR(100)"),
        ("work_req", "VARCHAR(255)"),
    ),
    "DOM-ACAD": (
        ("accept_dept", "VARCHAR(100)"),
        ("material_note", "VARCHAR(255)"),
    ),
    "DOM-TRIP": (
        ("own_dept", "VARCHAR(100)"),
        ("fill_note", "VARCHAR(255)"),
    ),
    "DOM-EXPENSE": (
        ("own_dept", "VARCHAR(100)"),
        ("budget_note", "VARCHAR(255)"),
    ),
    "DOM-CREDIT": (
        ("dept_name", "VARCHAR(100)"),
        ("note_hint", "VARCHAR(255)"),
    ),
    "DOM-LABOR": (
        ("dept_name", "VARCHAR(100)"),
        ("note_hint", "VARCHAR(255)"),
    ),
    "DOM-EVAL": (
        ("lecturer_name", "VARCHAR(100)"),
        ("course_note", "VARCHAR(255)"),
    ),
    "DOM-MORAL": (
        ("dept_name", "VARCHAR(100)"),
        ("note_hint", "VARCHAR(255)"),
    ),
    "DOM-AWARD": (
        ("dept_name", "VARCHAR(100)"),
        ("note_hint", "VARCHAR(255)"),
    ),
    "DOM-BED": (
        ("building_name", "VARCHAR(100)"),
        ("layout_note", "VARCHAR(255)"),
    ),
    "DOM-CHECKIN": (
        ("building_name", "VARCHAR(100)"),
        ("room_note", "VARCHAR(255)"),
    ),
    "DOM-INSTRUMENT": (
        ("lab_name", "VARCHAR(100)"),
        ("model_note", "VARCHAR(255)"),
    ),
    "DOM-MUTUAL-TUTOR": (
        ("college_name", "VARCHAR(100)"),
        ("research_note", "VARCHAR(255)"),
    ),
    "DOM-MUTUAL-TOPIC": (
        ("college_name", "VARCHAR(100)"),
        ("research_note", "VARCHAR(255)"),
    ),
    "DOM-MUTUAL-TEAM": (
        ("college_name", "VARCHAR(100)"),
        ("skill_note", "VARCHAR(255)"),
    ),
    "DOM-VISITOR": (
        ("zone_place", "VARCHAR(100)"),
        ("receive_note", "VARCHAR(255)"),
    ),
    "DOM-CARPASS": (
        ("dept_name", "VARCHAR(100)"),
        ("note_hint", "VARCHAR(255)"),
    ),
    "DOM-LISTING": (
        ("estate_area", "VARCHAR(100)"),
        ("house_type_note", "VARCHAR(255)"),
    ),
    "DOM-PROCURE": (
        ("own_dept", "VARCHAR(100)"),
        ("item_spec", "VARCHAR(255)"),
    ),
    "DOM-CLUB": (
        ("guide_unit", "VARCHAR(100)"),
        ("matter_note", "VARCHAR(255)"),
    ),
    "DOM-PROJ": (
        ("own_unit", "VARCHAR(100)"),
        ("declare_note", "VARCHAR(255)"),
    ),
    "DOM-ETHIC": (
        ("own_unit", "VARCHAR(100)"),
        ("material_brief", "VARCHAR(255)"),
    ),
    "DOM-PARTY": (
        ("party_org", "VARCHAR(100)"),
        ("material_brief", "VARCHAR(255)"),
    ),
    "DOM-CONTRACT": (
        ("own_dept", "VARCHAR(100)"),
        ("approve_note", "VARCHAR(255)"),
    ),
    "DOM-EXAM": (
        ("course_unit", "VARCHAR(100)"),
        ("note_hint", "VARCHAR(255)"),
    ),
    "DOM-SURVEY": (
        ("publish_unit", "VARCHAR(100)"),
        ("note_hint", "VARCHAR(255)"),
    ),
    "DOM-VOTE": (
        ("host_unit", "VARCHAR(100)"),
        ("rule_note", "VARCHAR(255)"),
    ),
    "DOM-DOCLIB": (
        ("publish_unit", "VARCHAR(100)"),
        ("summary_note", "VARCHAR(255)"),
    ),
    "DOM-CARPOOL": (
        ("publisher_name", "VARCHAR(100)"),
        ("route_note", "VARCHAR(255)"),
    ),
    "DOM-TIMEBANK": (
        ("organizer", "VARCHAR(100)"),
        ("service_note", "VARCHAR(255)"),
    ),
    "DOM-CINEMA": (
        ("price_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("hall_note", "VARCHAR(128) DEFAULT ''"),
    ),
    "DOM-MEDIA": (
        ("cast_info", "VARCHAR(100)"),
        ("play_url", "VARCHAR(255)"),
    ),
    "DOM-MUSIC": (
        ("artist", "VARCHAR(100)"),
        ("play_url", "VARCHAR(255)"),
    ),
    "DOM-FORUM": (
        ("author", "VARCHAR(100)"),
        ("body_html", "TEXT"),
    ),
    "DOM-BLOG": (
        ("author", "VARCHAR(100)"),
        ("body_html", "TEXT"),
    ),
    "DOM-ACTIVITY": (
        ("organizer", "VARCHAR(100)"),
        ("venue", "VARCHAR(128)"),
    ),
    "DOM-LOST": (
        ("registrant", "VARCHAR(100)"),
        ("feature_note", "VARCHAR(255)"),
    ),
    "DOM-COURSE": (
        ("teacher", "VARCHAR(100)"),
        ("course_code", "VARCHAR(128)"),
    ),
    "DOM-TOUR": (
        ("planner", "VARCHAR(100)"),
        ("highlight_note", "VARCHAR(255)"),
    ),
    "DOM-SHOP": (
        ("price_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("sku", "VARCHAR(64) DEFAULT ''"),
    ),
    "DOM-FOOD": (
        ("price_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("spec_note", "VARCHAR(128) DEFAULT ''"),
    ),
    "DOM-PARKING": (
        ("fee_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("location_note", "VARCHAR(128) DEFAULT ''"),
    ),
    "DOM-HOSPITAL": (
        ("fee_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("title_note", "VARCHAR(128) DEFAULT ''"),
    ),
    "DOM-MEETING": (
        ("fee_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("location_note", "VARCHAR(128) DEFAULT ''"),
    ),
    "DOM-SALON": (
        ("price_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("duration_note", "VARCHAR(128) DEFAULT ''"),
    ),
    "DOM-HOTEL": (
        ("price_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("room_note", "VARCHAR(128) DEFAULT ''"),
    ),
    "DOM-CARRENT": (
        ("price_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("vehicle_note", "VARCHAR(128) DEFAULT ''"),
    ),
    "DOM-GENERIC": (
        ("subtitle", "VARCHAR(100)"),
        ("detail", "VARCHAR(255)"),
    ),
}

_GENERIC_TRADE: tuple[ArchiveCol, ArchiveCol] = (
    ("price_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
    ("sku", "VARCHAR(64) DEFAULT ''"),
)


def archive_column_spec_for(
    domain: str,
    *,
    archetypes: list[str] | None = None,
) -> tuple[ArchiveCol, ArchiveCol]:
    d = (domain or "").strip()
    if d == "DOM-GENERIC":
        arches = {a for a in (archetypes or []) if a}
        if "ARCH-TRADE" in arches:
            return _GENERIC_TRADE
        return ARCHIVE_COLUMN_SPEC["DOM-GENERIC"]
    return ARCHIVE_COLUMN_SPEC.get(
        d,
        (("subtitle", "VARCHAR(100)"), ("detail", "VARCHAR(255)")),
    )


def archive_column_payload(
    domain: str,
    *,
    archetypes: list[str] | None = None,
    item_table: str | None = None,
) -> dict[str, Any]:
    (a_name, a_ddl), (i_name, i_ddl) = archive_column_spec_for(
        domain, archetypes=archetypes
    )
    return {
        "itemTable": (item_table or "").strip(),
        "authorColumn": a_name,
        "isbnColumn": i_name,
        "authorDdl": a_ddl,
        "isbnDdl": i_ddl,
    }


def apply_archive_semantic_columns(
    sql: str,
    *,
    domain: str,
    item_table: str | None,
    archetypes: list[str] | None = None,
) -> str:
    """将档案主表物理列 author/isbn 改为域语义名，并同步 INSERT 列清单。"""
    t = (item_table or "").strip()
    if not valid_ident(t):
        return sql
    (a_name, a_ddl), (i_name, i_ddl) = archive_column_spec_for(
        domain, archetypes=archetypes
    )

    def transform(body: str) -> str:
        body = rewrite_col_def(body, "author", a_name, a_ddl)
        return rewrite_col_def(body, "isbn", i_name, i_ddl)

    out = map_create_table(sql, t, transform)
    return rewrite_insert_col_names(
        out, t, {"author": a_name, "isbn": i_name}
    )
