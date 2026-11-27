"""具名域按 scene 替换演示种子（表结构不变，只换人名/地点/公告）。

DOM-EVENT 仍走 ``event_scene_seed``；本模块覆盖其余易与校园模板打架的域。
种子正文在 ``general_scene_overlays`` / ``shop_scene_overlays``；
预约深皮 ``reserve_scene_overlays``；内容深皮 ``content_scene_overlays``。
"""

from __future__ import annotations

from app.bake.scene_scan import (
    activity_product_kind,
    blog_product_kind,
    crm_product_kind,
    equip_product_kind,
    food_product_kind,
    forum_product_kind,
    hospital_product_kind,
    hotel_product_kind,
    it_product_kind,
    library_product_kind,
    media_product_kind,
    meeting_product_kind,
    music_product_kind,
    parking_product_kind,
    procure_product_kind,
    property_product_kind,
    recruit_product_kind,
    salon_product_kind,
    scene_for,
    shop_product_kind,
)
from app.bake.sql import content_scene_overlays as _content
from app.bake.sql import general_scene_overlays as _gen
from app.bake.sql import reserve_scene_overlays as _rsv
from app.bake.sql import shop_scene_overlays as _shop
from app.bake.sql.scene_seed_util import (
    _CARPASS_ENTERPRISE_USER,
    _FITOUT_COMMUNITY_USER,
    _OA_ENTERPRISE_USER,
    _patch_portal_user_identity,
    _replace_user_seed_tail,
)


