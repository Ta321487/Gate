"""预约组 reserve_thicken：R-00～R-09（含域皮与能力岛加深）。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.reserve_thicken import RESERVE_DOMAINS, ensure_reserve_thicken_sql
from app.bake.runtime_policy import collect as collect_app, render as render_app


def _spec(domain: str, title: str, body: str = "") -> dict:
    return attach_accept(
        {
            "domain": domain,
            "title": title,
            "capabilities": list(DOMAIN_CAPABILITIES[domain]),
            "features": [],
            "archetype": "ARCH-RESERVE",
        },
        body,
    )


class ReserveThickenFeatureTests(unittest.TestCase):
    def test_reserve_domains_constant(self) -> None:
        self.assertEqual(
            RESERVE_DOMAINS,
            frozenset(
                {
                    "DOM-HOSPITAL",
                    "DOM-PARKING",
                    "DOM-MEETING",
                    "DOM-SALON",
                    "DOM-HOTEL",
                    "DOM-CARRENT",
                    "DOM-INSTRUMENT",
                }
            ),
        )

    def test_trade_domains_untouched(self) -> None:
        for domain, title in (
            ("DOM-SHOP", "校园二手商城系统"),
            ("DOM-FOOD", "校园点餐配送系统"),
            ("DOM-CINEMA", "影院在线选座购票系统"),
        ):
            out = _spec(domain, title, "")
            schema = out.get("schema") or {}
            self.assertFalse(schema.get("reserveThicken"))

    def test_hospital_r01_nails(self) -> None:
        out = _spec("DOM-HOSPITAL", "医院挂号预约系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("reserveThicken") or {}
        labels = schema.get("labels") or {}
        resv = (schema.get("entities") or {}).get("reservation") or {}
        archive = (schema.get("entities") or {}).get("archive") or {}
        keys = {f.get("key") for f in (archive.get("fields") or []) if isinstance(f, dict)}

        self.assertTrue(resv.get("reserveThicken"))
        self.assertTrue(thicken.get("core"))
        self.assertTrue(thicken.get("cancelFreeHours"))
        self.assertTrue(thicken.get("rescheduleMax"))
        self.assertTrue(thicken.get("remindAhead"))
        self.assertTrue(thicken.get("noShowLimit"))
        self.assertTrue(thicken.get("successMessage"))
        self.assertTrue(thicken.get("lateCheckIn"))
        self.assertTrue(thicken.get("maintainBlock"))
        self.assertTrue(thicken.get("waitlistPromote"))
        self.assertTrue(thicken.get("calendarTone"))
        self.assertTrue(thicken.get("adminNote"))
        self.assertTrue(thicken.get("blacklist"))
        self.assertTrue(thicken.get("blacklistAppeal"))
        self.assertTrue(schema.get("reserveBlacklist"))

        self.assertGreaterEqual(int(schema.get("cancelFreeHours") or 0), 1)
        self.assertGreaterEqual(int(schema.get("rescheduleMaxTimes") or 0), 1)
        self.assertGreaterEqual(int(schema.get("remindAheadMinutes") or 0), 1)
        self.assertGreaterEqual(int(schema.get("noShowLimit") or 0), 1)
        self.assertGreaterEqual(int(schema.get("lateGraceMinutes") or 0), 1)

        for key in (
            "cancelFreeHoursHint",
            "rescheduleMaxHint",
            "remindAheadHint",
            "noShowLimitHint",
            "reserveSuccessTitle",
            "reserveSuccessBody",
            "lateGraceHint",
            "checkInLabel",
            "lateFlagLabel",
            "maintainBlockHint",
            "waitlistPromoteTitle",
            "slotCalendarLegendOk",
            "slotCalendarLegendWarn",
            "slotCalendarLegendFull",
            "adminNoteLabel",
            "adminNoteHint",
            "reserveBlacklistDenyMessage",
            "reserveBlacklistAppealTitle",
            "reserveBlacklistAppealReasonLabel",
        ):
            self.assertIn(key, labels)
            self.assertTrue(str(labels.get(key) or "").strip(), key)

        self.assertIn("maintainFrom", keys)
        self.assertIn("maintainTo", keys)
        self.assertIn("adminNote", keys)

        policy = collect_app("DOM-HOSPITAL", out)
        self.assertGreaterEqual(int(policy.get("CANCEL_FREE_HOURS") or 0), 1)
        self.assertGreaterEqual(int(policy.get("RESCHEDULE_MAX_TIMES") or 0), 1)
        self.assertGreaterEqual(int(policy.get("REMIND_AHEAD_MINUTES") or 0), 1)
        self.assertGreaterEqual(int(policy.get("NO_SHOW_LIMIT") or 0), 1)
        self.assertGreaterEqual(int(policy.get("LATE_GRACE_MINUTES") or 0), 1)
        self.assertTrue(policy.get("RESERVE_BLACKLIST_ENABLED"))
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-HOSPITAL", out)
        self.assertNotIn("cancel-free-hours:", yml)
        self.assertNotIn("reserve-blacklist-enabled:", yml)

        menus = (schema.get("menus") or {}).get("admin") or []
        menu_keys = {m.get("key") for m in menus if isinstance(m, dict)}
        self.assertIn("reserve_blacklist", menu_keys)
        user_menus = (schema.get("menus") or {}).get("user") or []
        user_keys = {m.get("key") for m in user_menus if isinstance(m, dict)}
        self.assertIn("reserve_blacklist_appeal", user_keys)

    def test_all_reserve_domains_get_thicken(self) -> None:
        titles = {
            "DOM-HOSPITAL": "医院挂号预约系统",
            "DOM-PARKING": "车位预约管理系统",
            "DOM-MEETING": "会议室预约系统",
            "DOM-SALON": "美发预约管理系统",
            "DOM-HOTEL": "酒店客房预订系统",
            "DOM-CARRENT": "汽车租赁管理系统",
            "DOM-INSTRUMENT": "仪器机时预约系统",
        }
        for domain in RESERVE_DOMAINS:
            out = _spec(domain, titles[domain], "")
            schema = out.get("schema") or {}
            self.assertTrue(
                (schema.get("reserveThicken") or {}).get("core"),
                domain,
            )

    def test_ensure_sql_injects_columns(self) -> None:
        sql = domain_sql("DOM-MEETING", "会议室预约系统", "")
        self.assertIn("reschedule_count", sql)
        self.assertIn("remind_sent", sql)
        self.assertIn("no_show", sql)
        self.assertIn("late_flag", sql)
        self.assertIn("checked_in_at", sql)
        self.assertIn("maintain_from", sql)
        self.assertIn("maintain_to", sql)
        self.assertIn("admin_note", sql)
        self.assertIn("reserve_blacklist", sql)
        self.assertIn("reserve_blacklist_appeal", sql)

        shop = ensure_reserve_thicken_sql(
            "CREATE TABLE IF NOT EXISTS t (id INT);\n",
            domain="DOM-SHOP",
            reservation_table="reservation",
            item_table="product",
        )
        self.assertNotIn("reserve_blacklist", shop)

    def test_hospital_r02_domain_skin(self) -> None:
        out = _spec("DOM-HOSPITAL", "医院挂号预约系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("reserveThicken") or {}
        labels = schema.get("labels") or {}
        resv = (schema.get("entities") or {}).get("reservation") or {}
        archive = (schema.get("entities") or {}).get("archive") or {}
        keys = {f.get("key") for f in (archive.get("fields") or []) if isinstance(f, dict)}

        for flag in (
            "hospitalCheckinCode",
            "hospitalPeriodRemain",
            "hospitalPatientProfile",
            "hospitalQueueNo",
            "hospitalWaitlist",
            "hospitalCancelCutoff",
            "hospitalVisitType",
            "hospitalDeptIntro",
            "hospitalStopNotify",
            "hospitalStopCalendar",
            "hospitalQueueEstimate",
            "hospitalIdLimit",
            "hospitalRevisitPriority",
            "hospitalSlotKind",
        ):
            self.assertTrue(thicken.get(flag), flag)

        self.assertTrue(schema.get("patientProfile"))
        self.assertTrue(schema.get("hospitalWaitlist"))
        self.assertTrue(resv.get("allowWaitlist"))
        self.assertGreaterEqual(int(schema.get("hospitalCancelCutoffMinutes") or 0), 1)
        self.assertGreaterEqual(int(schema.get("hospitalIdLimitPerDay") or 0), 1)

        for key in (
            "checkinCodeLabel",
            "checkinCodeHint",
            "checkinCodeAdminHint",
            "slotPeriodMorningLabel",
            "slotPeriodAfternoonLabel",
            "slotPeriodRemainHint",
            "patientProfileMenuLabel",
            "patientProfileTitle",
            "patientProfileLead",
            "patientProfileNameLabel",
            "patientProfileRelationLabel",
            "patientProfileIdHintLabel",
            "queueNoLabel",
            "queueNoHint",
            "hospitalWaitlistHint",
            "hospitalCancelCutoffLabel",
            "hospitalCancelCutoffHint",
            "visitTypeLabel",
            "visitTypeHint",
            "deptIntroLabel",
            "deptIntroHint",
            "hospitalStopNotifyTitle",
            "hospitalStopNotifyBody",
            "hospitalStopCalendarHint",
            "queueEstimateHint",
            "queueEstimateLabel",
            "hospitalIdLimitLabel",
            "hospitalIdLimitHint",
            "revisitPriorityHint",
            "slotKindLabel",
            "slotKindClinic",
            "slotKindLab",
            "slotKindHint",
        ):
            self.assertIn(key, labels)
            self.assertTrue(str(labels.get(key) or "").strip(), key)

        for col in ("checkinCode", "deptIntro", "slotKind", "queueEstimateHint"):
            self.assertIn(col, keys)

        user_keys = {
            m.get("key")
            for m in ((schema.get("menus") or {}).get("user") or [])
            if isinstance(m, dict)
        }
        self.assertIn("patient_profile", user_keys)

        policy = collect_app("DOM-HOSPITAL", out)
        self.assertGreaterEqual(int(policy.get("HOSPITAL_CANCEL_CUTOFF_MINUTES") or 0), 1)
        self.assertGreaterEqual(int(policy.get("HOSPITAL_ID_LIMIT_PER_DAY") or 0), 1)
        self.assertTrue(policy.get("HOSPITAL_WAITLIST_ENABLED"))
        self.assertTrue(policy.get("PATIENT_PROFILE_ENABLED"))
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-HOSPITAL", out)
        self.assertNotIn("hospital-cancel-cutoff-minutes:", yml)
        self.assertNotIn("patient-profile-enabled:", yml)

        sql = domain_sql("DOM-HOSPITAL", "医院挂号预约系统", "")
        self.assertIn("patient_profile", sql)
        self.assertIn("dept_intro", sql)
        self.assertIn("slot_kind", sql)
        self.assertIn("queue_estimate_hint", sql)

        parking = _spec("DOM-PARKING", "车位预约管理系统", "")
        psch = parking.get("schema") or {}
        self.assertFalse(psch.get("patientProfile"))
        self.assertFalse((psch.get("reserveThicken") or {}).get("hospitalCheckinCode"))

    def test_parking_r03_domain_skin(self) -> None:
        out = _spec("DOM-PARKING", "车位预约管理系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("reserveThicken") or {}
        labels = schema.get("labels") or {}
        archive = (schema.get("entities") or {}).get("archive") or {}
        keys = {f.get("key") for f in (archive.get("fields") or []) if isinstance(f, dict)}

        for flag in (
            "parkingOvertime",
            "parkingPass",
            "parkingCarpassHint",
            "parkingDurationFee",
            "parkingCancelPenalty",
            "parkingShareSlot",
            "parkingOverlap",
        ):
            self.assertTrue(thicken.get(flag), flag)

        self.assertTrue(schema.get("parkingPass"))
        self.assertGreaterEqual(int(schema.get("parkingHourlyYuan") or 0), 1)
        self.assertGreaterEqual(int(schema.get("parkingOvertimeYuan") or 0), 1)

        for key in (
            "parkingOvertimeLabel",
            "parkingOvertimeHint",
            "parkingPassMenuLabel",
            "parkingPassTitle",
            "parkingPassLead",
            "parkingPassRemainHint",
            "parkingPassPackLabel",
            "parkingPassRemainLabel",
            "parkingPassGrantLabel",
            "parkingCarpassHint",
            "passHintLabel",
            "passHintAdminHint",
            "parkingDurationFeeLabel",
            "parkingDurationFeeHint",
            "parkingEntryLabel",
            "parkingExitLabel",
            "parkingHourlyLabel",
            "parkingCancelPenaltyHint",
            "parkingShareSlotHint",
            "parkingOverlapHint",
        ):
            self.assertIn(key, labels)
            self.assertTrue(str(labels.get(key) or "").strip(), key)

        self.assertIn("passHint", keys)

        user_keys = {
            m.get("key")
            for m in ((schema.get("menus") or {}).get("user") or [])
            if isinstance(m, dict)
        }
        admin_keys = {
            m.get("key")
            for m in ((schema.get("menus") or {}).get("admin") or [])
            if isinstance(m, dict)
        }
        self.assertIn("parking_pass", user_keys)
        self.assertIn("parking_pass_admin", admin_keys)

        policy = collect_app("DOM-PARKING", out)
        self.assertGreaterEqual(int(policy.get("PARKING_HOURLY_YUAN") or 0), 1)
        self.assertGreaterEqual(int(policy.get("PARKING_OVERTIME_YUAN") or 0), 1)
        self.assertTrue(policy.get("PARKING_PASS_ENABLED"))
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-PARKING", out)
        self.assertNotIn("parking-hourly-yuan:", yml)
        self.assertNotIn("parking-pass-enabled:", yml)

        sql = domain_sql("DOM-PARKING", "车位预约管理系统", "")
        self.assertIn("parking_pass", sql)
        self.assertIn("exit_at", sql)
        self.assertIn("overtime_fee_yuan", sql)
        self.assertIn("duration_fee_yuan", sql)
        self.assertIn("pass_hint", sql)

        hospital = _spec("DOM-HOSPITAL", "医院挂号预约系统", "")
        hsch = hospital.get("schema") or {}
        self.assertFalse(hsch.get("parkingPass"))
        self.assertFalse((hsch.get("reserveThicken") or {}).get("parkingOvertime"))

    def test_meeting_r04_domain_skin(self) -> None:
        out = _spec("DOM-MEETING", "会议室预约系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("reserveThicken") or {}
        labels = schema.get("labels") or {}
        resv = (schema.get("entities") or {}).get("reservation") or {}
        archive = (schema.get("entities") or {}).get("archive") or {}
        keys = {f.get("key") for f in (archive.get("fields") or []) if isinstance(f, dict)}

        self.assertTrue(resv.get("requireConfirm"))
        self.assertTrue(schema.get("meetingMinutesRequired"))
        self.assertGreaterEqual(int(schema.get("meetingMinDurationMinutes") or 0), 1)

        for flag in (
            "meetingRequireConfirm",
            "meetingMinutes",
            "meetingCheckinExport",
            "meetingConflict",
            "meetingRecording",
            "meetingVideo",
            "meetingWeeklyRepeat",
            "meetingService",
            "meetingBlacklist",
            "meetingDoorCode",
            "meetingCheckinCode",
            "meetingMinDuration",
            "meetingStage",
        ):
            self.assertTrue(thicken.get(flag), flag)

        for key in (
            "meetingRequireConfirmHint",
            "meetingMinutesLabel",
            "meetingMinutesHint",
            "meetingCheckinExportLabel",
            "meetingCheckinExportHint",
            "meetingConflictHint",
            "meetingRecordingLabel",
            "meetingRecordingHint",
            "meetingVideoLabel",
            "meetingVideoHint",
            "meetingWeeklyRepeatLabel",
            "meetingWeeklyRepeatHint",
            "meetingServiceTeaLabel",
            "meetingServiceDeviceLabel",
            "meetingServiceHint",
            "meetingBlacklistHint",
            "meetingDoorCodeLabel",
            "meetingDoorCodeHint",
            "meetingCheckinCodeLabel",
            "meetingCheckinCodeHint",
            "meetingMinDurationLabel",
            "meetingMinDurationHint",
            "meetingStageLabel",
            "meetingStageInProgress",
            "meetingStageEnded",
            "meetingStageHint",
        ):
            self.assertIn(key, labels)
            self.assertTrue(str(labels.get(key) or "").strip(), key)

        self.assertIn("minDurationMinutes", keys)

        policy = collect_app("DOM-MEETING", out)
        self.assertTrue(policy.get("SLOT_REQUIRE_CONFIRM"))
        self.assertGreaterEqual(int(policy.get("MEETING_MIN_DURATION_MINUTES") or 0), 1)
        self.assertTrue(policy.get("MEETING_MINUTES_REQUIRED"))
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-MEETING", out)
        self.assertNotIn("slot-require-confirm:", yml)
        self.assertNotIn("meeting-min-duration-minutes:", yml)
        self.assertNotIn("meeting-minutes-required:", yml)

        sql = domain_sql("DOM-MEETING", "会议室预约系统", "")
        self.assertIn("recording_url", sql)
        self.assertIn("video_url", sql)
        self.assertIn("door_code", sql)
        self.assertIn("minutes_attach", sql)
        self.assertIn("meeting_stage", sql)
        self.assertIn("checkin_token", sql)
        self.assertIn("min_duration_minutes", sql)

        parking = _spec("DOM-PARKING", "车位预约管理系统", "")
        self.assertFalse((parking.get("schema") or {}).get("meetingMinutesRequired"))

    def test_salon_r05_domain_skin(self) -> None:
        out = _spec("DOM-SALON", "美发美容预约系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("reserveThicken") or {}
        labels = schema.get("labels") or {}
        archive = (schema.get("entities") or {}).get("archive") or {}
        keys = {f.get("key") for f in (archive.get("fields") or []) if isinstance(f, dict)}
        caps = set(out.get("capabilities") or [])

        # wallet / gallery：开题写到才挂，禁止 SALON 域默认硬挂
        self.assertNotIn("wallet", caps)
        self.assertNotIn("gallery", caps)
        self.assertFalse(thicken.get("salonWallet"))
        self.assertFalse(thicken.get("salonGallery"))
        self.assertGreaterEqual(int(schema.get("salonRescheduleFeeYuan") or 0), 1)

        for flag in (
            "salonCheckinCode",
            "salonServiceMinutes",
            "salonQueueNo",
            "salonRescheduleFee",
            "salonLateGrace",
            "salonTaboo",
            "salonCheckinScan",
            "salonVisitCount",
        ):
            self.assertTrue(thicken.get(flag), flag)

        for key in (
            "checkinCodeLabel",
            "checkinCodeHint",
            "checkinCodeAdminHint",
            "salonServiceMinutesLabel",
            "salonServiceMinutesHint",
            "queueNoLabel",
            "queueNoHint",
            "salonRescheduleFeeLabel",
            "salonRescheduleFeeHint",
            "salonLateGraceHint",
            "salonTabooLabel",
            "salonTabooHint",
            "salonCheckinScanLabel",
            "salonCheckinScanHint",
            "salonVisitCountLabel",
            "salonVisitCountHint",
        ):
            self.assertIn(key, labels)
            self.assertTrue(str(labels.get(key) or "").strip(), key)

        self.assertIn("checkinCode", keys)
        self.assertIn("serviceMinutes", keys)
        self.assertIn("tabooNote", keys)

        policy = collect_app("DOM-SALON", out)
        self.assertGreaterEqual(int(policy.get("SALON_RESCHEDULE_FEE_YUAN") or 0), 1)
        java = render_app(policy)
        self.assertIn("SALON_RESCHEDULE_FEE_YUAN", java)
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-SALON", out)
        self.assertNotIn("salon-reschedule-fee-yuan:", yml)
        self.assertNotIn("gallery-enabled: true", yml)

        sql = domain_sql("DOM-SALON", "美发美容预约系统", "")
        self.assertIn("checkin_code", sql)
        self.assertIn("service_minutes", sql)
        self.assertIn("taboo_note", sql)
        self.assertIn("reschedule_fee_yuan", sql)
        self.assertIn("checkin_token", sql)

        meeting = _spec("DOM-MEETING", "会议室预约系统", "")
        self.assertFalse((meeting.get("schema") or {}).get("salonRescheduleFeeYuan"))
        self.assertFalse((meeting.get("schema") or {}).get("reserveThicken", {}).get("salonCheckinCode"))

    def test_hotel_r06_domain_skin(self) -> None:
        out = _spec("DOM-HOTEL", "酒店客房预订系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("reserveThicken") or {}
        labels = schema.get("labels") or {}
        archive = (schema.get("entities") or {}).get("archive") or {}
        resv = (schema.get("entities") or {}).get("reservation") or {}
        keys = {f.get("key") for f in (archive.get("fields") or []) if isinstance(f, dict)}
        caps = set(out.get("capabilities") or [])

        # 查房浅字段：禁止硬挂 material_check（wallet 为 HOTEL 旧域默认，非 R-06）
        self.assertNotIn("material_check", caps)
        self.assertNotIn("gallery", caps)
        self.assertGreaterEqual(int(schema.get("hotelLateCheckoutFeeYuan") or 0), 1)
        self.assertTrue(schema.get("hotelNoticeRequired"))
        self.assertTrue(resv.get("hotelNoticeRequired"))
        self.assertEqual(resv.get("guestCountLabel"), "同住人数")

        for flag in (
            "hotelExtendStay",
            "hotelLateCheckout",
            "hotelIdNo",
            "hotelDepositBalance",
            "hotelStayMultiNight",
            "hotelBreakfast",
            "hotelNoticeAck",
            "hotelExtraBed",
            "hotelRoomKind",
            "hotelHourlyToFull",
            "hotelRoommate",
            "hotelCheckoutChecklist",
        ):
            self.assertTrue(thicken.get(flag), flag)

        for key in (
            "hotelExtendStayLabel",
            "hotelExtendStayHint",
            "hotelLateCheckoutLabel",
            "hotelLateCheckoutHint",
            "hotelIdNoLabel",
            "hotelIdNoHint",
            "hotelIdNoMaskedLabel",
            "hotelDepositLabel",
            "hotelBalanceLabel",
            "hotelDepositBalanceHint",
            "hotelStayMultiNightHint",
            "hotelBreakfastLabel",
            "hotelBreakfastHint",
            "hotelNoticeLabel",
            "hotelNoticeText",
            "hotelNoticeAckLabel",
            "hotelExtraBedLabel",
            "hotelExtraBedHint",
            "hotelRoomKindLabel",
            "hotelRoomKindFull",
            "hotelRoomKindHourly",
            "hotelRoomKindHint",
            "hotelHourlyToFullHint",
            "hotelRoommateLabel",
            "hotelRoommateHint",
            "hotelCheckoutChecklistLabel",
            "hotelCheckoutChecklistHint",
        ):
            self.assertIn(key, labels)
            self.assertTrue(str(labels.get(key) or "").strip(), key)

        self.assertIn("roomKind", keys)

        policy = collect_app("DOM-HOTEL", out)
        self.assertGreaterEqual(int(policy.get("HOTEL_LATE_CHECKOUT_FEE_YUAN") or 0), 1)
        self.assertTrue(policy.get("HOTEL_NOTICE_REQUIRED"))
        java = render_app(policy)
        self.assertIn("HOTEL_LATE_CHECKOUT_FEE_YUAN", java)
        self.assertIn("HOTEL_NOTICE_REQUIRED = true", java)
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-HOTEL", out)
        self.assertNotIn("hotel-late-checkout-fee-yuan:", yml)
        self.assertNotIn("hotel-notice-required:", yml)

        sql = domain_sql("DOM-HOTEL", "酒店客房预订系统", "")
        for col in (
            "stay_from",
            "stay_to",
            "id_no",
            "deposit_yuan",
            "balance_yuan",
            "breakfast_vouchers",
            "notice_ack",
            "extra_bed",
            "late_checkout_fee_yuan",
            "checkout_checklist",
            "room_kind",
        ):
            self.assertIn(col, sql)

        salon = _spec("DOM-SALON", "美发美容预约系统", "")
        self.assertFalse((salon.get("schema") or {}).get("hotelLateCheckoutFeeYuan"))
        self.assertFalse((salon.get("schema") or {}).get("reserveThicken", {}).get("hotelExtendStay"))

    def test_carrent_r07_domain_skin(self) -> None:
        out = _spec("DOM-CARRENT", "汽车租赁管理系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("reserveThicken") or {}
        labels = schema.get("labels") or {}
        archive = (schema.get("entities") or {}).get("archive") or {}
        keys = {f.get("key") for f in (archive.get("fields") or []) if isinstance(f, dict)}
        caps = set(out.get("capabilities") or [])

        self.assertNotIn("material_check", caps)
        self.assertNotIn("gallery", caps)
        self.assertNotIn("rental_bond", caps)
        self.assertGreaterEqual(int(schema.get("carrentMileageOverFeeYuan") or 0), 1)

        for flag in (
            "carrentViolationHold",
            "carrentInspectAck",
            "carrentMileageOver",
            "carrentNav",
            "carrentInsurance",
            "carrentLicenseExpire",
            "carrentViolationAttach",
            "carrentEtcFee",
        ):
            self.assertTrue(thicken.get(flag), flag)

        for key in (
            "carrentViolationHoldLabel",
            "carrentViolationHoldHint",
            "carrentInspectAckLabel",
            "carrentInspectAckHint",
            "carrentMileageOverLabel",
            "carrentMileageOverHint",
            "carrentPickupNavLabel",
            "carrentReturnNavLabel",
            "carrentNavHint",
            "carrentInsuranceLabel",
            "carrentInsuranceNone",
            "carrentInsuranceBasic",
            "carrentInsuranceFull",
            "carrentInsuranceHint",
            "carrentLicenseExpireLabel",
            "carrentLicenseExpireHint",
            "carrentViolationAttachLabel",
            "carrentViolationAttachHint",
            "carrentEtcFeeLabel",
            "carrentEtcFeeHint",
        ):
            self.assertIn(key, labels)
            self.assertTrue(str(labels.get(key) or "").strip(), key)

        self.assertIn("pickupNavUrl", keys)
        self.assertIn("returnNavUrl", keys)

        policy = collect_app("DOM-CARRENT", out)
        self.assertGreaterEqual(int(policy.get("CARRENT_MILEAGE_OVER_FEE_YUAN") or 0), 1)
        java = render_app(policy)
        self.assertIn("CARRENT_MILEAGE_OVER_FEE_YUAN", java)
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-CARRENT", out)
        self.assertNotIn("carrent-mileage-over-fee-yuan:", yml)

        sql = domain_sql("DOM-CARRENT", "汽车租赁管理系统", "")
        for col in (
            "violation_hold_yuan",
            "violation_hold_note",
            "inspect_ack",
            "mileage_over_fee_yuan",
            "insurance_pkg",
            "license_expire_on",
            "violation_attach",
            "etc_fee_yuan",
            "pickup_nav_url",
            "return_nav_url",
        ):
            self.assertIn(col, sql)

        hotel = _spec("DOM-HOTEL", "酒店客房预订系统", "")
        self.assertFalse((hotel.get("schema") or {}).get("carrentMileageOverFeeYuan"))
        self.assertFalse((hotel.get("schema") or {}).get("reserveThicken", {}).get("carrentEtcFee"))

    def test_instrument_r08_domain_skin(self) -> None:
        out = _spec("DOM-INSTRUMENT", "大型仪器机时预约系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("reserveThicken") or {}
        labels = schema.get("labels") or {}
        resv = (schema.get("entities") or {}).get("reservation") or {}
        caps = set(out.get("capabilities") or [])

        self.assertNotIn("material_check", caps)
        self.assertTrue(resv.get("requireConfirm"))
        self.assertTrue(resv.get("requireRemark"))
        self.assertEqual(resv.get("remarkLabel"), "实验目的")
        self.assertTrue(schema.get("instrumentTrainingRequired"))
        self.assertGreaterEqual(int(schema.get("instrumentOvertimeYuan") or 0), 1)

        for flag in (
            "instrumentOvertime",
            "instrumentTraining",
            "instrumentConflict",
            "instrumentPurpose",
            "instrumentConsumable",
            "instrumentMentor",
            "instrumentFeeExport",
        ):
            self.assertTrue(thicken.get(flag), flag)

        for key in (
            "instrumentOvertimeLabel",
            "instrumentOvertimeHint",
            "instrumentTrainingAckLabel",
            "instrumentTrainingAckHint",
            "instrumentConflictHint",
            "instrumentPurposeLabel",
            "instrumentPurposeHint",
            "instrumentConsumableLabel",
            "instrumentConsumableHint",
            "instrumentMentorConfirmHint",
            "instrumentFeeExportLabel",
            "instrumentFeeExportHint",
        ):
            self.assertIn(key, labels)
            self.assertTrue(str(labels.get(key) or "").strip(), key)

        policy = collect_app("DOM-INSTRUMENT", out)
        self.assertTrue(policy.get("SLOT_REQUIRE_CONFIRM"))
        self.assertTrue(policy.get("SLOT_REQUIRE_REMARK"))
        self.assertTrue(policy.get("INSTRUMENT_TRAINING_REQUIRED"))
        self.assertGreaterEqual(int(policy.get("INSTRUMENT_OVERTIME_YUAN") or 0), 1)
        java = render_app(policy)
        self.assertIn("INSTRUMENT_OVERTIME_YUAN", java)
        self.assertIn("INSTRUMENT_TRAINING_REQUIRED", java)
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-INSTRUMENT", out)
        self.assertNotIn("instrument-overtime-yuan:", yml)
        self.assertNotIn("instrument-training-required:", yml)
        self.assertNotIn("slot-require-confirm:", yml)

        sql = domain_sql("DOM-INSTRUMENT", "大型仪器机时预约系统", "")
        for col in ("overtime_fee_yuan", "training_ack", "consumable_note"):
            self.assertIn(col, sql)

        parking = _spec("DOM-PARKING", "车位预约管理系统", "")
        self.assertFalse((parking.get("schema") or {}).get("instrumentOvertimeYuan"))
        self.assertFalse(
            (parking.get("schema") or {}).get("reserveThicken", {}).get("instrumentFeeExport")
        )

    def test_r09_capability_islands(self) -> None:
        from pathlib import Path

        # 未挂 cap：不出现 R-09 thicken 旗
        bare = _spec("DOM-SALON", "美发美容预约系统", "")
        bare_th = (bare.get("schema") or {}).get("reserveThicken") or {}
        self.assertFalse(bare_th.get("salonLessonRemain"))
        self.assertFalse(bare_th.get("salonWallet"))
        self.assertFalse(bare_th.get("salonGallery"))
        self.assertFalse(bare_th.get("salonLeaveBlock"))

        hospital = attach_accept(
            {
                "domain": "DOM-HOSPITAL",
                "title": "医院挂号预约系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-HOSPITAL"]) + ["staff_roster"],
                "features": [],
                "archetype": "ARCH-RESERVE",
            },
            "医生排班值班表",
        )
        h_th = (hospital.get("schema") or {}).get("reserveThicken") or {}
        h_lab = (hospital.get("schema") or {}).get("labels") or {}
        self.assertTrue(h_th.get("hospitalRoster"))
        self.assertIn("hospitalRosterHint", h_lab)

        salon = attach_accept(
            {
                "domain": "DOM-SALON",
                "title": "美发美容预约系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-SALON"])
                + ["staff_roster", "lesson_pack", "gallery"],
                "features": [],
                "archetype": "ARCH-RESERVE",
            },
            "技师排班课时包储值卡作品集",
        )
        self.assertIn("wallet", salon.get("capabilities") or [])
        s_th = (salon.get("schema") or {}).get("reserveThicken") or {}
        s_lab = (salon.get("schema") or {}).get("labels") or {}
        for flag in (
            "salonLeaveBlock",
            "salonLessonRemain",
            "salonLessonExpire",
            "salonWallet",
            "salonGallery",
        ):
            self.assertTrue(s_th.get(flag), flag)
        for key in (
            "salonLeaveBlockHint",
            "salonLessonRemainLabel",
            "salonLessonExpireBody",
            "salonWalletHint",
            "salonGalleryHint",
        ):
            self.assertIn(key, s_lab)
            self.assertTrue(str(s_lab.get(key) or "").strip(), key)

        meeting = attach_accept(
            {
                "domain": "DOM-MEETING",
                "title": "会议室预约系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-MEETING"]) + ["room_equipment"],
                "features": [],
                "archetype": "ARCH-RESERVE",
            },
            "会议室设备清单录制设备",
        )
        m_th = (meeting.get("schema") or {}).get("reserveThicken") or {}
        m_lab = (meeting.get("schema") or {}).get("labels") or {}
        self.assertTrue(m_th.get("meetingEquipBorrow"))
        self.assertIn("meetingEquipBorrowLabel", m_lab)
        sql = domain_sql("DOM-MEETING", "会议室预约系统", "会议室设备清单录制设备")
        self.assertIn("equip_borrow", sql)

        fe = Path(__file__).resolve().parents[2] / "skeletons" / "baseline" / "frontend" / "src"
        slot_book = (fe / "views" / "user" / "SlotBook.vue").read_text(encoding="utf-8")
        self.assertIn("hospitalRosterHint", slot_book)
        self.assertIn("salonLessonRemain", slot_book)
        self.assertIn("meetingEquipBorrow", slot_book)
        self.assertIn("salonWalletOn", slot_book)
        admin = (fe / "views" / "admin" / "ReservationsAdmin.vue").read_text(encoding="utf-8")
        self.assertIn("meetingEquipBorrowLabel", admin)
        my_resv = (fe / "views" / "user" / "MyReservations.vue").read_text(encoding="utf-8")
        self.assertIn("meetingEquipBorrowLabel", my_resv)
        be = (
            Path(__file__).resolve().parents[2]
            / "skeletons"
            / "baseline"
            / "backend"
            / "src"
            / "main"
            / "java"
            / "com"
            / "thesis"
        )
        self.assertIn(
            "assertNotOnLeave",
            (be / "capability" / "StaffRosterStore.java").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "expireSoonNotify",
            (be / "capability" / "LessonStore.java").read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
