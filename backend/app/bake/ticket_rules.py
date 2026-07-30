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
    "DOM-SEAL": {"max_active": 5},
    "DOM-FLEET": {"max_active": 5},
    "DOM-CERT": {"max_active": 5},
    "DOM-PROMO": {"max_active": 5},
    "DOM-FITOUT": {"max_active": 5},
    "DOM-ACAD": {"max_active": 5},
    "DOM-TRIP": {"max_active": 5},
    "DOM-EXPENSE": {"max_active": 5},
    "DOM-CREDIT": {"max_active": 8},
    "DOM-LABOR": {"max_active": 8},
    "DOM-EVAL": {"max_active": 8},
    "DOM-MORAL": {"max_active": 8},
    "DOM-AWARD": {"max_active": 8},
    "DOM-BED": {"max_active": 2},
    "DOM-CHECKIN": {"max_active": 3},
    "DOM-MUTUAL-TUTOR": {"max_active": 3},
    "DOM-MUTUAL-TOPIC": {"max_active": 3},
    "DOM-MUTUAL-TEAM": {"max_active": 3},
    "DOM-VISITOR": {"max_active": 5},
    "DOM-CARPASS": {"max_active": 5},
    "DOM-LISTING": {"max_active": 5},
    "DOM-CARPOOL": {"max_active": 5},
    "DOM-TOUR": {"max_active": 5},
    "DOM-TIMEBANK": {"max_active": 5},
    "DOM-PROCURE": {"max_active": 5},
    "DOM-CLUB": {"max_active": 5},
    "DOM-PROJ": {"max_active": 5},
    "DOM-ETHIC": {"max_active": 5},
    "DOM-PARTY": {"max_active": 5},
    "DOM-CONTRACT": {"max_active": 5},
    "DOM-INSTRUMENT": {"loan_days": 7, "max_active": 3, "fine_per_day": 0.5},
    # 独立报修 SLA：受理后起算处理时限；无罚金
    "DOM-DORM": {"loan_days": 3, "fine_per_day": 0},
    "DOM-PROPERTY": {"loan_days": 3, "fine_per_day": 0},
    "DOM-IT": {"loan_days": 2, "fine_per_day": 0},
    "DOM-RECRUIT": {"max_active": 5},
    "DOM-DATING": {"max_active": 5},
    "DOM-COURSE": {"max_active": 3},
    "DOM-ACTIVITY": {"max_active": 5},
    "DOM-FORUM": {"max_active": 50},
}


def rules_for(
    domain: str | None,
    *,
    title: str = "",
    proposal_text: str = "",
) -> dict[str, Any]:
    out = dict(TICKET_RULES_BY_DOMAIN.get(domain or "") or {})
    if domain == "DOM-PARCEL":
        from app.bake.scene_scan import scene_for

        if scene_for("DOM-PARCEL", title, proposal_text) == "community":
            out["pickup_place"] = "小区驿站前台"
    return out
