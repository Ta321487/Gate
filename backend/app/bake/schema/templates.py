"""Domain Schema 模板入口：壳 + 各域 builder 登记。

实现拆在：
- shells.py — 通用壳构造
- domain_builders.py — 各 DOM-* builder
- followup_presets.py — CRM/考勤等档案+跟进单预设
"""

from __future__ import annotations

from app.bake.oa_apply_meta import OA_APPLY_META
from app.bake.stuwork_meta import STUWORK_META
from app.bake.schema.followup_presets import followup_builder
from app.bake.schema.domain_builders import (  # noqa: F401
    _activity_schema,
    _asset_schema,
    _attend_schema,
    _blog_schema,
    _course_schema,
    _crm_schema,
    _dorm_schema,
    _dating_schema,
    _exam_schema,
    _survey_schema,
    _vote_schema,
    _doclib_schema,
    _equip_schema,
    _event_schema,
    _food_schema,
    _forum_schema,
    _fund_schema,
    _grade_schema,
    _hospital_schema,
    _hotel_schema,
    _intern_schema,
    _it_schema,
    _labsafe_schema,
    _library_schema,
    _lost_schema,
    _media_schema,
    _meeting_schema,
    _music_schema,
    _parcel_schema,
    _parking_schema,
    _property_schema,
    _recruit_schema,
    _salon_schema,
    _shop_schema,
    _cinema_schema,
)
from app.bake.schema.shells import (  # noqa: F401
    _SCENE_COPY_DOMAINS,
    _copy_scan_text,
    _scan_has,
    _with_portal_banners,
    archive_favorites_schema,
    archive_ticket_schema,
    category_menu_label,
    generic_schema,
    order_shell_schema,
    product_name_from_title,
    slot_shell_schema,
    standalone_ticket_schema,
)

SCHEMA_BUILDERS = {
    "DOM-LIBRARY": _library_schema,
    "DOM-EQUIP": _equip_schema,
    "DOM-ASSET": _asset_schema,
    "DOM-CRM": _crm_schema,
    "DOM-EVENT": _event_schema,
    "DOM-ATTEND": _attend_schema,
    "DOM-FUND": _fund_schema,
    "DOM-LABSAFE": _labsafe_schema,
    "DOM-RECRUIT": _recruit_schema,
    "DOM-DATING": _dating_schema,
    "DOM-GRADE": _grade_schema,
    "DOM-INTERN": _intern_schema,
    "DOM-PARCEL": _parcel_schema,
    "DOM-MEDIA": _media_schema,
    "DOM-MUSIC": _music_schema,
    "DOM-FORUM": _forum_schema,
    "DOM-BLOG": _blog_schema,
    "DOM-ACTIVITY": _activity_schema,
    "DOM-LOST": _lost_schema,
    "DOM-COURSE": _course_schema,
    "DOM-DORM": _dorm_schema,
    "DOM-PROPERTY": _property_schema,
    "DOM-IT": _it_schema,
    "DOM-SHOP": _shop_schema,
    "DOM-CINEMA": _cinema_schema,
    "DOM-FOOD": _food_schema,
    "DOM-MEETING": _meeting_schema,
    "DOM-HOSPITAL": _hospital_schema,
    "DOM-PARKING": _parking_schema,
    "DOM-SALON": _salon_schema,
    "DOM-HOTEL": _hotel_schema,
}

for _m in OA_APPLY_META:
    SCHEMA_BUILDERS[_m["domain"]] = followup_builder(_m["domain"])

for _m in STUWORK_META:
    SCHEMA_BUILDERS[_m["domain"]] = followup_builder(_m["domain"])

SCHEMA_BUILDERS["DOM-BED"] = followup_builder("DOM-BED")

SCHEMA_BUILDERS["DOM-CHECKIN"] = followup_builder("DOM-CHECKIN")

SCHEMA_BUILDERS["DOM-MUTUAL-TUTOR"] = followup_builder("DOM-MUTUAL-TUTOR")
SCHEMA_BUILDERS["DOM-MUTUAL-TOPIC"] = followup_builder("DOM-MUTUAL-TOPIC")
SCHEMA_BUILDERS["DOM-MUTUAL-TEAM"] = followup_builder("DOM-MUTUAL-TEAM")

SCHEMA_BUILDERS["DOM-VISITOR"] = followup_builder("DOM-VISITOR")

SCHEMA_BUILDERS["DOM-CARPASS"] = followup_builder("DOM-CARPASS")
SCHEMA_BUILDERS["DOM-LISTING"] = followup_builder("DOM-LISTING")
SCHEMA_BUILDERS["DOM-PROCURE"] = followup_builder("DOM-PROCURE")
SCHEMA_BUILDERS["DOM-CLUB"] = followup_builder("DOM-CLUB")
SCHEMA_BUILDERS["DOM-PROJ"] = followup_builder("DOM-PROJ")
SCHEMA_BUILDERS["DOM-ETHIC"] = followup_builder("DOM-ETHIC")
SCHEMA_BUILDERS["DOM-PARTY"] = followup_builder("DOM-PARTY")
SCHEMA_BUILDERS["DOM-CONTRACT"] = followup_builder("DOM-CONTRACT")
SCHEMA_BUILDERS["DOM-INSTRUMENT"] = followup_builder("DOM-INSTRUMENT")
SCHEMA_BUILDERS["DOM-EXAM"] = _exam_schema
SCHEMA_BUILDERS["DOM-SURVEY"] = _survey_schema
SCHEMA_BUILDERS["DOM-VOTE"] = _vote_schema
SCHEMA_BUILDERS["DOM-DOCLIB"] = _doclib_schema
SCHEMA_BUILDERS["DOM-CARPOOL"] = followup_builder("DOM-CARPOOL")
SCHEMA_BUILDERS["DOM-TIMEBANK"] = followup_builder("DOM-TIMEBANK")