def apply_domain_scene_seed(
    domain: str,
    sql: str,
    *,
    title: str = "",
    proposal_text: str = "",
) -> str:
    """按 scene_for 替换演示种子；默认/校园档保留模板原文（除非另有覆盖）。"""
    if domain == "DOM-EVENT":
        from app.bake.sql.event_scene_seed import apply_event_scene_seed

        return apply_event_scene_seed(sql, title=title, proposal_text=proposal_text)

    scene = scene_for(domain, title, proposal_text)
    seed: str | None = None
    if domain == "DOM-CINEMA":
        from app.bake.scene_scan import cinema_product_kind, scan_shop_marketplace

        face = cinema_product_kind(title, proposal_text)
        if scan_shop_marketplace(title, proposal_text):
            sql = _shop._shop_sql_marketplace(sql, farm=False)
            seed = _shop._CINEMA_PERF_MP if face == "performance" else _shop._CINEMA_MP
        elif face == "performance":
            seed = _shop._CINEMA_PERF
    elif domain == "DOM-SHOP":
        from app.bake.scene_scan import shop_catalog_kind, shop_product_kind

        pk = shop_product_kind(title, proposal_text)
        ck = shop_catalog_kind(title, proposal_text)
        campus = pk == "campus"
        farm = pk == "farm"
        sql = _shop._shop_sql_condition_grade(sql, campus=campus)
        sql = _shop._shop_sql_farm_attrs(sql, farm=farm)
        seed = {
            "campus": _shop._SHOP_CAMPUS,
            "print": _shop._SHOP_PRINT,
            "farm": _shop._SHOP_FARM,
            "flowers": _shop._SHOP_FLOWERS,
            "errand": _shop._SHOP_ERRAND,
            "points": _shop._SHOP_POINTS,
        }.get(pk)
        if seed is None:
            seed = _shop._shop_retail_seed_for(ck)
        from app.bake.scene_scan import scan_shop_marketplace

        if scan_shop_marketplace(title, proposal_text):
            sql = _shop._shop_sql_marketplace(sql, farm=farm)
            # 多店种子覆盖单店种子（含店长账号与商品归属）
            if farm:
                seed = _shop._SHOP_MP_FARM
            else:
                seed = _shop._shop_mp_retail_seed_for(ck)
    elif domain == "DOM-FOOD" and food_product_kind(title, proposal_text) == "canteen":
        seed = _shop._FOOD_CANTEEN
    elif domain == "DOM-PARKING":
        if parking_product_kind(title, proposal_text) == "charge":
            seed = _rsv.PARKING_CHARGE
        elif scene == "campus":
            seed = _gen._PARKING_CAMPUS
    elif domain == "DOM-HOTEL" and hotel_product_kind(title, proposal_text) == "boarding":
        seed = _shop._HOTEL_BOARDING
    elif domain == "DOM-HOTEL" and hotel_product_kind(title, proposal_text) == "homestay":
        seed = _rsv.HOTEL_HOMESTAY
    elif domain == "DOM-ATTEND" and scene == "campus":
        seed = _gen._ATTEND_CAMPUS
    elif domain == "DOM-PARCEL" and scene == "community":
        seed = _gen._PARCEL_COMMUNITY
    elif domain == "DOM-LOST" and scene == "community":
        seed = _gen._LOST_COMMUNITY
    elif domain == "DOM-LOST" and scene == "baggage":
        seed = _gen._LOST_BAGGAGE
    elif domain == "DOM-LOST" and scene == "adopt":
        seed = _gen._LOST_ADOPT
    elif domain == "DOM-LOST" and scene == "donate":
        seed = _gen._LOST_DONATE
    elif domain == "DOM-ACTIVITY":
        ak = activity_product_kind(title, proposal_text)
        if ak == "cert":
            if any(x in (title or "") for x in ("防暴恐", "反恐", "安全培训")):
                seed = _gen._ACTIVITY_SECURITY
            else:
                seed = _gen._ACTIVITY_CERT
        elif ak == "ticket":
            seed = _gen._ACTIVITY_TICKET
        elif ak == "blood":
            seed = _gen._ACTIVITY_BLOOD
        elif ak == "camp":
            seed = _gen._ACTIVITY_CAMP
    elif domain == "DOM-PROCURE" and procure_product_kind(title, proposal_text) == "journal":
        seed = _gen._PROCURE_JOURNAL
    elif domain == "DOM-RECRUIT" and recruit_product_kind(title, proposal_text) == "witkey":
        seed = _gen._RECRUIT_WITKEY
    elif domain == "DOM-RECRUIT" and scene == "enterprise":
        seed = _gen._RECRUIT_ENTERPRISE
    elif domain == "DOM-DATING" and scene == "campus":
        seed = _gen._DATING_CAMPUS
    elif domain == "DOM-HOSPITAL":
        hk = hospital_product_kind(title, proposal_text)
        if hk == "pet":
            seed = _gen._HOSPITAL_PET
        elif hk == "vaccine":
            seed = _gen._HOSPITAL_VACCINE
        elif hk == "window":
            seed = _rsv.HOSPITAL_WINDOW
        elif hk == "visit":
            seed = _rsv.HOSPITAL_VISIT
    elif domain == "DOM-SALON":
        sk = salon_product_kind(title, proposal_text)
        if sk == "fitness":
            seed = _gen._SALON_FITNESS
        elif sk == "photo":
            seed = _gen._SALON_PHOTO
        elif sk == "counsel":
            seed = _rsv.SALON_COUNSEL
        elif sk == "drive":
            seed = _rsv.SALON_DRIVE
        elif sk == "home":
            seed = _rsv.SALON_HOME
        elif sk == "tutor":
            seed = _rsv.SALON_TUTOR
    elif domain == "DOM-FUND" and scene == "enterprise":
        seed = _gen._FUND_ENTERPRISE
    elif domain == "DOM-GRADE" and scene == "enterprise":
        seed = _gen._GRADE_ENTERPRISE
    elif domain == "DOM-INTERN" and scene == "enterprise":
        seed = _gen._INTERN_ENTERPRISE
    elif domain == "DOM-LABSAFE" and scene == "enterprise":
        seed = _gen._LABSAFE_ENTERPRISE
    elif domain == "DOM-PROPERTY":
        pk = property_product_kind(title, proposal_text)
        if pk == "municipal":
            seed = _gen._PROPERTY_MUNICIPAL
        elif pk == "complaint":
            seed = _gen._PROPERTY_COMPLAINT
        elif scene == "campus":
            seed = _gen._PROPERTY_CAMPUS
    elif domain == "DOM-CRM":
        pk = crm_product_kind(title, proposal_text)
        if pk == "legal":
            seed = _gen._CRM_LEGAL
        elif pk == "homevisit":
            seed = _gen._CRM_HOMEVISIT
        elif pk == "coop":
            seed = _gen._CRM_COOP
        elif scene == "campus":
            seed = _gen._CRM_CAMPUS
    elif domain == "DOM-LIBRARY":
        pk = library_product_kind(title, proposal_text)
        if pk == "archive":
            seed = _gen._LIBRARY_ARCHIVE
        elif pk == "drift":
            seed = _gen._LIBRARY_DRIFT
    elif domain == "DOM-EQUIP":
        seed = _gen._EQUIP_SEEDS.get(equip_product_kind(title, proposal_text))
    elif domain == "DOM-IT":
        pk = it_product_kind(title, proposal_text)
        if pk == "aftersales":
            seed = _gen._IT_AFTERSALES
        elif pk == "maintenance":
            seed = _gen._IT_MAINTENANCE
        elif scene == "enterprise":
            seed = _gen._IT_ENTERPRISE
    elif domain == "DOM-ASSET" and scene == "campus":
        seed = _gen._ASSET_CAMPUS
    elif domain == "DOM-MEETING":
        mk = meeting_product_kind(title, proposal_text)
        if mk == "exhibit":
            seed = _rsv.MEETING_EXHIBIT
        elif mk == "gym":
            seed = _rsv.MEETING_GYM
        elif scene == "campus" or mk in ("study", "piano", "seat", "lab"):
            seed = _gen._MEETING_CAMPUS
    elif domain == "DOM-FORUM":
        if forum_product_kind(title, proposal_text) == "wall":
            seed = _content.FORUM_WALL
        elif scene == "community":
            seed = _gen._FORUM_COMMUNITY
    elif domain == "DOM-MEDIA":
        mk = media_product_kind(title, proposal_text)
        if mk == "coursevod":
            seed = _content.MEDIA_COURSEVOD
        elif scene == "campus" or mk == "campus":
            seed = _gen._MEDIA_CAMPUS
    elif domain == "DOM-MUSIC":
        mk = music_product_kind(title, proposal_text)
        if mk == "karaoke":
            seed = _content.MUSIC_KARAOKE
        elif scene == "campus" or mk == "campus":
            seed = _gen._MUSIC_CAMPUS
    elif domain == "DOM-BLOG":
        bk = blog_product_kind(title, proposal_text)
        if bk == "press":
            seed = _content.BLOG_PRESS
        elif scene == "campus" or bk == "campus":
            seed = _gen._BLOG_CAMPUS
    elif domain == "DOM-TIMEBANK" and scene == "campus":
        seed = _gen._TIMEBANK_CAMPUS
    elif domain in {
        "DOM-SEAL",
        "DOM-FLEET",
        "DOM-CERT",
        "DOM-PROMO",
        "DOM-TRIP",
        "DOM-EXPENSE",
    } and scene == "enterprise":
        nick, prof = _OA_ENTERPRISE_USER
        return _patch_portal_user_identity(sql, nickname=nick, profile_json=prof)
    elif domain == "DOM-FITOUT" and scene == "community":
        nick, prof = _FITOUT_COMMUNITY_USER
        return _patch_portal_user_identity(sql, nickname=nick, profile_json=prof)
    elif domain == "DOM-FITOUT" and scene == "enterprise":
        nick, prof = _OA_ENTERPRISE_USER
        return _patch_portal_user_identity(sql, nickname=nick, profile_json=prof)
    elif domain == "DOM-CARPASS" and scene == "enterprise":
        nick, prof = _CARPASS_ENTERPRISE_USER
        return _patch_portal_user_identity(sql, nickname=nick, profile_json=prof)
    if seed is not None:
        sql = _replace_user_seed_tail(sql, seed)
    if domain == "DOM-INTERN":
        from app.bake.scene_scan import intern_post_bound

        if intern_post_bound(title, proposal_text):
            # 开题写绑岗：周报须知提示资料绑岗
            if "资料绑岗" not in sql:
                sql = sql.replace(
                    "系统要求岗位与学生绑定时，请在个人资料填写实习单位与岗位后再交周报。",
                    "本系统要求岗位与学生绑定：请先在个人资料填写实习单位与岗位（资料绑岗），仅可对本岗交周报。",
                    1,
                )
            if "资料绑岗" not in sql:
                sql = sql.replace(
                    "「实习中」仅标关联岗。",
                    "「实习中」仅标关联岗。本系统要求岗位与学生绑定：请先在个人资料填写实习单位与岗位（资料绑岗）。",
                    1,
                )
    return sql
