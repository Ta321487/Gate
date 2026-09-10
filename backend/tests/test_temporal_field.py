"""日历字段精度：默认 date；开题强调时分才 datetime。"""

from __future__ import annotations

import unittest

from app.bake.features.temporal_field import (
    apply_soft_calendar_types,
    calendar_field_type,
    scan_clock_emphasis,
)
from app.bake.schema.builders_slot import _shop_schema
from app.bake.schema.templates import SCHEMA_BUILDERS


class TemporalFieldTests(unittest.TestCase):
    def test_default_is_date(self) -> None:
        self.assertFalse(scan_clock_emphasis(""))
        self.assertFalse(scan_clock_emphasis("设置报名截止日期，过期不可再报。"))
        self.assertEqual(calendar_field_type("设置报名截止日期"), "date")

    def test_clock_emphasis_upgrades(self) -> None:
        self.assertTrue(scan_clock_emphasis("报名须在截止到 18 点前提交。"))
        self.assertTrue(scan_clock_emphasis("开抢时间为每天 10:00。"))
        self.assertEqual(calendar_field_type("截止到18点前完成申报"), "datetime")
        self.assertEqual(calendar_field_type("", clock_inherent=True), "datetime")

    def test_soft_fields_default_date_in_builders(self) -> None:
        act = SCHEMA_BUILDERS["DOM-ACTIVITY"]("校园活动报名系统")
        fields = {f["key"]: f for f in act["entities"]["archive"]["fields"]}
        self.assertEqual(fields["startAt"]["type"], "datetime")
        self.assertEqual(fields["applyDeadlineAt"]["type"], "date")

        course = SCHEMA_BUILDERS["DOM-COURSE"]("公选课选课系统")
        cf = {f["key"]: f for f in course["entities"]["archive"]["fields"]}
        self.assertEqual(cf["applyDeadlineAt"]["type"], "date")

        lost = SCHEMA_BUILDERS["DOM-LOST"]("失物招领系统")
        lf = {f["key"]: f for f in lost["entities"]["archive"]["fields"]}
        self.assertEqual(lf["foundAt"]["type"], "date")

        farm = _shop_schema("农产品电商", "产地采摘时间规格价格简介")
        ff = {f["key"]: f for f in farm["entities"]["archive"]["fields"]}
        self.assertEqual(ff["harvestOn"]["type"], "date")

    def test_apply_soft_calendar_upgrades_deadline(self) -> None:
        schema = SCHEMA_BUILDERS["DOM-ACTIVITY"]("校园活动")
        apply_soft_calendar_types(schema, "报名截止到 18 点前须完成。")
        fields = {f["key"]: f for f in schema["entities"]["archive"]["fields"]}
        self.assertEqual(fields["applyDeadlineAt"]["type"], "datetime")
        self.assertEqual(fields["startAt"]["type"], "datetime")


if __name__ == "__main__":
    unittest.main()
