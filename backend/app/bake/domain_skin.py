"""学生端可见「皮肤 / 特征」：不写 DOM-* 工厂编号。"""

from __future__ import annotations

from typing import Any

# DOM → 短皮肤 id（404/500 文案桶；非工厂目录号）
_DOMAIN_FLAVOR: dict[str, str] = {
    "DOM-LIBRARY": "library",
    "DOM-EQUIP": "equipment",
    "DOM-ASSET": "asset",
    "DOM-CRM": "crm",
    "DOM-EVENT": "event",
    "DOM-ATTEND": "attend",
    "DOM-RECRUIT": "recruit",
    "DOM-GRADE": "grade",
    "DOM-INTERN": "intern",
    "DOM-PARCEL": "parcel",
    "DOM-SHOP": "shop",
    "DOM-DORM": "dorm",
    "DOM-PROPERTY": "property",
    "DOM-IT": "ithelp",
    "DOM-ACTIVITY": "activity",
    "DOM-LOST": "lostfound",
    "DOM-COURSE": "course",
    "DOM-FOOD": "food",
    "DOM-HOSPITAL": "hospital",
    "DOM-PARKING": "parking",
    "DOM-MEETING": "meeting",
    "DOM-SALON": "salon",
    "DOM-HOTEL": "hotel",
    "DOM-MEDIA": "media",
    "DOM-MUSIC": "music",
    "DOM-FORUM": "forum",
    "DOM-BLOG": "blog",
    "DOM-GENERIC": "generic",
}

# 页面分支用布尔特征（替代 getDomain() === 'DOM-…'）
_DOMAIN_TRAITS: dict[str, dict[str, bool]] = {
    "DOM-LIBRARY": {"shelfCopy": True, "loanFine": True},
    "DOM-EQUIP": {"loanFine": True},
    "DOM-ASSET": {"pickupFlow": True},
    "DOM-CRM": {"crm": True},
    "DOM-EVENT": {"crm": True},
    "DOM-ATTEND": {"crm": True},
    "DOM-RECRUIT": {"crm": True},
    "DOM-GRADE": {"crm": True},
    "DOM-INTERN": {"crm": True},
    "DOM-PARCEL": {"pickupFlow": True},
    "DOM-SHOP": {"shop": True, "addressBook": True, "shelfCopy": True},
    "DOM-FOOD": {"food": True, "addressBook": True, "shelfCopy": True},
    "DOM-LOST": {"pickupFlow": True},
    "DOM-PARKING": {"slotParking": True},
    "DOM-HOSPITAL": {"slotHospital": True},
    "DOM-MEETING": {"slotMeeting": True},
    "DOM-HOTEL": {"slotHotel": True},
    "DOM-SALON": {"slotSalon": True},
    "DOM-MEDIA": {"shelfCopy": True},
    "DOM-MUSIC": {"shelfCopy": True},
    "DOM-FORUM": {"shelfCopy": True},
    "DOM-BLOG": {"shelfCopy": True},
    "DOM-GENERIC": {"addressBook": True},
}


def flavor_for_domain(domain: str) -> str:
    return _DOMAIN_FLAVOR.get(domain) or "generic"


def traits_for_domain(domain: str) -> dict[str, bool]:
    base = dict(_DOMAIN_TRAITS.get(domain) or {})
    # 未声明的特征视为 false，不写入交付物（保持干净）
    return {k: v for k, v in base.items() if v}


# 登录氛围图 Unsplash 英文检索锚点（原 auth_hero._DOMAIN_QUERY）
_DOMAIN_AUTH_QUERY: dict[str, str] = {
    "DOM-LIBRARY": "university library books reading",
    "DOM-DORM": "university dormitory campus building",
    "DOM-PROPERTY": "residential apartment community property",
    "DOM-IT": "server room network operations campus it",
    "DOM-EQUIP": "laboratory equipment workshop",
    "DOM-ASSET": "warehouse inventory shelves",
    "DOM-CRM": "business meeting handshake office crm",
    "DOM-ATTEND": "office attendance leave request calendar desk",
    "DOM-RECRUIT": "campus job fair recruitment resume interview",
    "DOM-GRADE": "university academic transcript grades classroom",
    "DOM-INTERN": "student internship workplace mentor weekly report",
    "DOM-PARCEL": "campus parcel pickup station courier lockers",
    "DOM-EVENT": "emergency response public health report clipboard",
    "DOM-ACTIVITY": "campus event students gathering",
    "DOM-LOST": "campus corridor lost and found desk",
    "DOM-COURSE": "university classroom lecture hall",
    "DOM-SHOP": "modern retail store aisle",
    "DOM-FOOD": "campus cafeteria food counter",
    "DOM-HOSPITAL": "hospital clinic corridor",
    "DOM-PARKING": "parking garage cars",
    "DOM-MEETING": "conference meeting room",
    "DOM-SALON": "salon service studio interior",
    "DOM-HOTEL": "hotel lobby interior",
    "DOM-MEDIA": "cinema movie theater screen audience",
    "DOM-MUSIC": "headphones music vinyl record studio",
    "DOM-FORUM": "online forum discussion community bulletin board",
    "DOM-BLOG": "writing desk laptop coffee blog journal",
    "DOM-GENERIC": "modern office workspace",
}


def auth_hero_query_for(domain: str) -> str:
    return _DOMAIN_AUTH_QUERY.get(domain) or _DOMAIN_AUTH_QUERY["DOM-GENERIC"]


def student_skin_payload(domain: str, domain_label: str) -> dict[str, Any]:
    """写入 APP_DELIVERED 的皮肤字段（无 DOM-*）。"""
    return {
        "flavor": flavor_for_domain(domain),
        "domainLabel": domain_label or "通用",
        "traits": traits_for_domain(domain),
    }
