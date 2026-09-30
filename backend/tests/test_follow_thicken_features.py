"""跟进组 follow_thicken：域默认提醒/额度/评价/面试结果；扫词家访/收藏/异议等。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.follow_thicken import (
    scan_home_visit,
    scan_job_fav,
    scan_listing_fav,
    scan_onboard_mat,
)
from app.bake.sql.fragments import ensure_follow_archive_columns


def _spec(domain: str, title: str, body: str = "") -> dict:
    return attach_accept(
        {
            "domain": domain,
            "title": title,
            "capabilities": list(DOMAIN_CAPABILITIES[domain]),
            "features": [],
            "archetype": "ARCH-FLOW",
        },
        body,
    )


class FollowThickenFeatureTests(unittest.TestCase):
    def test_crm_follow_remind_and_tags(self) -> None:
        out = _spec("DOM-CRM", "客户跟进管理系统", "")
        schema = out.get("schema") or {}
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        thicken = schema.get("followThicken") or {}
        self.assertEqual(int(ticket.get("followRemindDays") or 0), 1)
        self.assertTrue(thicken.get("followRemind"))
        self.assertTrue(ticket.get("phoneDupCheck"))
        self.assertTrue(ticket.get("allowDealAmount"))
        keys = {
            f.get("key")
            for f in ((schema.get("entities") or {}).get("archive") or {}).get("fields") or []
            if isinstance(f, dict)
        }
        self.assertIn("tags", keys)
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-CRM", out)
        self.assertIn("ticket-follow-remind-days: 1", yml)
        self.assertIn("ticket-phone-dup-check: true", yml)

    def test_crm_home_visit_scan(self) -> None:
        self.assertTrue(scan_home_visit("支持家访谈话记录模板"))
        out = _spec("DOM-CRM", "学工客户跟进", "家访谈话记录与后续计划")
        ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("homeVisitTemplate"))

    def test_attend_leave_balance_default(self) -> None:
        out = _spec("DOM-ATTEND", "考勤请假管理系统", "")
        caps = out.get("capabilities") or []
        self.assertIn("balance_ledger", caps)
        schema = out.get("schema") or {}
        thicken = schema.get("followThicken") or {}
        self.assertTrue(thicken.get("leaveBalance"))
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("requireReturnDate"))
        self.assertTrue(ticket.get("attachByLeaveType"))
        labels = schema.get("labels") or {}
        self.assertEqual(labels.get("balanceUnit"), "天")

    def test_event_close_attach_default(self) -> None:
        out = _spec("DOM-EVENT", "事件上报管理系统", "")
        ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("requireCloseAttach"))
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-EVENT", out)
        self.assertIn("ticket-require-close-attach: true", yml)

    def test_recruit_interview_and_batch(self) -> None:
        out = _spec("DOM-RECRUIT", "招聘投递管理系统", "")
        ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("allowInterviewResult"))
        self.assertTrue(ticket.get("allowBatchHire"))
        keys = {
            f.get("key")
            for f in (
                ((out.get("schema") or {}).get("entities") or {}).get("archive") or {}
            ).get("fields")
            or []
            if isinstance(f, dict)
        }
        self.assertIn("expireOn", keys)

    def test_recruit_job_fav_scan(self) -> None:
        self.assertTrue(scan_job_fav("支持岗位收藏与投递进度"))
        out = _spec("DOM-RECRUIT", "校园招聘系统", "岗位收藏与收藏夹分享")
        self.assertIn("favorites", out.get("capabilities") or [])

    def test_recruit_onboard_mat_scan(self) -> None:
        self.assertTrue(scan_onboard_mat("入职材料清单必传"))
        out = _spec("DOM-RECRUIT", "招聘系统", "录用后入职材料清单勾选")
        self.assertIn("material_check", out.get("capabilities") or [])

    def test_listing_rating_and_vr(self) -> None:
        out = _spec("DOM-LISTING", "房源带看管理系统", "")
        ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("allowRating"))
        self.assertTrue(ticket.get("requireFeedbackSet"))
        keys = {
            f.get("key")
            for f in (
                ((out.get("schema") or {}).get("entities") or {}).get("archive") or {}
            ).get("fields")
            or []
            if isinstance(f, dict)
        }
        self.assertIn("vrUrl", keys)
        self.assertIn("tags", keys)
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-LISTING", out)
        self.assertIn("ticket-allow-rating: true", yml)
        self.assertIn("ticket-follow-remind-days: 1", yml)

    def test_listing_fav_scan(self) -> None:
        self.assertTrue(scan_listing_fav("房源收藏与对比"))
        out = _spec("DOM-LISTING", "二手房带看", "房源收藏与两套对比")
        self.assertIn("favorites", out.get("capabilities") or [])

    def test_intern_week_and_words(self) -> None:
        out = _spec("DOM-INTERN", "实习周报管理系统", "")
        ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("weekReportRemind"))
        self.assertTrue(ticket.get("requireAppraisal"))
        self.assertGreaterEqual(int(ticket.get("minRemarkWords") or 0), 100)
        self.assertGreaterEqual(int(ticket.get("maxReviseTimes") or 0), 1)
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-INTERN", out)
        self.assertIn("ticket-min-remark-words:", yml)
        self.assertIn("ticket-week-report-remind: true", yml)

    def test_fund_defense_and_bank_mask(self) -> None:
        out = _spec("DOM-FUND", "资助奖学金管理系统", "")
        ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("allowDefenseResult"))
        self.assertTrue(ticket.get("maskBankAccount"))
        self.assertTrue(ticket.get("allowDisburseBatch"))

    def test_grade_makeup_and_print(self) -> None:
        out = _spec("DOM-GRADE", "成绩管理系统", "")
        schema = out.get("schema") or {}
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        thicken = schema.get("followThicken") or {}
        self.assertTrue(ticket.get("allowMakeupApply"))
        self.assertTrue(thicken.get("gradePrint"))
        self.assertTrue(thicken.get("distChart"))

    def test_follow_archive_sql_inject(self) -> None:
        sql = """
CREATE TABLE IF NOT EXISTS customer (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(128) DEFAULT ''
);
"""
        out = ensure_follow_archive_columns(sql, domain="DOM-CRM", item_table="customer")
        self.assertIn("tags", out)
        self.assertIn("lead_source", out)
        skip = ensure_follow_archive_columns(sql, domain="DOM-LIBRARY", item_table="customer")
        self.assertNotIn("lead_source", skip)

    def test_domain_sql_has_follow_cols(self) -> None:
        out = _spec("DOM-CRM", "客户跟进", "")
        ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        text = domain_sql(
            "DOM-CRM",
            "db_test",
            capabilities=list(out.get("capabilities") or []),
            title="客户跟进",
            ticket_flags=ticket,
        )
        self.assertIn("deal_amount_yuan", text)
        self.assertIn("follow_soon_notified_at", text)


if __name__ == "__main__":
    unittest.main()
