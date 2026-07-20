"""学生端可见「皮肤 / 特征」：不写 DOM-* 工厂编号。"""

from __future__ import annotations

from typing import Any

# DOM → 短皮肤 id（404/500 文案桶；非工厂目录号）
_DOMAIN_FLAVOR: dict[str, str] = {
    "DOM-LIBRARY": "library",
    "DOM-EQUIP": "equipment",
    "DOM-ASSET": "asset",
    "DOM-CRM": "crm",
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


def student_skin_payload(domain: str, domain_label: str) -> dict[str, Any]:
    """写入 APP_DELIVERED 的皮肤字段（无 DOM-*）。"""
    return {
        "flavor": flavor_for_domain(domain),
        "domainLabel": domain_label or "通用",
        "traits": traits_for_domain(domain),
    }
