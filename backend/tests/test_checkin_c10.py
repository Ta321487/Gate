"""泳道 E · C-10：通用口令签到；P-22 挂 DOM-CHECKIN。"""

from __future__ import annotations

import unittest

from app.bake.capabilities import CAPABILITIES
from app.bake.catalog import match_text
from app.bake.domain_schema import build_domain_schema, validate_schema
from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
from app.bake.engine_sql import domain_sql
from app.bake.sql.fragments import _ticket_flag_column_names


class CheckinC10Tests(unittest.TestCase):
    def test_capability_registered(self) -> None:
        self.assertIn("checkin", CAPABILITIES)
        self.assertEqual(CAPABILITIES["checkin"]["status"], "implemented")
        self.assertIn("checkin", DOMAIN_CAPABILITIES["DOM-CHECKIN"])
        self.assertIn("checkin", DOMAIN_CAPABILITIES["DOM-ACTIVITY"])

    def test_activity_still_has_checkin_schema(self) -> None:
        schema = build_domain_schema("校园活动报名管理系统", "DOM-ACTIVITY")
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("allowCheckin"))
        self.assertTrue(ticket.get("noShowAfterEnd"))

    def test_checkin_schema_and_sql(self) -> None:
        schema = build_domain_schema("高校宿舍查寝归寝签到管理系统", "DOM-CHECKIN")
        ok, errs = validate_schema(schema)
        self.assertTrue(ok, errs[:5])
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("allowCheckin"))
        archive = (schema.get("entities") or {}).get("archive") or {}
        keys = {f.get("key") for f in (archive.get("fields") or []) if isinstance(f, dict)}
        self.assertIn("checkinCode", keys)
        self.assertIn("startAt", keys)
        self.assertIn("endAt", keys)
        names = _ticket_flag_column_names(ticket)
        self.assertIn("checked_in_at", names)
        sql = domain_sql(
            "DOM-CHECKIN",
            "t_checkin",
            title="高校宿舍查寝归寝签到管理系统",
            proposal_text="宿舍查寝归寝签到缺勤记录",
        )
        self.assertIn("checkin_code", sql)
        self.assertIn("checked_in_at", sql)
        self.assertIn("start_at", sql)
        self.assertIn("end_at", sql)
        self.assertIn("dorm_room", sql)
        self.assertIn("checkin_apply", sql)

    def test_p22_hits_checkin_not_neighbors(self) -> None:
        got = match_text("基于 Spring Boot 的宿舍查寝归寝签到缺勤记录系统的设计与实现")
        self.assertEqual(got.domain, "DOM-CHECKIN", f"hits={got.hits[:10]}")
        oom = DOMAINS["DOM-CHECKIN"].get("out_of_mvp") or []
        self.assertIn("人脸签到", oom)
        self.assertIn("GPS轨迹打卡", oom)


if __name__ == "__main__":
    unittest.main()
