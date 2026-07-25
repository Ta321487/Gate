# -*- coding: utf-8 -*-
"""工厂向学生包灌入的单据业务参数（bake → thesis.ticket-*）。

学生交付物无 sys_config 表；本表是工厂侧写参的唯一来源（原 SQL 种子值上提）。
"""

from __future__ import annotations

from typing import Any

# loan_days / max_active / fine_per_day / pickup_place
# max_active：原各域 max_borrow / max_open_* / max_signup / max_enrollment / max_reply
TICKET_RULES_BY_DOMAIN: dict[str, dict[str, Any]] = {
    "DOM-LIBRARY": {"loan_days": 30, "max_active": 5, "fine_per_day": 0.5},
    "DOM-EQUIP": {"loan_days": 14, "max_active": 5, "fine_per_day": 0.5},
    "DOM-ASSET": {"max_active": 5, "pickup_place": "行政楼地下库房"},
    "DOM-LOST": {"pickup_place": "保卫处失物点"},
    "DOM-PARCEL": {"pickup_place": "东门校园驿站前台"},
    "DOM-ATTEND": {"max_active": 3},
    "DOM-CRM": {"max_active": 20},
    "DOM-INTERN": {"max_active": 4},
    "DOM-LABSAFE": {"max_active": 3},
    "DOM-EVENT": {"max_active": 20},
    "DOM-FUND": {"max_active": 3},
    "DOM-GRADE": {"max_active": 2},
    "DOM-RECRUIT": {"max_active": 5},
    "DOM-DATING": {"max_active": 5},
    "DOM-COURSE": {"max_active": 3},
    "DOM-ACTIVITY": {"max_active": 5},
    "DOM-FORUM": {"max_active": 50},
}


def rules_for(domain: str | None) -> dict[str, Any]:
    return dict(TICKET_RULES_BY_DOMAIN.get(domain or "") or {})
