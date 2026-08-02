"""泳道 E · C-10：通用口令签到；P-22 挂 DOM-CHECKIN（登记→审→签→缺勤）。"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from typing import Any

from app.bake.capabilities import CAPABILITIES
from app.bake.catalog import match_text
from app.bake.domain_schema import attach_accept, build_domain_schema, validate_schema
from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
from app.bake.engine_sql import domain_sql
from app.bake.sql.fragments import _ticket_flag_column_names


def noshow_should_mark(
    *,
    status: str,
    checked_in_at: str | None,
    end_at: datetime | None,
    now: datetime,
    no_show_after_end: bool = True,
    allow_checkin: bool = True,
) -> bool:
    """与 TicketStatusOps.refreshNoShow 同条件（Python 侧可验收契约）。"""
    if not (no_show_after_end and allow_checkin):
        return False
    if status != "approved":
        return False
    if checked_in_at is not None and str(checked_in_at).strip():
        return False
    if end_at is None:
        return False
    return now > end_at


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
        # ACTIVITY 仍走报名审核，勿被查寝改动带偏
        self.assertFalse(ticket.get("autoApprove"))
        self.assertEqual((ticket.get("states") or {}).get("overdue"), "爽约")

    def test_checkin_schema_and_sql(self) -> None:
        schema = build_domain_schema("高校宿舍查寝归寝签到管理系统", "DOM-CHECKIN")
        ok, errs = validate_schema(schema)
        self.assertTrue(ok, errs[:5])
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("allowCheckin"))
        self.assertFalse(ticket.get("autoApprove"))
        self.assertTrue(ticket.get("noShowAfterEnd"))
        self.assertEqual(ticket.get("checkinLabel"), "归寝签到")
        states = ticket.get("states") or {}
        self.assertEqual(states.get("pending"), "待审")
        self.assertEqual(states.get("approved"), "签到中")
        self.assertEqual(states.get("returned"), "已签到")
        self.assertEqual(states.get("overdue"), "缺勤")
        verbs = ticket.get("verbs") or {}
        self.assertEqual(verbs.get("apply"), "归寝登记")
        self.assertNotEqual(verbs.get("return"), "取消签到")
        admin_keys = {m.get("key") for m in (schema.get("menus") or {}).get("admin") or []}
        self.assertIn("ticket_pending", admin_keys)
        pending = next(
            m for m in (schema.get("menus") or {}).get("admin") or [] if m.get("key") == "ticket_pending"
        )
        self.assertEqual(pending.get("label"), "归寝审核")
        self.assertNotIn("缺勤调剂", str(schema))
        self.assertNotIn("取消签到", str(schema))
        self.assertNotIn("提交即记已签到", str((schema.get("labels") or {}).get("authLead") or ""))
        archive = (schema.get("entities") or {}).get("archive") or {}
        keys = {f.get("key") for f in (archive.get("fields") or []) if isinstance(f, dict)}
        self.assertIn("checkinCode", keys)
        self.assertIn("startAt", keys)
        self.assertIn("endAt", keys)
        stock = next(f for f in (archive.get("fields") or []) if f.get("key") == "stock")
        self.assertEqual(stock.get("label"), "应签人数")
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
        self.assertIn("归寝登记", sql)
        self.assertNotIn("演示", sql)

    def test_attach_accept_review_gated_checkin(self) -> None:
        title = "高校宿舍查寝归寝签到管理系统"
        spec: dict[str, Any] = {
            "title": title,
            "domain": "DOM-CHECKIN",
            "archetype": "ARCH-FLOW",
            "schema": build_domain_schema(title, "DOM-CHECKIN"),
        }
        out = attach_accept(spec, "宿舍查寝归寝签到缺勤记录；归寝登记审核后口令签到")
        ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(ticket.get("autoApprove"))
        self.assertTrue(ticket.get("allowCheckin"))
        self.assertTrue(ticket.get("noShowAfterEnd"))

    def test_noshow_after_end_marks_absence(self) -> None:
        end = datetime(2026, 8, 1, 23, 0, 0)
        # 窗内有单不签 → 过 endAt 变缺勤
        self.assertTrue(
            noshow_should_mark(
                status="approved",
                checked_in_at=None,
                end_at=end,
                now=end + timedelta(minutes=1),
            )
        )
        # 窗内尚未结束 → 不缺勤
        self.assertFalse(
            noshow_should_mark(
                status="approved",
                checked_in_at=None,
                end_at=end,
                now=end - timedelta(minutes=1),
            )
        )
        # 签成功不进缺勤
        self.assertFalse(
            noshow_should_mark(
                status="approved",
                checked_in_at="2026-08-01 22:30:00",
                end_at=end,
                now=end + timedelta(hours=1),
            )
        )
        # 已签到终态（returned）不二次记缺勤
        self.assertFalse(
            noshow_should_mark(
                status="returned",
                checked_in_at="2026-08-01 22:30:00",
                end_at=end,
                now=end + timedelta(hours=1),
            )
        )
        # 待审未通过 → 不记缺勤（须先审到签到中）
        self.assertFalse(
            noshow_should_mark(
                status="pending",
                checked_in_at=None,
                end_at=end,
                now=end + timedelta(hours=1),
            )
        )

    def test_p22_hits_checkin_not_neighbors(self) -> None:
        got = match_text("基于 Spring Boot 的宿舍查寝归寝签到缺勤记录系统的设计与实现")
        self.assertEqual(got.domain, "DOM-CHECKIN", f"hits={got.hits[:10]}")
        oom = DOMAINS["DOM-CHECKIN"].get("out_of_mvp") or []
        self.assertIn("人脸签到", oom)
        self.assertIn("GPS轨迹打卡", oom)


if __name__ == "__main__":
    unittest.main()
