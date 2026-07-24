"""各具名域 Domain Schema builder（再导出）。

实现见 builders_archive / builders_slot / builders_content / builders_ticket。
"""

from __future__ import annotations

from app.bake.schema.builders_archive import (  # noqa: F401
    _activity_schema,
    _asset_schema,
    _attend_schema,
    _course_schema,
    _crm_schema,
    _equip_schema,
    _event_schema,
    _fund_schema,
    _grade_schema,
    _intern_schema,
    _labsafe_schema,
    _library_schema,
    _lost_schema,
    _parcel_schema,
    _recruit_schema,
)
from app.bake.schema.builders_content import (  # noqa: F401
    _blog_schema,
    _forum_schema,
    _media_schema,
    _music_schema,
)
from app.bake.schema.builders_slot import (  # noqa: F401
    _food_schema,
    _hospital_schema,
    _hotel_schema,
    _meeting_schema,
    _parking_schema,
    _salon_schema,
    _shop_schema,
)
from app.bake.schema.builders_ticket import (  # noqa: F401
    _dorm_schema,
    _it_schema,
    _property_schema,
)

__all__ = [
    "_library_schema",
    "_equip_schema",
    "_asset_schema",
    "_crm_schema",
    "_event_schema",
    "_attend_schema",
    "_fund_schema",
    "_labsafe_schema",
    "_recruit_schema",
    "_grade_schema",
    "_intern_schema",
    "_parcel_schema",
    "_activity_schema",
    "_lost_schema",
    "_course_schema",
    "_shop_schema",
    "_food_schema",
    "_meeting_schema",
    "_hospital_schema",
    "_parking_schema",
    "_salon_schema",
    "_hotel_schema",
    "_media_schema",
    "_music_schema",
    "_forum_schema",
    "_blog_schema",
    "_dorm_schema",
    "_property_schema",
    "_it_schema",
]
