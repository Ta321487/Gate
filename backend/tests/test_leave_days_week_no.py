"""考勤请假天数 / 实习周报周次：域默认列 + 域内文案（读 schema.labels，不写死）。"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.bake.domain_schema import build_domain_schema
from app.bake.engine_sql import domain_sql

GOLDEN_SCHEMA = Path(__file__).resolve().parent / "golden" / "schema"


class LeaveDaysWeekNoTests(unittest.TestCase):
    def test_attend_has_leave_days_column_and_label(self) -> None:
        sql = domain_sql("DOM-ATTEND", "t_attend", title="学生请假销假")
        self.assertIn("leave_days", sql)
        self.assertNotIn("week_no", sql, "周次不该出现在考勤域")
        labels = build_domain_schema("学生请假销假管理系统", "DOM-ATTEND").get("labels") or {}
        self.assertEqual(labels.get("leaveDaysLabel"), "请假天数")
        self.assertIn("含首尾", labels.get("leaveDaysLead") or "")

    def test_intern_has_week_no_column_and_label(self) -> None:
        sql = domain_sql("DOM-INTERN", "t_intern", title="实习周报")
        self.assertIn("week_no", sql)
        self.assertNotIn("leave_days", sql, "请假天数不该出现在实习域")
        labels = build_domain_schema("顶岗实习周报管理系统", "DOM-INTERN").get("labels") or {}
        self.assertEqual(labels.get("weekNoLabel"), "周次")

    def test_golden_schema_carries_labels(self) -> None:
        attend = json.loads((GOLDEN_SCHEMA / "DOM-ATTEND.json").read_text(encoding="utf-8"))
        intern = json.loads((GOLDEN_SCHEMA / "DOM-INTERN.json").read_text(encoding="utf-8"))
        self.assertIn("leaveDaysLabel", (attend.get("labels") or {}))
        self.assertIn("weekNoLabel", (intern.get("labels") or {}))
