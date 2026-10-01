"""报名/申请组 apply_thicken：须知勾选、驳回文案、站内信、失物下架/到期、浅档案字段。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.apply_thicken import APPLY_DOMAINS
from app.bake.ticket_policy import policy_preview
from app.bake.sql.fragments import ensure_apply_archive_columns


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


class ApplyThickenFeatureTests(unittest.TestCase):
    def test_activity_core_defaults(self) -> None:
        out = _spec("DOM-ACTIVITY", "校园活动报名系统", "")
        schema = out.get("schema") or {}
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        archive = (schema.get("entities") or {}).get("archive") or {}
        thicken = schema.get("applyThicken") or {}
        labels = schema.get("labels") or {}
        self.assertTrue(ticket.get("applyThicken"))
        self.assertTrue(thicken.get("core"))
        self.assertTrue(ticket.get("requireNoticeAck"))
        self.assertTrue(ticket.get("notifyOnApplySuccess"))
        self.assertTrue(ticket.get("allowBatchHire"))
        self.assertTrue(ticket.get("requireInsuranceAck"))
        self.assertEqual(int(ticket.get("cancelBeforeHours") or 0), 24)
        self.assertIn("noticeAckLabel", labels)
        self.assertIn("rejectReasonRequired", labels)
        self.assertIn("applySuccessInboxTitle", labels)
        self.assertIn("stockTightHint", labels)
        self.assertIn("batchHireLabel", labels)
        self.assertIn("cancelBeforeHint", labels)
        self.assertIn("waitlistPromoteHint", labels)
        self.assertIn("insuranceAckLabel", labels)
        self.assertTrue(ticket.get("requireApplyInvite"))
        self.assertTrue(ticket.get("allowDeposit"))
        self.assertTrue(ticket.get("bedConstraint"))
        self.assertTrue(thicken.get("applyInvite"))
        self.assertTrue(thicken.get("feeDemo"))
        self.assertTrue(thicken.get("gradeLimit"))
        self.assertTrue(thicken.get("sessionGroup"))
        self.assertTrue(ticket.get("requirePriceNoteAck"))
        self.assertTrue(ticket.get("requireSponsorAck"))
        self.assertTrue(thicken.get("priceNoteAck"))
        self.assertTrue(thicken.get("sponsorAck"))
        self.assertTrue(ticket.get("allowLateMinutes"))
        self.assertTrue(thicken.get("lateMinutes"))
        self.assertIn("applyInviteLabel", labels)
        self.assertIn("applyInviteHint", labels)
        self.assertIn("depositLabel", labels)
        self.assertIn("sessionGroupHint", labels)
        self.assertIn("priceNoteAckLabel", labels)
        self.assertIn("sponsorAckLabel", labels)
        self.assertIn("lateMinutesLabel", labels)
        self.assertTrue(thicken.get("batchApprove"))
        self.assertTrue(thicken.get("cancelBeforeHours"))
        self.assertTrue(thicken.get("safetyAck"))
        self.assertEqual(int(schema.get("stockTightBelow") or 0), 3)
        keys = {f.get("key") for f in (archive.get("fields") or []) if isinstance(f, dict)}
        self.assertIn("checkinPlace", keys)
        self.assertIn("sessionGroup", keys)
        self.assertIn("applyInviteCode", keys)
        self.assertIn("sponsorNote", keys)
        self.assertIn("groupPriceNote", keys)
        self.assertIn("allowedGrades", keys)
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-ACTIVITY", out) + policy_preview(
            "DOM-ACTIVITY", out
        )
        self.assertIn("ticket-apply-thicken: true", yml)
        self.assertIn("ticket-require-notice-ack: true", yml)
        self.assertIn("ticket-notify-on-apply-success: true", yml)
        self.assertIn("ticket-cancel-before-hours: 24", yml)
        self.assertIn("ticket-require-insurance-ack: true", yml)
        self.assertIn("ticket-require-apply-invite: true", yml)
        self.assertIn("ticket-allow-deposit: true", yml)
        self.assertIn("ticket-bed-constraint: true", yml)
        self.assertIn("ticket-require-price-note-ack: true", yml)
        self.assertIn("ticket-require-sponsor-ack: true", yml)
        self.assertIn("ticket-allow-late-minutes: true", yml)

    def test_lost_claim_and_expire(self) -> None:
        out = _spec("DOM-LOST", "校园失物招领", "")
        schema = out.get("schema") or {}
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        archive = (schema.get("entities") or {}).get("archive") or {}
        thicken = schema.get("applyThicken") or {}
        labels = schema.get("labels") or {}
        self.assertTrue(ticket.get("requireNoticeAck"))
        self.assertTrue(ticket.get("preferredSlot"))
        self.assertTrue(ticket.get("allowMeetingPlace"))
        self.assertTrue(ticket.get("allowBatchHire"))
        self.assertEqual(int(ticket.get("claimCooldownHours") or 0), 2)
        self.assertTrue(thicken.get("claimAutoOff"))
        self.assertTrue(thicken.get("expireOff"))
        self.assertTrue(thicken.get("bountyNote"))
        self.assertTrue(thicken.get("claimCooldown"))
        self.assertIn("claimAutoOffHint", labels)
        self.assertIn("expireOffHint", labels)
        self.assertIn("meetingPlaceLabel", labels)
        self.assertTrue(ticket.get("requireMeetingAck"))
        self.assertTrue(thicken.get("lostCategory"))
        self.assertTrue(thicken.get("viewCount"))
        self.assertTrue(thicken.get("meetingAck"))
        self.assertTrue(ticket.get("allowDeposit"))
        self.assertTrue(thicken.get("claimDeposit"))
        self.assertTrue(thicken.get("claimMaterial"))
        self.assertIn("material_check", out.get("capabilities") or [])
        self.assertTrue(ticket.get("requireMaterialChecklist"))
        self.assertIn("meetingAckLabel", labels)
        self.assertIn("ownerMeetingAckLabel", labels)
        self.assertIn("depositLabel", labels)
        keys = {f.get("key") for f in (archive.get("fields") or []) if isinstance(f, dict)}
        self.assertIn("expireOn", keys)
        self.assertIn("bountyNote", keys)
        self.assertIn("stage", keys)
        self.assertIn("lostCategory", keys)
        self.assertIn("viewCount", keys)
        self.assertIn("feeYuan", keys)
        yml = policy_preview("DOM-LOST", out)
        self.assertIn("ticket-claim-cooldown-hours: 2", yml)
        self.assertIn("ticket-require-meeting-ack: true", yml)
        self.assertIn("ticket-allow-deposit: true", yml)

    def test_course_textbook(self) -> None:
        out = _spec("DOM-COURSE", "公选课选课系统", "")
        schema = out.get("schema") or {}
        archive = (schema.get("entities") or {}).get("archive") or {}
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        thicken = schema.get("applyThicken") or {}
        labels = schema.get("labels") or {}
        keys = {f.get("key") for f in (archive.get("fields") or []) if isinstance(f, dict)}
        self.assertIn("textbook", keys)
        self.assertIn("courseKind", keys)
        self.assertIn("prereqCode", keys)
        self.assertTrue(ticket.get("requireNoticeAck"))
        self.assertTrue(ticket.get("notifyOnApplySuccess"))
        self.assertTrue(ticket.get("allowBatchHire"))
        self.assertEqual(int(ticket.get("semesterCreditCap") or 0), 30)
        self.assertEqual(int(ticket.get("creditWarnRemaining") or 0), 4)
        self.assertEqual(int(ticket.get("maxDropTimes") or 0), 3)
        self.assertTrue(thicken.get("creditCap"))
        self.assertTrue(thicken.get("maxDrop"))
        self.assertTrue(thicken.get("prereqHint"))
        self.assertTrue(thicken.get("courseKind"))
        self.assertIn("creditCapHint", labels)
        self.assertIn("creditWarnHint", labels)
        self.assertIn("maxDropHint", labels)
        self.assertIn("prereqHint", labels)
        self.assertIn("courseKindHint", labels)
        self.assertTrue(ticket.get("bedConstraint"))
        self.assertTrue(thicken.get("college"))
        self.assertTrue(thicken.get("planUrl"))
        self.assertTrue(thicken.get("gradeLimit"))
        self.assertTrue(ticket.get("requirePlanAck"))
        self.assertTrue(thicken.get("planAck"))
        self.assertTrue(ticket.get("requirePrereqAck"))
        self.assertTrue(thicken.get("prereqHard"))
        self.assertIn("collegeFilterHint", labels)
        self.assertIn("planUrlHint", labels)
        self.assertIn("planAckLabel", labels)
        self.assertIn("prereqAckLabel", labels)
        self.assertIn("college", keys)
        self.assertIn("planUrl", keys)
        self.assertIn("allowedGrades", keys)
        yml = policy_preview("DOM-COURSE", out)
        self.assertIn("ticket-semester-credit-cap: 30", yml)
        self.assertIn("ticket-credit-warn-remaining: 4", yml)
        self.assertIn("ticket-max-drop-times: 3", yml)
        self.assertIn("ticket-bed-constraint: true", yml)
        self.assertIn("ticket-require-plan-ack: true", yml)
        self.assertIn("ticket-require-prereq-ack: true", yml)

    def test_tour_fields_and_emergency(self) -> None:
        out = _spec("DOM-TOUR", "旅行社线路报名", "")
        schema = out.get("schema") or {}
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        archive = (schema.get("entities") or {}).get("archive") or {}
        thicken = schema.get("applyThicken") or {}
        labels = schema.get("labels") or {}
        self.assertTrue(ticket.get("allowEmergencyContact"))
        self.assertTrue(ticket.get("requireInsuranceAck"))
        self.assertTrue(ticket.get("allowBatchHire"))
        self.assertIn("emergencyContactLabel", labels)
        self.assertIn("insuranceAckLabel", labels)
        self.assertIn("minGroupHint", labels)
        self.assertTrue(ticket.get("allowWaitlist"))
        self.assertTrue(ticket.get("allowDeposit"))
        self.assertTrue(thicken.get("tourWaitlist"))
        self.assertTrue(thicken.get("feeDemo"))
        self.assertTrue(thicken.get("singleRoomNote"))
        self.assertTrue(thicken.get("tourRosterExport"))
        self.assertTrue(ticket.get("requirePriceNoteAck"))
        self.assertTrue(thicken.get("priceNoteAck"))
        self.assertTrue(ticket.get("ageConstraint"))
        self.assertTrue(thicken.get("ageLimit"))
        self.assertTrue(thicken.get("tourMaterial"))
        self.assertTrue(thicken.get("insuranceExport"))
        self.assertIn("material_check", out.get("capabilities") or [])
        self.assertTrue(ticket.get("requireMaterialChecklist"))
        self.assertIn("depositLabel", labels)
        self.assertIn("priceNoteAckLabel", labels)
        self.assertIn("waitlistPromoteHint", labels)
        keys = {f.get("key") for f in (archive.get("fields") or []) if isinstance(f, dict)}
        self.assertIn("dayItinerary", keys)
        self.assertIn("leaderContact", keys)
        self.assertIn("meetingPoint", keys)
        self.assertIn("minGroupSize", keys)
        self.assertIn("singleRoomNote", keys)
        self.assertIn("groupPriceNote", keys)
        self.assertIn("minAge", keys)
        self.assertIn("maxAge", keys)
        yml = policy_preview("DOM-TOUR", out)
        self.assertIn("ticket-allow-emergency-contact: true", yml)
        self.assertIn("ticket-require-insurance-ack: true", yml)
        self.assertIn("ticket-allow-waitlist: true", yml)
        self.assertIn("ticket-allow-deposit: true", yml)
        self.assertIn("ticket-require-price-note-ack: true", yml)
        self.assertIn("ticket-age-constraint: true", yml)

    def test_non_apply_domain_skips(self) -> None:
        out = _spec("DOM-LIBRARY", "图书借阅", "")
        schema = out.get("schema") or {}
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertFalse(ticket.get("applyThicken"))
        self.assertNotIn("applyThicken", schema)

    def test_domain_sql_has_apply_cols(self) -> None:
        for domain in sorted(APPLY_DOMAINS):
            out = _spec(domain, f"{domain} 报名", "")
            ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
            text = domain_sql(
                domain,
                "db_test",
                capabilities=list(out.get("capabilities") or []),
                title="报名",
                ticket_flags=ticket,
            )
            self.assertIn("notice_ack", text)
            if domain == "DOM-ACTIVITY":
                self.assertIn("checkin_place", text)
                self.assertIn("session_group", text)
                self.assertIn("apply_invite_code", text)
                self.assertIn("deposit_yuan", text)
                self.assertIn("price_note_ack", text)
                self.assertIn("sponsor_ack", text)
                self.assertIn("late_minutes", text)
            if domain == "DOM-LOST":
                self.assertIn("expire_on", text)
                self.assertIn("bounty_note", text)
                self.assertIn("lost_category", text)
                self.assertIn("view_count", text)
                self.assertIn("meeting_ack", text)
                self.assertIn("deposit_yuan", text)
                self.assertIn("fee_yuan", text)
            if domain == "DOM-COURSE":
                self.assertIn("textbook", text)
                self.assertIn("course_kind", text)
                self.assertIn("prereq_code", text)
                self.assertIn("college", text)
                self.assertIn("plan_url", text)
                self.assertIn("plan_ack", text)
                self.assertIn("prereq_ack", text)
            if domain == "DOM-TOUR":
                self.assertIn("day_itinerary", text)
                self.assertIn("leader_contact", text)
                self.assertIn("meeting_point", text)
                self.assertIn("min_group_size", text)
                self.assertIn("emergency_contact", text)
                self.assertIn("single_room_note", text)
                self.assertIn("deposit_yuan", text)
                self.assertIn("price_note_ack", text)
                self.assertIn("min_age", text)
                self.assertIn("max_age", text)

    def test_ensure_apply_archive_columns_injects(self) -> None:
        raw = (
            "CREATE TABLE IF NOT EXISTS lost_item (\n"
            "  id BIGINT PRIMARY KEY AUTO_INCREMENT,\n"
            "  title VARCHAR(200) NOT NULL,\n"
            "  stock INT DEFAULT 1\n"
            ");\n"
        )
        out = ensure_apply_archive_columns(raw, domain="DOM-LOST", item_table="lost_item")
        self.assertIn("expire_on", out)
        self.assertIn("bounty_note", out)
        self.assertIn("stage", out)
        self.assertIn("lost_category", out)
        self.assertIn("view_count", out)


if __name__ == "__main__":
    unittest.main()
