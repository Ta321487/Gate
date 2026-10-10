package com.thesis.capability;

import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.thesis.config.MybatisSupport;
import com.thesis.mapper.SchemaMapper;
import com.thesis.mapper.SlotMapper;
import com.thesis.service.MessageStore;
import com.thesis.service.UserStore;

import java.math.BigDecimal;
import java.sql.Timestamp;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 能力 slot_reserve：资源时段库存占坑（有别于本人已选时段相交）。
 */
public final class SlotStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private static String SLOT = "";
    private static String RESV = "";
    private static boolean enabled = false;
    private static boolean requireRemark = false;
    /** true：预约进 pending，管理端确认后才变 confirmed；false：占坑即确认 */
    private static boolean requireConfirm = false;
    /** true：办结后用户可评星+短评 */
    private static boolean allowRating = false;
    private static int cancelFreeHours = 0;
    private static int rescheduleMaxTimes = 0;
    private static int remindAheadMinutes = 0;
    private static int noShowLimit = 0;
    private static int lateGraceMinutes = 15;
    private static boolean reserveBlacklistOn = false;
    private static int hospitalCancelCutoffMinutes = 0;
    private static int hospitalIdLimitPerDay = 0;
    private static boolean hospitalWaitlistOn = false;
    private static int parkingHourlyYuan = 0;
    private static int parkingOvertimeYuan = 0;
    private static boolean parkingPassOn = false;
    private static int meetingMinDurationMinutes = 0;
    private static boolean meetingMinutesRequired = false;
    /** SALON：改约手续费默认（元） */
    private static int salonRescheduleFeeYuan = 0;
    /** HOTEL：延迟退房加收默认（元） */
    private static int hotelLateCheckoutFeeYuan = 0;
    /** HOTEL：入住须知必勾 */
    private static boolean hotelNoticeRequired = false;
    /** CARRENT：里程超支加收默认（元） */
    private static int carrentMileageOverFeeYuan = 0;
    /** INSTRUMENT：超时加收默认（元） */
    private static int instrumentOvertimeYuan = 0;
    /** INSTRUMENT：须勾选培训合格 */
    private static boolean instrumentTrainingRequired = false;

    private SlotStore() {}

    private static SlotMapper mapper() {
        return MybatisSupport.mapper(SlotMapper.class);
    }

    private static SchemaMapper schema() {
        return MybatisSupport.mapper(SchemaMapper.class);
    }

    public static void bind(String slotTable, String reservationTable) {
        SLOT = slotTable == null ? "" : slotTable.trim();
        RESV = reservationTable == null ? "" : reservationTable.trim();
        enabled = !SLOT.isBlank() && !RESV.isBlank();
        requireRemark = false;
        requireConfirm = false;
        allowRating = false;
        cancelFreeHours = 0;
        rescheduleMaxTimes = 0;
        remindAheadMinutes = 0;
        noShowLimit = 0;
        lateGraceMinutes = 15;
        reserveBlacklistOn = false;
        hospitalCancelCutoffMinutes = 0;
        hospitalIdLimitPerDay = 0;
        hospitalWaitlistOn = false;
        parkingHourlyYuan = 0;
        parkingOvertimeYuan = 0;
        parkingPassOn = false;
        meetingMinDurationMinutes = 0;
        meetingMinutesRequired = false;
        salonRescheduleFeeYuan = 0;
        hotelLateCheckoutFeeYuan = 0;
        hotelNoticeRequired = false;
        carrentMileageOverFeeYuan = 0;
        instrumentOvertimeYuan = 0;
        instrumentTrainingRequired = false;
    }

    public static void configureRemark(boolean required) {
        requireRemark = required;
    }

    public static void configureConfirm(boolean required) {
        requireConfirm = required;
    }

    public static void configureRating(boolean ratingEnabled) {
        allowRating = ratingEnabled;
    }

    public static void configureThicken(
            int cancelFreeHrs,
            int rescheduleMax,
            int remindAheadMin,
            int noShowLim,
            int lateGraceMin,
            boolean blacklistOn) {
        cancelFreeHours = Math.max(0, cancelFreeHrs);
        rescheduleMaxTimes = Math.max(0, rescheduleMax);
        remindAheadMinutes = Math.max(0, remindAheadMin);
        noShowLimit = Math.max(0, noShowLim);
        lateGraceMinutes = Math.max(0, lateGraceMin);
        reserveBlacklistOn = blacklistOn;
    }

    public static boolean requireConfirm() {
        return requireConfirm;
    }

    public static boolean allowRating() {
        return allowRating;
    }

    public static int remindAheadMinutes() {
        return remindAheadMinutes;
    }

    public static void configureHospital(
            int cancelCutoffMinutes, int idLimitPerDay, boolean waitlistOn) {
        hospitalCancelCutoffMinutes = Math.max(0, cancelCutoffMinutes);
        hospitalIdLimitPerDay = Math.max(0, idLimitPerDay);
        hospitalWaitlistOn = waitlistOn;
    }

    public static void configureParking(int hourlyYuan, int overtimeYuan, boolean passOn) {
        parkingHourlyYuan = Math.max(0, hourlyYuan);
        parkingOvertimeYuan = Math.max(0, overtimeYuan);
        parkingPassOn = passOn;
    }

    public static void configureMeeting(int minDurationMinutes, boolean minutesRequired) {
        meetingMinDurationMinutes = Math.max(0, minDurationMinutes);
        meetingMinutesRequired = minutesRequired;
    }

    /** §1.7 R-05 SALON */
    public static void configureSalon(int rescheduleFeeYuan) {
        salonRescheduleFeeYuan = Math.max(0, rescheduleFeeYuan);
    }

    /** §1.7 R-06 HOTEL */
    public static void configureHotel(int lateCheckoutFeeYuan, boolean noticeRequired) {
        hotelLateCheckoutFeeYuan = Math.max(0, lateCheckoutFeeYuan);
        hotelNoticeRequired = noticeRequired;
    }

    /** §1.7 R-07 CARRENT */
    public static void configureCarrent(int mileageOverFeeYuan) {
        carrentMileageOverFeeYuan = Math.max(0, mileageOverFeeYuan);
    }

    /** §1.7 R-08 INSTRUMENT */
    public static void configureInstrument(int overtimeYuan, boolean trainingRequired) {
        instrumentOvertimeYuan = Math.max(0, overtimeYuan);
        instrumentTrainingRequired = trainingRequired;
    }

    public static void unbind() {
        enabled = false;
        requireRemark = false;
        requireConfirm = false;
        allowRating = false;
        cancelFreeHours = 0;
        rescheduleMaxTimes = 0;
        remindAheadMinutes = 0;
        noShowLimit = 0;
        lateGraceMinutes = 15;
        reserveBlacklistOn = false;
        hospitalCancelCutoffMinutes = 0;
        hospitalIdLimitPerDay = 0;
        hospitalWaitlistOn = false;
        parkingHourlyYuan = 0;
        parkingOvertimeYuan = 0;
        parkingPassOn = false;
        meetingMinDurationMinutes = 0;
        meetingMinutesRequired = false;
        salonRescheduleFeeYuan = 0;
        hotelLateCheckoutFeeYuan = 0;
        hotelNoticeRequired = false;
        carrentMileageOverFeeYuan = 0;
        instrumentOvertimeYuan = 0;
        instrumentTrainingRequired = false;
        SLOT = RESV = "";
    }

    public static boolean enabled() {
        return enabled;
    }

    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        String s = String.valueOf(o).trim();
        return s.isBlank() || "null".equals(s) ? null : s;
    }

    public static List<Map<String, Object>> listSlots(Long itemId, String day) {
        return listSlots(itemId, day, false);
    }

    /** @param bookableOnly 用户预约：只列未开始时段 */
    public static List<Map<String, Object>> listSlots(Long itemId, String day, boolean bookableOnly) {
        requireEnabled();
        String d = day == null || day.isBlank() ? null : day.trim();
        List<Map<String, Object>> raw = mapper().selectSlots(SLOT, itemId, d, bookableOnly);
        List<Map<String, Object>> out = new ArrayList<>();
        if (raw != null) {
            for (Map<String, Object> r : raw) out.add(enrichSlot(shapeSlot(r)));
        }
        return out;
    }

    public static Map<String, Object> getSlot(long id) {
        requireEnabled();
        Map<String, Object> raw = mapper().selectSlotById(SLOT, id);
        return raw == null ? null : enrichSlot(shapeSlot(raw));
    }

    public static int generateDaySlots(
            long itemId, String day, int startHour, int endHour, int slotMinutes, int capacity) {
        requireEnabled();
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) throw new IllegalArgumentException("资源不存在");
        Object sm = item.get("serviceMinutes");
        if (sm == null) sm = item.get("service_minutes");
        int svc = toInt(sm);
        if (svc >= 15) slotMinutes = svc;
        if (slotMinutes < 15) slotMinutes = 30;
        if (capacity < 1) capacity = 1;
        LocalDate d = LocalDate.parse(day.substring(0, 10));
        LocalDateTime cursor = d.atTime(Math.max(0, startHour), 0);
        LocalDateTime end = d.atTime(Math.min(23, endHour), 0);
        int n = 0;
        while (cursor.plusMinutes(slotMinutes).compareTo(end) <= 0) {
            LocalDateTime slotEnd = cursor.plusMinutes(slotMinutes);
            Timestamp startTs = Timestamp.valueOf(cursor);
            Timestamp endTs = Timestamp.valueOf(slotEnd);
            if (mapper().countSlotRange(SLOT, itemId, startTs, endTs) == 0) {
                mapper().insertSlot(SLOT, itemId, startTs, endTs, capacity);
                n++;
            }
            cursor = slotEnd;
        }
        return n;
    }

    public static Map<String, Object> reserve(String username, long slotId, String remark) {
        return reserve(username, slotId, remark, null);
    }

    public static Map<String, Object> reserve(
            String username, long slotId, String remark, Map<String, Object> extras) {
        requireEnabled();
        Map<String, Object> early = extras == null ? Map.of() : extras;
        boolean rangeHeld = false;
        long stayItemId = 0L;
        String stayFromHeld = str(early.get("stayFrom"));
        String stayToHeld = str(early.get("stayTo"));
        Map<String, Object> slot;
        if (BoardingStore.enabled()) {
            BoardingStore.assertStay(early);
            if (slotId > 0) {
                Map<String, Object> picked = getSlot(slotId);
                if (picked != null && picked.get("itemId") instanceof Number pickedItem) {
                    stayItemId = pickedItem.longValue();
                }
            }
            slotId = BoardingStore.holdFrom(early, stayItemId);
            rangeHeld = true;
            slot = getSlot(slotId);
            if (slot != null && slot.get("itemId") instanceof Number heldItem) {
                stayItemId = heldItem.longValue();
            }
        } else {
            slot = getSlot(slotId);
        }
        if (slot == null) throw new IllegalArgumentException("时段不存在");
        if (hasResvColumn("stay_from") && stayFromHeld.isBlank() && slot.get("startAt") != null) {
            String sa = String.valueOf(slot.get("startAt"));
            if (sa.length() >= 10) stayFromHeld = sa.substring(0, 10);
        }
        if (hasResvColumn("stay_to") && stayToHeld.isBlank() && slot.get("endAt") != null) {
            String ea = String.valueOf(slot.get("endAt"));
            if (ea.length() >= 10) stayToHeld = ea.substring(0, 10);
        }
        if (isPastSlot(slot)) {
            if (rangeHeld) BoardingStore.releaseRange(stayItemId, stayFromHeld, stayToHeld);
            throw new IllegalStateException("该时段已过，不可预约");
        }
        assertReserveAllowed(username, slot);
        boolean asWaitlist = false;
        if (!rangeHeld) {
            int capacity = ((Number) slot.get("capacity")).intValue();
            int booked = ((Number) slot.get("booked")).intValue();
            if (booked >= capacity) {
                if (hospitalWaitlistOn) asWaitlist = true;
                else throw new IllegalStateException("该时段已约满");
            }
        }
        if (mapper().countActiveResv(RESV, username, slotId) > 0) {
            throw new IllegalStateException("您已预约该时段");
        }

        String rawNote = remark == null ? "" : remark.trim();
        final String note = rawNote.length() > 255 ? rawNote.substring(0, 255) : rawNote;
        Map<String, Object> ex = extras == null ? Map.of() : extras;
        String plate = str(ex.get("plateNo"));
        assertParkingOverlap(plate, slot);
        assertMeetingMinDuration(slot);
        assertSalonServiceDuration(slot);
        String patient = str(ex.get("patientName"));
        String visit = str(ex.get("visitType"));
        assertHospitalIdLimit(slot, patient);
        String symptom = str(ex.get("symptomNote"));
        String subject = str(ex.get("subject"));
        int party = toInt(ex.get("partySize"));
        String guest = str(ex.get("guestName"));
        int guestCount = toInt(ex.get("guestCount"));
        String stylist = str(ex.get("preferredStylist"));
        int queue = toInt(ex.get("queueNo"));
        String noteFilled = note;
        if (noteFilled.isBlank()) {
            if (!plate.isBlank()) noteFilled = plate;
            else if (!patient.isBlank()) noteFilled = patient;
            else if (!guest.isBlank()) noteFilled = guest;
            else if (!subject.isBlank()) noteFilled = subject;
        }
        if (requireRemark && noteFilled.isBlank()) {
            throw new IllegalStateException("请填写备注后再预约");
        }
        requireResvColIfPresent("plate_no", "车牌号", !plate.isBlank());
        requireResvColIfPresent("patient_name", "就诊人", !patient.isBlank());
        requireResvColIfPresent("visit_type", "就诊类型", !visit.isBlank());
        requireResvColIfPresent("symptom_note", "症状说明", !symptom.isBlank());
        requireResvColIfPresent("subject", "主题", !subject.isBlank());
        requireResvColIfPresent("party_size", "人数", party > 0);
        requireResvColIfPresent("guest_name", "客人姓名", !guest.isBlank());
        requireResvColIfPresent("guest_count", "同住人数", guestCount > 0);
        requireResvColIfPresent("preferred_stylist", "指定技师", !stylist.isBlank());
        String careIds = BoardingStore.careIds(ex);
        requireResvColIfPresent("stay_from", "入住日期", !stayFromHeld.isBlank());
        requireResvColIfPresent("stay_to", "离店日期", !stayToHeld.isBlank());
        requireResvColIfPresent("care_ids", "特殊要求", !careIds.isBlank());
        requireResvColIfPresent("queue_no", "排队号", queue > 0);
        if (hotelNoticeRequired && hasResvColumn("notice_ack") && toInt(ex.get("noticeAck")) <= 0) {
            throw new IllegalStateException("请先勾选同意入住须知");
        }
        if (instrumentTrainingRequired && hasResvColumn("training_ack") && toInt(ex.get("trainingAck")) <= 0) {
            throw new IllegalStateException("请先勾选已完成上机培训");
        }
        final String noteFinal = noteFilled.length() > 255 ? noteFilled.substring(0, 255) : noteFilled;
        String statusToUse = asWaitlist
                ? "waitlisted"
                : (requireConfirm ? "pending" : "confirmed");
        ShootStore.assertBook(ex);
        LessonStore.assertRemain(username);
        String leaveDay = "";
        if (slot.get("startAt") != null) {
            String sa = String.valueOf(slot.get("startAt"));
            if (sa.length() >= 10) leaveDay = sa.substring(0, 10);
        }
        StaffRosterStore.assertNotOnLeave(stylist, leaveDay);
        if (!rangeHeld && !"waitlisted".equals(statusToUse)) {
            if (mapper().bumpBooked(SLOT, slotId) == 0) {
                if (hospitalWaitlistOn) statusToUse = "waitlisted";
                else throw new IllegalStateException("该时段已约满");
            }
        }
        final String initialStatus = statusToUse;
        LinkedHashMap<String, Object> extraCols = new LinkedHashMap<>();
        if (hasResvColumn("plate_no")) extraCols.put("plate_no", plate);
        if (hasResvColumn("patient_name")) extraCols.put("patient_name", patient);
        if (hasResvColumn("visit_type")) extraCols.put("visit_type", visit);
        if (hasResvColumn("symptom_note")) extraCols.put("symptom_note", symptom);
        if (hasResvColumn("subject")) extraCols.put("subject", subject);
        if (hasResvColumn("party_size")) extraCols.put("party_size", party);
        if (hasResvColumn("guest_name")) extraCols.put("guest_name", guest);
        if (hasResvColumn("guest_count")) extraCols.put("guest_count", guestCount);
        if (hasResvColumn("preferred_stylist")) extraCols.put("preferred_stylist", stylist);
        if (hasResvColumn("stay_from")) extraCols.put("stay_from", stayFromHeld);
        if (hasResvColumn("stay_to")) extraCols.put("stay_to", stayToHeld);
        if (hasResvColumn("care_ids")) extraCols.put("care_ids", careIds);
        if (hasResvColumn("queue_no")) {
            extraCols.put("queue_no", queue > 0 ? queue : (int) (slotId % 1000) + 1);
        }
        if (hasResvColumn("video_url")) extraCols.put("video_url", str(ex.get("videoUrl")));
        if (hasResvColumn("recording_url")) extraCols.put("recording_url", str(ex.get("recordingUrl")));
        if (hasResvColumn("service_tea")) extraCols.put("service_tea", toInt(ex.get("serviceTea")) > 0 ? 1 : 0);
        if (hasResvColumn("service_device")) extraCols.put("service_device", toInt(ex.get("serviceDevice")) > 0 ? 1 : 0);
        if (hasResvColumn("equip_borrow")) {
            extraCols.put("equip_borrow", toInt(ex.get("equipBorrow")) > 0 ? 1 : 0);
        }
        if (hasResvColumn("checkin_token") && !requireConfirm) {
            extraCols.put("checkin_token", newCheckinToken());
        }
        int priorReschedule = toInt(ex.get("rescheduleCount"));
        if (hasResvColumn("reschedule_count")) {
            extraCols.put("reschedule_count", Math.max(0, priorReschedule));
        }
        if (hasResvColumn("reschedule_fee_yuan") && priorReschedule > 0 && salonRescheduleFeeYuan > 0) {
            extraCols.put("reschedule_fee_yuan", BigDecimal.valueOf(salonRescheduleFeeYuan));
        } else if (hasResvColumn("reschedule_fee_yuan") && ex.get("rescheduleFeeYuan") != null) {
            extraCols.put("reschedule_fee_yuan", ex.get("rescheduleFeeYuan"));
        }
        if (hasResvColumn("id_no")) extraCols.put("id_no", str(ex.get("idNo")));
        if (hasResvColumn("deposit_yuan")) {
            extraCols.put("deposit_yuan", toDecimal(ex.get("depositYuan")));
        }
        if (hasResvColumn("balance_yuan")) {
            extraCols.put("balance_yuan", toDecimal(ex.get("balanceYuan")));
        }
        if (hasResvColumn("breakfast_vouchers")) {
            extraCols.put("breakfast_vouchers", Math.max(0, toInt(ex.get("breakfastVouchers"))));
        }
        if (hasResvColumn("notice_ack")) {
            extraCols.put("notice_ack", toInt(ex.get("noticeAck")) > 0 ? 1 : 0);
        }
        if (hasResvColumn("extra_bed")) {
            extraCols.put("extra_bed", toInt(ex.get("extraBed")) > 0 ? 1 : 0);
        }
        if (hasResvColumn("checkout_checklist") && ex.get("checkoutChecklist") != null) {
            String cl = str(ex.get("checkoutChecklist"));
            if (cl.length() > 512) cl = cl.substring(0, 512);
            extraCols.put("checkout_checklist", cl);
        }
        if (hasResvColumn("violation_hold_yuan")) {
            extraCols.put("violation_hold_yuan", toDecimal(ex.get("violationHoldYuan")));
        }
        if (hasResvColumn("violation_hold_note")) {
            String holdNote = str(ex.get("violationHoldNote"));
            if (holdNote.length() > 255) holdNote = holdNote.substring(0, 255);
            extraCols.put("violation_hold_note", holdNote);
        }
        if (hasResvColumn("inspect_ack")) {
            extraCols.put("inspect_ack", toInt(ex.get("inspectAck")) > 0 ? 1 : 0);
        }
        if (hasResvColumn("insurance_pkg")) {
            String pkg = str(ex.get("insurancePkg"));
            if (pkg.length() > 32) pkg = pkg.substring(0, 32);
            extraCols.put("insurance_pkg", pkg);
        }
        if (hasResvColumn("license_expire_on")) {
            String exp = str(ex.get("licenseExpireOn"));
            if (exp.length() >= 10) exp = exp.substring(0, 10);
            extraCols.put("license_expire_on", exp.isBlank() ? null : exp);
        }
        if (hasResvColumn("violation_attach") && ex.get("violationAttach") != null) {
            String att = str(ex.get("violationAttach"));
            if (att.length() > 512) att = att.substring(0, 512);
            extraCols.put("violation_attach", att);
        }
        if (hasResvColumn("training_ack")) {
            extraCols.put("training_ack", toInt(ex.get("trainingAck")) > 0 ? 1 : 0);
        }
        if (hasResvColumn("consumable_note") && ex.get("consumableNote") != null) {
            String cn = str(ex.get("consumableNote"));
            if (cn.length() > 512) cn = cn.substring(0, 512);
            extraCols.put("consumable_note", cn);
        }
        long resvId;
        try {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("resvTable", RESV);
            row.put("slotId", slotId);
            row.put("username", username);
            row.put("status", initialStatus);
            row.put("remark", noteFinal);
            row.put("extraCols", extraCols);
            row.put("createdAt", Timestamp.valueOf(LocalDateTime.now()));
            mapper().insertReservation(row);
            resvId = row.get("id") == null ? 0L : ((Number) row.get("id")).longValue();
            ShootStore.attach(resvId, ex);
            if (parkingPassOn && !plate.isBlank() && hasResvColumn("parking_pass_used")) {
                if (com.thesis.service.ParkingPassStore.spendOne(username)) {
                    MybatisSupport.db().update(
                            "UPDATE " + RESV + " SET parking_pass_used=1 WHERE id=?", resvId);
                }
            }
            try {
                LessonStore.spend(username, resvId);
            } catch (RuntimeException lessonEx) {
                try {
                    mapper().deleteReservation(RESV, resvId);
                } catch (Exception ignored) {
                }
                throw lessonEx;
            }
        } catch (RuntimeException e) {
            if (rangeHeld) BoardingStore.releaseRange(stayItemId, stayFromHeld, stayToHeld);
            else mapper().releaseBooked(SLOT, slotId);
            throw e;
        }
        if (OrderStore.enabled()) {
            long itemId = ((Number) slot.get("itemId")).longValue();
            Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
            String title = item == null ? "预约" : String.valueOf(item.get("title"));
            double price;
            if (BoardingStore.enabled() && item != null) {
                int days = BoardingStore.dayCount(str(ex.get("stayFrom")), str(ex.get("stayTo")));
                price = BoardingStore.stayYuan(
                        BigDecimal.valueOf(OrderStore.unitPriceOf(item)), days).doubleValue();
            } else if (ShootStore.enabled()) {
                price = ShootStore.bundlePrice(ex);
            } else {
                price = item == null ? 0 : OrderStore.unitPriceOf(item);
            }
            String body = title + " · " + slot.get("startAt") + " ~ " + slot.get("endAt");
            try {
                OrderStore.placeSimple(username, itemId, body, price, 1, "reservation:" + resvId, resvId);
            } catch (RuntimeException e) {
                try {
                    LessonStore.refund(resvId);
                    mapper().deleteReservation(RESV, resvId);
                } catch (Exception ignored) {
                }
                if (rangeHeld) BoardingStore.releaseRange(stayItemId, stayFromHeld, stayToHeld);
                else mapper().releaseBooked(SLOT, slotId);
                throw e;
            }
        }
        try {
            String who = UserStore.notifyWho(username, patient, guest);
            if (requireConfirm) {
                MessageStore.send(
                        username,
                        "预约已提交",
                        "已提交「" + slot.get("itemTitle") + "」" + slot.get("startAt") + " ~ " + slot.get("endAt")
                                + "，请等待确认。",
                        "reservation",
                        resvId);
                MessageStore.notifyAdmins(
                        "待确认预约",
                        who + " 提交了「" + slot.get("itemTitle") + "」"
                                + slot.get("startAt") + " ~ " + slot.get("endAt") + "，请确认。",
                        "reservation",
                        resvId);
            } else {
                MessageStore.send(
                        username,
                        "预约成功",
                        "已预约「" + slot.get("itemTitle") + "」" + slot.get("startAt") + " ~ " + slot.get("endAt"),
                        "reservation",
                        resvId);
                MessageStore.notifyAdmins(
                        "新预约",
                        who + " 预约了「" + slot.get("itemTitle") + "」"
                                + slot.get("startAt") + " ~ " + slot.get("endAt"),
                        "reservation",
                        resvId);
            }
        } catch (Exception ignored) {
        }
        return getReservation(resvId);
    }

    /** 管理端：pending / waitlisted → confirmed */
    public static Map<String, Object> confirm(long resvId) {
        requireEnabled();
        Map<String, Object> m = getReservation(resvId);
        if (m == null) throw new IllegalArgumentException("预约不存在");
        String st = String.valueOf(m.get("status"));
        if (!"pending".equals(st) && !"waitlisted".equals(st)) {
            throw new IllegalStateException("当前状态不可确认");
        }
        mapper().updateResvStatus(RESV, resvId, "confirmed");
        if (hasResvColumn("checkin_token")) {
            Map<String, Object> cur = getReservation(resvId);
            String tok = cur == null ? "" : str(cur.get("checkinToken"));
            if (tok.isBlank()) {
                MybatisSupport.db().update("UPDATE `" + RESV + "` SET checkin_token=? WHERE id=?", newCheckinToken(), resvId);
            }
        }
        try {
            String user = String.valueOf(m.get("username"));
            if ("waitlisted".equals(st)) {
                MessageStore.send(
                        user,
                        "候补已转正",
                        "您的候补预约「" + m.get("itemTitle") + "」" + m.get("startAt") + " ~ " + m.get("endAt")
                                + " 已转为正式预约，请按时到场。",
                        "reservation",
                        resvId);
            } else {
                MessageStore.send(
                        user,
                        "预约已确认",
                        "「" + m.get("itemTitle") + "」" + m.get("startAt") + " ~ " + m.get("endAt") + " 已确认。",
                        "reservation",
                        resvId);
            }
        } catch (Exception ignored) {
        }
        return getReservation(resvId);
    }

    /**
     * 履约办结：confirmed → completed（入场 / 就诊 / 到店 / 入住离店等，文案由 schema 决定）。
     * 不回补号源（时段已使用）；联动订单则一并完成。
     */
    public static Map<String, Object> complete(long resvId) {
        requireEnabled();
        Map<String, Object> m = getReservation(resvId);
        if (m == null) throw new IllegalArgumentException("预约不存在");
        if (!"confirmed".equals(String.valueOf(m.get("status")))) {
            throw new IllegalStateException("仅已确认的预约可办结");
        }
        if (meetingMinutesRequired && hasResvColumn("minutes_attach")) {
            String att = str(m.get("minutesAttach"));
            if (att.isBlank()) {
                throw new IllegalStateException("请先上传会议纪要附件再办结");
            }
        }
        if (hasResvColumn("entry_at")) {
            mapper().completeWithEntry(RESV, resvId);
        } else {
            mapper().updateResvStatus(RESV, resvId, "completed");
        }
        OrderStore.completeByReservation(resvId);
        try {
            Object itemId = m.get("itemId");
            if (itemId != null) {
                long iid = Long.parseLong(String.valueOf(itemId));
                VenueCleanStore.markDirtyAfterReservation(iid);
            }
        } catch (Exception ignored) {
        }
        try {
            String user = String.valueOf(m.get("username"));
            MessageStore.send(
                    user,
                    "预约已办结",
                    "「" + m.get("itemTitle") + "」" + m.get("startAt") + " ~ " + m.get("endAt") + " 已办结。",
                    "reservation",
                    resvId);
        } catch (Exception ignored) {
        }
        return getReservation(resvId);
    }

    public static Map<String, Object> cancel(long resvId, String username, boolean asAdmin) {
        requireEnabled();
        Map<String, Object> m = getReservation(resvId);
        if (m == null) throw new IllegalArgumentException("预约不存在");
        if (!asAdmin && !username.equals(String.valueOf(m.get("username")))) {
            throw new IllegalStateException("无权取消");
        }
        String st = String.valueOf(m.get("status"));
        if ("cancelled".equals(st)) return m;
        if (!"pending".equals(st) && !"confirmed".equals(st) && !"waitlisted".equals(st)) {
            throw new IllegalStateException("当前状态不可取消");
        }
        if (!asAdmin) {
            assertCancelFreeWindow(m);
        }
        mapper().updateResvStatus(RESV, resvId, "cancelled");
        if (!isPastSlot(m)) LessonStore.refund(resvId);
        if (!BoardingStore.releaseStay(RESV, SLOT, resvId)) {
            mapper().releaseBooked(SLOT, ((Number) m.get("slotId")).longValue());
        }
        OrderStore.cancelByReservation(resvId);
        if (parkingPassOn && hasResvColumn("parking_pass_used")) {
            Object used = m.get("parkingPassUsed");
            int u = 0;
            if (used instanceof Number) u = ((Number) used).intValue();
            else if (used != null) {
                try { u = Integer.parseInt(String.valueOf(used)); } catch (Exception ignored) {}
            }
            if (u > 0) {
                com.thesis.service.ParkingPassStore.refundOne(String.valueOf(m.get("username")));
            }
        }
        tryPromoteWaitlist(((Number) m.get("slotId")).longValue());
        return getReservation(resvId);
    }

    /**
     * 办结后评分 1～5 + 短评；仅本人、仅 completed、仅一次。
     */
    public static Map<String, Object> rate(long resvId, String username, int rating, String ratingRemark) {
        requireEnabled();
        if (!allowRating) throw new IllegalStateException("当前未开启评价");
        if (!hasResvColumn("rating")) throw new IllegalStateException("当前不支持评价");
        Map<String, Object> m = getReservation(resvId);
        if (m == null) throw new IllegalArgumentException("预约不存在");
        if (!username.equals(String.valueOf(m.get("username")))) {
            throw new IllegalStateException("只能评价本人的预约");
        }
        if (!"completed".equals(String.valueOf(m.get("status")))) {
            throw new IllegalStateException("仅办结后可评价");
        }
        Object existing = m.get("rating");
        if (existing != null && !"null".equals(String.valueOf(existing)) && !"".equals(String.valueOf(existing))) {
            throw new IllegalStateException("已评价过");
        }
        if (rating < 1 || rating > 5) throw new IllegalArgumentException("评分须为 1～5 星");
        String remark = ratingRemark == null ? "" : ratingRemark.trim();
        if (remark.length() > 200) remark = remark.substring(0, 200);
        mapper().rateReservation(RESV, resvId, rating, remark);
        return getReservation(resvId);
    }

    /**
     * 改约：取消原时段占坑并预约新时段（同一用户；保留备注等扩展字段）。
     */
    public static Map<String, Object> reschedule(long resvId, long newSlotId, String username) {
        requireEnabled();
        Map<String, Object> old = getReservation(resvId);
        if (old == null) throw new IllegalArgumentException("预约不存在");
        if (!username.equals(String.valueOf(old.get("username")))) {
            throw new IllegalStateException("无权改约");
        }
        String st = String.valueOf(old.get("status"));
        if (!"pending".equals(st) && !"confirmed".equals(st)) {
            throw new IllegalStateException("仅待确认/已确认可改约");
        }
        int used = toInt(old.get("rescheduleCount"));
        if (rescheduleMaxTimes > 0 && used >= rescheduleMaxTimes) {
            throw new IllegalStateException("改约次数已达上限（" + rescheduleMaxTimes + " 次）");
        }
        long oldSlot = ((Number) old.get("slotId")).longValue();
        if (oldSlot == newSlotId) throw new IllegalStateException("请选择不同时段");
        Map<String, Object> extras = new LinkedHashMap<>();
        extras.put("plateNo", old.get("plateNo"));
        extras.put("patientName", old.get("patientName"));
        extras.put("visitType", old.get("visitType"));
        extras.put("symptomNote", old.get("symptomNote"));
        extras.put("subject", old.get("subject"));
        extras.put("partySize", old.get("partySize"));
        extras.put("guestName", old.get("guestName"));
        extras.put("guestCount", old.get("guestCount"));
        extras.put("preferredStylist", old.get("preferredStylist"));
        extras.put("stayFrom", old.get("stayFrom"));
        extras.put("stayTo", old.get("stayTo"));
        extras.put("idNo", old.get("idNo"));
        extras.put("depositYuan", old.get("depositYuan"));
        extras.put("balanceYuan", old.get("balanceYuan"));
        extras.put("breakfastVouchers", old.get("breakfastVouchers"));
        extras.put("noticeAck", old.get("noticeAck"));
        extras.put("extraBed", old.get("extraBed"));
        extras.put("checkoutChecklist", old.get("checkoutChecklist"));
        extras.put("violationHoldYuan", old.get("violationHoldYuan"));
        extras.put("violationHoldNote", old.get("violationHoldNote"));
        extras.put("inspectAck", old.get("inspectAck"));
        extras.put("insurancePkg", old.get("insurancePkg"));
        extras.put("licenseExpireOn", old.get("licenseExpireOn"));
        extras.put("violationAttach", old.get("violationAttach"));
        extras.put("trainingAck", old.get("trainingAck"));
        extras.put("consumableNote", old.get("consumableNote"));
        extras.put("rescheduleCount", used + 1);
        String remark = String.valueOf(old.getOrDefault("remark", ""));
        cancel(resvId, username, true);
        try {
            return reserve(username, newSlotId, remark, extras);
        } catch (RuntimeException e) {
            throw new IllegalStateException("原预约已取消，但新时段预约失败：" + e.getMessage());
        }
    }

    public static Map<String, Object> getReservation(long id) {
        requireEnabled();
        Map<String, Object> raw = mapper().selectResvById(RESV, id);
        if (raw == null) return null;
        return enrichResv(shapeResv(raw));
    }

    public static Map<String, Object> pageReservations(String username, String status, int page, int size) {
        requireEnabled();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        String u = username == null || username.isBlank() ? null : username;
        String st = status == null || status.isBlank() ? null : status;
        PageHelper.startPage(page, size);
        List<Map<String, Object>> raw = mapper().selectReservations(RESV, u, st);
        PageInfo<Map<String, Object>> pi = new PageInfo<>(raw == null ? List.of() : raw);
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> r : pi.getList()) list.add(enrichResv(shapeResv(r)));
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", pi.getTotal());
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    public static Map<String, Object> dashboard() {
        if (!enabled) return Map.of();
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("pendingReservations", mapper().countByStatus(RESV, "pending"));
        m.put("confirmedReservations", mapper().countByStatus(RESV, "confirmed"));
        m.put("completedReservations", mapper().countByStatus(RESV, "completed"));
        return m;
    }

    public static Map<String, Object> chartStats() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("statusSeries", List.of());
        out.put("trendSeries", List.of());
        if (!enabled) return out;
        try {
            List<Map<String, Object>> status = mapper().selectStatusSeries(RESV);
            out.put("statusSeries", status == null ? List.of() : status);
            List<Map<String, Object>> trend = mapper().selectTrendSeries(RESV);
            out.put("trendSeries", trend == null ? List.of() : trend);
        } catch (Exception ignored) {
        }
        return out;
    }

    private static Map<String, Object> shapeSlot(Map<String, Object> raw) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", raw.get("id"));
        m.put("itemId", first(raw, "itemId", "item_id"));
        m.put("startAt", fmt(first(raw, "startAt", "start_at")));
        m.put("endAt", fmt(first(raw, "endAt", "end_at")));
        m.put("capacity", first(raw, "capacity"));
        m.put("booked", first(raw, "booked"));
        return m;
    }

    private static boolean isPastSlot(Map<String, Object> slot) {
        String sa = slot == null ? "" : String.valueOf(slot.get("startAt"));
        if (sa == null || sa.isBlank() || "null".equalsIgnoreCase(sa)) return false;
        try {
            String norm = sa.length() >= 19 ? sa.substring(0, 19) : sa;
            LocalDateTime t = LocalDateTime.parse(norm.replace(' ', 'T'));
            return !t.isAfter(LocalDateTime.now());
        } catch (Exception e) {
            try {
                return !LocalDateTime.parse(sa, FMT).isAfter(LocalDateTime.now());
            } catch (Exception ignored) {
                // 脏 start_at：视为已过，禁止再约
                return true;
            }
        }
    }

    private static Map<String, Object> enrichSlot(Map<String, Object> slot) {
        Map<String, Object> m = new LinkedHashMap<>(slot);
        long itemId = ((Number) slot.get("itemId")).longValue();
        Map<String, Object> item = ArchiveStore.getItem(itemId);
        m.put("itemTitle", item == null ? "" : item.get("title"));
        m.put("remain", Math.max(0, ((Number) slot.get("capacity")).intValue()
                - ((Number) slot.get("booked")).intValue()));
        return m;
    }

    private static Map<String, Object> shapeResv(Map<String, Object> raw) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", raw.get("id"));
        m.put("slotId", first(raw, "slotId", "slot_id"));
        m.put("username", raw.get("username"));
        m.put("status", raw.get("status"));
        m.put("remark", raw.get("remark"));
        m.put("plateNo", str(first(raw, "plateNo", "plate_no")));
        m.put("patientName", str(first(raw, "patientName", "patient_name")));
        m.put("visitType", str(first(raw, "visitType", "visit_type")));
        m.put("symptomNote", str(first(raw, "symptomNote", "symptom_note")));
        m.put("subject", str(first(raw, "subject")));
        m.put("recordingUrl", str(first(raw, "recordingUrl", "recording_url")));
        m.put("videoUrl", str(first(raw, "videoUrl", "video_url")));
        m.put("doorCode", str(first(raw, "doorCode", "door_code")));
        m.put("serviceTea", toInt(first(raw, "serviceTea", "service_tea")));
        m.put("serviceDevice", toInt(first(raw, "serviceDevice", "service_device")));
        m.put("equipBorrow", toInt(first(raw, "equipBorrow", "equip_borrow")));
        m.put("minutesAttach", str(first(raw, "minutesAttach", "minutes_attach")));
        m.put("meetingStage", str(first(raw, "meetingStage", "meeting_stage")));
        m.put("checkinToken", str(first(raw, "checkinToken", "checkin_token")));
        Object feeRaw = first(raw, "rescheduleFeeYuan", "reschedule_fee_yuan");
        m.put("rescheduleFeeYuan", feeRaw == null ? 0 : feeRaw);
        m.put("partySize", toInt(first(raw, "partySize", "party_size")));
        m.put("guestName", str(first(raw, "guestName", "guest_name")));
        m.put("guestCount", toInt(first(raw, "guestCount", "guest_count")));
        m.put("preferredStylist", str(first(raw, "preferredStylist", "preferred_stylist")));
        m.put("queueNo", toInt(first(raw, "queueNo", "queue_no")));
        m.put("stayFrom", str(first(raw, "stayFrom", "stay_from")));
        m.put("stayTo", str(first(raw, "stayTo", "stay_to")));
        String idNo = str(first(raw, "idNo", "id_no"));
        m.put("idNo", idNo);
        m.put("idNoMasked", maskIdNo(idNo));
        Object depRaw = first(raw, "depositYuan", "deposit_yuan");
        m.put("depositYuan", depRaw == null ? 0 : depRaw);
        Object balRaw = first(raw, "balanceYuan", "balance_yuan");
        m.put("balanceYuan", balRaw == null ? 0 : balRaw);
        m.put("breakfastVouchers", toInt(first(raw, "breakfastVouchers", "breakfast_vouchers")));
        m.put("noticeAck", toInt(first(raw, "noticeAck", "notice_ack")));
        m.put("extraBed", toInt(first(raw, "extraBed", "extra_bed")));
        Object lateRaw = first(raw, "lateCheckoutFeeYuan", "late_checkout_fee_yuan");
        m.put("lateCheckoutFeeYuan", lateRaw == null ? 0 : lateRaw);
        m.put("checkoutChecklist", str(first(raw, "checkoutChecklist", "checkout_checklist")));
        Object vhRaw = first(raw, "violationHoldYuan", "violation_hold_yuan");
        m.put("violationHoldYuan", vhRaw == null ? 0 : vhRaw);
        m.put("violationHoldNote", str(first(raw, "violationHoldNote", "violation_hold_note")));
        m.put("inspectAck", toInt(first(raw, "inspectAck", "inspect_ack")));
        m.put("trainingAck", toInt(first(raw, "trainingAck", "training_ack")));
        m.put("consumableNote", str(first(raw, "consumableNote", "consumable_note")));
        Object moRaw = first(raw, "mileageOverFeeYuan", "mileage_over_fee_yuan");
        m.put("mileageOverFeeYuan", moRaw == null ? 0 : moRaw);
        m.put("insurancePkg", str(first(raw, "insurancePkg", "insurance_pkg")));
        m.put("licenseExpireOn", str(first(raw, "licenseExpireOn", "license_expire_on")));
        m.put("violationAttach", str(first(raw, "violationAttach", "violation_attach")));
        Object etcRaw = first(raw, "etcFeeYuan", "etc_fee_yuan");
        m.put("etcFeeYuan", etcRaw == null ? 0 : etcRaw);
        m.put("rescheduleCount", toInt(first(raw, "rescheduleCount", "reschedule_count")));
        m.put("remindSent", toInt(first(raw, "remindSent", "remind_sent")));
        m.put("noShow", toInt(first(raw, "noShow", "no_show")));
        m.put("lateFlag", toInt(first(raw, "lateFlag", "late_flag")));
        m.put("checkedInAt", fmt(first(raw, "checkedInAt", "checked_in_at")));
        m.put("entryAt", fmt(first(raw, "entryAt", "entry_at")));
        m.put("exitAt", fmt(first(raw, "exitAt", "exit_at")));
        m.put("overtimeFeeYuan", first(raw, "overtimeFeeYuan", "overtime_fee_yuan"));
        m.put("durationFeeYuan", first(raw, "durationFeeYuan", "duration_fee_yuan"));
        Object ppu = first(raw, "parkingPassUsed", "parking_pass_used");
        m.put("parkingPassUsed", ppu == null ? 0 : ppu);
        Object rating = first(raw, "rating");
        if (rating == null || "".equals(String.valueOf(rating)) || "null".equalsIgnoreCase(String.valueOf(rating))) {
            m.put("rating", null);
        } else {
            m.put("rating", toInt(rating));
        }
        m.put("ratingRemark", str(first(raw, "ratingRemark", "rating_remark")));
        m.put("ratedAt", fmt(first(raw, "ratedAt", "rated_at")));
        m.put("createdAt", fmt(first(raw, "createdAt", "created_at")));
        return m;
    }

    private static Object first(Map<String, Object> raw, String... keys) {
        for (String k : keys) {
            if (raw.containsKey(k) && raw.get(k) != null) return raw.get(k);
        }
        return null;
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static int toInt(Object o) {
        if (o == null) return 0;
        if (o instanceof Number n) return n.intValue();
        try {
            return Integer.parseInt(String.valueOf(o).trim());
        } catch (Exception e) {
            return 0;
        }
    }

    private static void requireResvColIfPresent(String col, String label, boolean present) {
        if (!present) return;
        if (!hasResvColumn(col)) {
            throw new IllegalStateException("系统未配置「" + label + "」字段，无法保存预约信息");
        }
    }

    private static boolean hasResvColumn(String col) {
        try {
            Integer n = schema().countColumn(RESV, col);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    private static Map<String, Object> enrichResv(Map<String, Object> resv) {
        Map<String, Object> m = new LinkedHashMap<>(resv);
        Map<String, Object> slot = getSlot(((Number) resv.get("slotId")).longValue());
        if (slot != null) {
            m.put("startAt", slot.get("startAt"));
            m.put("endAt", slot.get("endAt"));
            m.put("itemId", slot.get("itemId"));
            m.put("itemTitle", slot.get("itemTitle"));
            m.put("title", slot.get("itemTitle"));
        }
        Object u = m.get("username");
        if (u != null && !String.valueOf(u).isBlank()) {
            m.put("displayName", UserStore.displayName(String.valueOf(u)));
        }
        return m;
    }

    public static Map<String, Object> checkIn(long resvId, String username, boolean asAdmin) {
        return checkIn(resvId, username, asAdmin, null);
    }

    public static Map<String, Object> checkIn(
            long resvId, String username, boolean asAdmin, String checkinCode) {
        requireEnabled();
        Map<String, Object> m = getReservation(resvId);
        if (m == null) throw new IllegalArgumentException("预约不存在");
        if (!asAdmin && !username.equals(String.valueOf(m.get("username")))) {
            throw new IllegalStateException("无权签到");
        }
        String st = String.valueOf(m.get("status"));
        if (!"confirmed".equals(st) && !"pending".equals(st)) {
            throw new IllegalStateException("当前状态不可签到");
        }
        if (m.get("checkedInAt") != null
                && !String.valueOf(m.get("checkedInAt")).isBlank()
                && !"null".equalsIgnoreCase(String.valueOf(m.get("checkedInAt")))) {
            return m;
        }
        assertCheckinCode(m, checkinCode, asAdmin);
        boolean late = false;
        try {
            String sa = String.valueOf(m.get("startAt"));
            if (sa != null && !sa.isBlank() && !"null".equalsIgnoreCase(sa)) {
                String norm = sa.length() >= 19 ? sa.substring(0, 19) : sa;
                LocalDateTime start = LocalDateTime.parse(norm.replace(' ', 'T'));
                late = LocalDateTime.now().isAfter(start.plusMinutes(Math.max(0, lateGraceMinutes)));
            }
        } catch (Exception ignored) {
        }
        if (!hasResvColumn("checked_in_at")) throw new IllegalStateException("当前不支持签到");
        mapper().checkInReservation(RESV, resvId, late ? 1 : 0);
        return getReservation(resvId);
    }

    public static Map<String, Object> markNoShow(long resvId) {
        requireEnabled();
        Map<String, Object> m = getReservation(resvId);
        if (m == null) throw new IllegalArgumentException("预约不存在");
        String st = String.valueOf(m.get("status"));
        if (!"confirmed".equals(st) && !"pending".equals(st)) {
            throw new IllegalStateException("当前状态不可记爽约");
        }
        if (hasResvColumn("no_show")) {
            mapper().markNoShow(RESV, resvId);
        } else {
            mapper().updateResvStatus(RESV, resvId, "cancelled");
        }
        if (!BoardingStore.releaseStay(RESV, SLOT, resvId)) {
            mapper().releaseBooked(SLOT, ((Number) m.get("slotId")).longValue());
        }
        OrderStore.cancelByReservation(resvId);
        return getReservation(resvId);
    }

    public static int remindDueSweep() {
        if (!enabled || remindAheadMinutes <= 0 || !hasResvColumn("remind_sent")) return 0;
        List<Map<String, Object>> rows;
        try {
            rows = mapper().selectRemindDue(RESV, SLOT, remindAheadMinutes);
        } catch (Exception e) {
            return 0;
        }
        if (rows == null) return 0;
        int n = 0;
        for (Map<String, Object> row : rows) {
            long id = ((Number) first(row, "id")).longValue();
            try {
                String title = "";
                Object iid = first(row, "itemId", "item_id");
                if (iid != null) {
                    Map<String, Object> item = ArchiveStore.getItemRaw(((Number) iid).longValue());
                    if (item != null) title = String.valueOf(item.getOrDefault("title", ""));
                }
                MessageStore.send(
                        String.valueOf(first(row, "username")),
                        "预约即将开始",
                        "「" + title + "」" + fmt(first(row, "startAt", "start_at")) + " ~ "
                                + fmt(first(row, "endAt", "end_at")) + " 即将开始，请按时到场。",
                        "reservation",
                        id);
                mapper().markRemindSent(RESV, id);
                n++;
            } catch (Exception ignored) {
            }
        }
        return n;
    }

    public static List<Map<String, Object>> dayFill(long itemId, String month) {
        requireEnabled();
        String ym = month == null ? "" : month.trim();
        if (ym.length() < 7) ym = LocalDate.now().toString().substring(0, 7);
        else ym = ym.substring(0, 7);
        try {
            List<Map<String, Object>> raw = mapper().selectDayFill(SLOT, itemId, ym + "%");
            List<Map<String, Object>> out = new ArrayList<>();
            for (Map<String, Object> r : raw) {
                int cap = toInt(first(r, "capacity"));
                int booked = toInt(first(r, "booked"));
                int remain = Math.max(0, cap - booked);
                String tone = "ok";
                if (remain <= 0) tone = "full";
                else if (cap > 0 && remain * 1.0 / cap <= 0.25) tone = "warn";
                else if (remain <= 2) tone = "warn";
                Map<String, Object> row = new LinkedHashMap<>();
                row.put("day", first(r, "day"));
                row.put("capacity", cap);
                row.put("booked", booked);
                row.put("remain", remain);
                row.put("tone", tone);
                out.add(row);
            }
            return out;
        } catch (Exception e) {
            return List.of();
        }
    }

    private static void assertReserveAllowed(String username, Map<String, Object> slot) {
        if (reserveBlacklistOn) {
            com.thesis.service.ReserveBlacklistStore.assertNotBlocked(username);
        }
        if (noShowLimit > 0 && hasResvColumn("no_show")) {
            int n = mapper().countNoShow(RESV, username);
            if (n >= noShowLimit) {
                throw new IllegalStateException("因多次爽约，暂时无法预约，请先提交申诉");
            }
        }
        assertNotInMaintain(slot);
    }

    private static void assertNotInMaintain(Map<String, Object> slot) {
        if (slot == null || slot.get("itemId") == null) return;
        long itemId;
        try {
            itemId = Long.parseLong(String.valueOf(slot.get("itemId")));
        } catch (Exception e) {
            return;
        }
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) return;
        String from = str(item.get("maintainFrom"));
        if (from.isBlank()) from = str(item.get("maintain_from"));
        String to = str(item.get("maintainTo"));
        if (to.isBlank()) to = str(item.get("maintain_to"));
        if (from.isBlank() && to.isBlank()) return;
        String day = "";
        Object sa = slot.get("startAt");
        if (sa != null) day = String.valueOf(sa).trim();
        if (day.length() >= 10) day = day.substring(0, 10);
        else return;
        String fromDay = from.isBlank() ? "" : from.substring(0, Math.min(10, from.length()));
        String toDay = to.isBlank() ? "" : to.substring(0, Math.min(10, to.length()));
        boolean afterFrom = fromDay.isBlank() || day.compareTo(fromDay) >= 0;
        boolean beforeTo = toDay.isBlank() || day.compareTo(toDay) <= 0;
        if (afterFrom && beforeTo) {
            throw new IllegalStateException("该资源在维护期内暂不可约，请换一天或其它资源");
        }
    }

    private static void assertCancelFreeWindow(Map<String, Object> m) {
        String sa = m == null ? "" : String.valueOf(m.get("startAt"));
        if (sa == null || sa.isBlank() || "null".equalsIgnoreCase(sa)) return;
        try {
            String norm = sa.length() >= 19 ? sa.substring(0, 19) : sa;
            LocalDateTime start = LocalDateTime.parse(norm.replace(' ', 'T'));
            if (hospitalCancelCutoffMinutes > 0) {
                if (LocalDateTime.now().plusMinutes(hospitalCancelCutoffMinutes).isAfter(start)) {
                    throw new IllegalStateException(
                            "开诊前不足 " + hospitalCancelCutoffMinutes + " 分钟，无法自行退号，请联系窗口");
                }
                return;
            }
            if (cancelFreeHours <= 0) return;
            if (LocalDateTime.now().plusHours(cancelFreeHours).isAfter(start)) {
                throw new IllegalStateException(
                        "距开始不足 " + cancelFreeHours + " 小时，无法自行取消，请联系管理员");
            }
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception ignored) {
        }
    }



    private static void assertMeetingMinDuration(Map<String, Object> slot) {
        if (meetingMinDurationMinutes <= 0 || slot == null) return;
        try {
            String sa = String.valueOf(slot.get("startAt"));
            String ea = String.valueOf(slot.get("endAt"));
            if (sa == null || ea == null || sa.isBlank() || ea.isBlank()) return;
            String sn = sa.length() >= 19 ? sa.substring(0, 19) : sa;
            String en = ea.length() >= 19 ? ea.substring(0, 19) : ea;
            LocalDateTime start = LocalDateTime.parse(sn.replace(' ', 'T'));
            LocalDateTime end = LocalDateTime.parse(en.replace(' ', 'T'));
            long mins = java.time.Duration.between(start, end).toMinutes();
            int need = meetingMinDurationMinutes;
            if (slot.get("itemId") != null) {
                Map<String, Object> item = ArchiveStore.getItemRaw(((Number) slot.get("itemId")).longValue());
                if (item != null) {
                    Object md = item.get("minDurationMinutes");
                    if (md == null) md = item.get("min_duration_minutes");
                    if (md != null) {
                        try {
                            int v = Integer.parseInt(String.valueOf(md));
                            if (v > 0) need = v;
                        } catch (Exception ignored) {
                        }
                    }
                }
            }
            if (mins < need) {
                throw new IllegalStateException("该时段短于最低预约时长 " + need + " 分钟，请改选");
            }
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception ignored) {
        }
    }

    /** SALON：时段长度须覆盖服务项目时长 */
    private static void assertSalonServiceDuration(Map<String, Object> slot) {
        if (slot == null || slot.get("itemId") == null) return;
        try {
            Map<String, Object> item = ArchiveStore.getItemRaw(((Number) slot.get("itemId")).longValue());
            if (item == null) return;
            Object sm = item.get("serviceMinutes");
            if (sm == null) sm = item.get("service_minutes");
            int need = toInt(sm);
            if (need <= 0) return;
            String sa = String.valueOf(slot.get("startAt"));
            String ea = String.valueOf(slot.get("endAt"));
            if (sa == null || ea == null || sa.isBlank() || ea.isBlank()) return;
            String sn = sa.length() >= 19 ? sa.substring(0, 19) : sa;
            String en = ea.length() >= 19 ? ea.substring(0, 19) : ea;
            LocalDateTime start = LocalDateTime.parse(sn.replace(' ', 'T'));
            LocalDateTime end = LocalDateTime.parse(en.replace(' ', 'T'));
            long mins = java.time.Duration.between(start, end).toMinutes();
            if (mins < need) {
                throw new IllegalStateException("该时段短于服务时长 " + need + " 分钟，请改选");
            }
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception ignored) {
        }
    }

    public static int visitCount(String username) {
        requireEnabled();
        if (username == null || username.isBlank()) return 0;
        try {
            Integer n = MybatisSupport.db().queryForObject(
                    "SELECT COUNT(*) FROM `" + RESV + "` WHERE username=? AND checked_in_at IS NOT NULL",
                    Integer.class,
                    username);
            return n == null ? 0 : n;
        } catch (Exception e) {
            return 0;
        }
    }

    public static Map<String, Object> registerRescheduleFee(long resvId, BigDecimal yuan) {
        requireEnabled();
        Map<String, Object> m = getReservation(resvId);
        if (m == null) throw new IllegalArgumentException("预约不存在");
        if (!hasResvColumn("reschedule_fee_yuan")) throw new IllegalStateException("当前不支持改约手续费");
        BigDecimal fee = yuan;
        if (fee == null || fee.compareTo(BigDecimal.ZERO) <= 0) {
            fee = BigDecimal.valueOf(Math.max(salonRescheduleFeeYuan, 0));
        }
        if (fee.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("请填写改约手续费金额");
        }
        MybatisSupport.db().update("UPDATE `" + RESV + "` SET reschedule_fee_yuan=? WHERE id=?", fee, resvId);
        return getReservation(resvId);
    }

    public static List<Map<String, Object>> listSlotOccupants(long slotId) {
        requireEnabled();
        if (slotId <= 0) return List.of();
        try {
            return MybatisSupport.db().query(
                    "SELECT id, username, subject, status, party_size FROM `" + RESV + "` "
                            + "WHERE slot_id=? AND status IN ('pending','confirmed','waitlisted','completed') ORDER BY id",
                    (rs, i) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("id", rs.getLong("id"));
                        row.put("username", rs.getString("username"));
                        try { row.put("subject", rs.getString("subject")); } catch (Exception e) { row.put("subject", ""); }
                        row.put("status", rs.getString("status"));
                        try { row.put("partySize", rs.getInt("party_size")); } catch (Exception e) { row.put("partySize", 0); }
                        return row;
                    },
                    slotId);
        } catch (Exception e) {
            return List.of();
        }
    }

    public static int generateWeeklySlots(
            long itemId, String startDay, int weeks, int startHour, int endHour, int slotMinutes, int capacity) {
        requireEnabled();
        if (weeks < 1) weeks = 1;
        if (weeks > 12) weeks = 12;
        LocalDate day = LocalDate.parse(startDay);
        int total = 0;
        for (int w = 0; w < weeks; w++) {
            total += generateDaySlots(itemId, day.plusWeeks(w).toString(), startHour, endHour, slotMinutes, capacity);
        }
        return total;
    }

    public static Map<String, Object> patchMeeting(
            long resvId, String doorCode, String recordingUrl, String videoUrl, String stage, String minutesAttach) {
        requireEnabled();
        Map<String, Object> m = getReservation(resvId);
        if (m == null) throw new IllegalArgumentException("预约不存在");
        if (doorCode != null && hasResvColumn("door_code")) {
            String v = doorCode.trim();
            if (v.length() > 32) v = v.substring(0, 32);
            MybatisSupport.db().update("UPDATE `" + RESV + "` SET door_code=? WHERE id=?", v, resvId);
        }
        if (recordingUrl != null && hasResvColumn("recording_url")) {
            String v = recordingUrl.trim();
            if (v.length() > 255) v = v.substring(0, 255);
            MybatisSupport.db().update("UPDATE `" + RESV + "` SET recording_url=? WHERE id=?", v, resvId);
        }
        if (videoUrl != null && hasResvColumn("video_url")) {
            String v = videoUrl.trim();
            if (v.length() > 255) v = v.substring(0, 255);
            MybatisSupport.db().update("UPDATE `" + RESV + "` SET video_url=? WHERE id=?", v, resvId);
        }
        if (stage != null && hasResvColumn("meeting_stage")) {
            String v = stage.trim();
            if (!v.isEmpty() && !"in_progress".equals(v) && !"ended".equals(v)) {
                throw new IllegalArgumentException("会议状态不正确");
            }
            MybatisSupport.db().update("UPDATE `" + RESV + "` SET meeting_stage=? WHERE id=?", v, resvId);
        }
        if (minutesAttach != null && hasResvColumn("minutes_attach")) {
            String v = minutesAttach.trim();
            if (v.length() > 512) v = v.substring(0, 512);
            MybatisSupport.db().update("UPDATE `" + RESV + "` SET minutes_attach=? WHERE id=?", v, resvId);
        }
        return getReservation(resvId);
    }

    private static String newCheckinToken() {
        return "M" + String.format("%05d", (int) (Math.random() * 100000));
    }


    private static void assertParkingOverlap(String plate, Map<String, Object> slot) {
        if (plate == null || plate.isBlank() || slot == null || !hasResvColumn("plate_no")) return;
        Object start = slot.get("startAt");
        Object end = slot.get("endAt");
        if (start == null || end == null) return;
        String sa = String.valueOf(start);
        String ea = String.valueOf(end);
        String saN = sa.replace('T', ' ');
        String eaN = ea.replace('T', ' ');
        if (saN.length() >= 19) saN = saN.substring(0, 19);
        if (eaN.length() >= 19) eaN = eaN.substring(0, 19);
        try {
            Integer n = MybatisSupport.db().queryForObject(
                    "SELECT COUNT(*) FROM `" + RESV + "` r JOIN `" + SLOT + "` s ON r.slot_id=s.id "
                            + "WHERE r.plate_no=? AND r.status IN ('pending','confirmed') "
                            + "AND s.start_at < ? AND s.end_at > ?",
                    Integer.class, plate, eaN, saN);
            if (n != null && n > 0) {
                throw new IllegalStateException("同一车牌在重叠时段不可重复预约，请改选其它时段");
            }
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception ignored) {
        }
    }

    public static Map<String, Object> markExit(long resvId) {
        requireEnabled();
        Map<String, Object> m = getReservation(resvId);
        if (m == null) throw new IllegalArgumentException("预约不存在");
        if (!hasResvColumn("exit_at")) throw new IllegalStateException("当前不支持离场登记");
        String st = String.valueOf(m.get("status"));
        if (!"completed".equals(st) && !"confirmed".equals(st)) {
            throw new IllegalStateException("请先登记入场再离场");
        }
        if (m.get("exitAt") != null
                && !String.valueOf(m.get("exitAt")).isBlank()
                && !"null".equalsIgnoreCase(String.valueOf(m.get("exitAt")))) {
            return m;
        }
        Object entry = m.get("entryAt");
        LocalDateTime entryDt = null;
        try {
            if (entry != null) {
                String es = String.valueOf(entry);
                String norm = es.length() >= 19 ? es.substring(0, 19) : es;
                entryDt = LocalDateTime.parse(norm.replace(' ', 'T'));
            }
        } catch (Exception ignored) {
        }
        if (entryDt == null) {
            if (hasResvColumn("entry_at")) {
                MybatisSupport.db().update(
                        "UPDATE `" + RESV + "` SET status='completed', entry_at=NOW() WHERE id=?", resvId);
                entryDt = LocalDateTime.now();
            }
        }
        LocalDateTime exitDt = LocalDateTime.now();
        java.math.BigDecimal fee = java.math.BigDecimal.ZERO;
        if (parkingHourlyYuan > 0 && entryDt != null) {
            long minutes = java.time.Duration.between(entryDt, exitDt).toMinutes();
            if (minutes < 0) minutes = 0;
            long hours = (minutes + 59) / 60;
            if (hours < 1) hours = 1;
            fee = java.math.BigDecimal.valueOf(parkingHourlyYuan).multiply(java.math.BigDecimal.valueOf(hours));
        }
        if (hasResvColumn("duration_fee_yuan")) {
            MybatisSupport.db().update(
                    "UPDATE `" + RESV + "` SET exit_at=?, duration_fee_yuan=?, status='completed' WHERE id=?",
                    java.sql.Timestamp.valueOf(exitDt), fee, resvId);
        } else {
            MybatisSupport.db().update(
                    "UPDATE `" + RESV + "` SET exit_at=?, status='completed' WHERE id=?",
                    java.sql.Timestamp.valueOf(exitDt), resvId);
        }
        return getReservation(resvId);
    }

    public static Map<String, Object> registerOvertimeFee(long resvId, java.math.BigDecimal yuan) {
        requireEnabled();
        Map<String, Object> m = getReservation(resvId);
        if (m == null) throw new IllegalArgumentException("预约不存在");
        if (!hasResvColumn("overtime_fee_yuan")) throw new IllegalStateException("当前不支持超时加收");
        java.math.BigDecimal fee = yuan;
        if (fee == null || fee.compareTo(java.math.BigDecimal.ZERO) <= 0) {
            int def = Math.max(parkingOvertimeYuan, instrumentOvertimeYuan);
            fee = java.math.BigDecimal.valueOf(Math.max(def, 0));
        }
        if (fee.compareTo(java.math.BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("请填写加收金额");
        }
        MybatisSupport.db().update("UPDATE `" + RESV + "` SET overtime_fee_yuan=? WHERE id=?", fee, resvId);
        return getReservation(resvId);
    }


    /** 续住：改离店日 */
    public static Map<String, Object> extendStay(long resvId, String username, boolean asAdmin, String newStayTo) {
        requireEnabled();
        Map<String, Object> m = getReservation(resvId);
        if (m == null) throw new IllegalArgumentException("预约不存在");
        if (!asAdmin && !username.equals(String.valueOf(m.get("username")))) {
            throw new IllegalStateException("无权续住");
        }
        if (!hasResvColumn("stay_to")) throw new IllegalStateException("当前不支持续住");
        String st = String.valueOf(m.get("status"));
        if (!"pending".equals(st) && !"confirmed".equals(st)) {
            throw new IllegalStateException("当前状态不可续住");
        }
        String to = newStayTo == null ? "" : newStayTo.trim();
        if (to.length() < 10) throw new IllegalArgumentException("请填写新的离店日期");
        to = to.substring(0, 10);
        String from = str(m.get("stayFrom"));
        if (!from.isBlank() && to.compareTo(from) <= 0) {
            throw new IllegalArgumentException("离店日须晚于入住日");
        }
        String oldTo = str(m.get("stayTo"));
        if (!oldTo.isBlank() && to.compareTo(oldTo) <= 0) {
            throw new IllegalArgumentException("续住离店日须晚于原离店日");
        }
        db().update("UPDATE " + RESV + " SET stay_to=? WHERE id=?", to, resvId);
        return getReservation(resvId);
    }

    /** 管理端登记延迟退房加收 */
    public static Map<String, Object> registerLateCheckoutFee(long resvId, BigDecimal yuan) {
        requireEnabled();
        Map<String, Object> m = getReservation(resvId);
        if (m == null) throw new IllegalArgumentException("预约不存在");
        if (!hasResvColumn("late_checkout_fee_yuan")) {
            throw new IllegalStateException("当前不支持延迟退房加收");
        }
        BigDecimal fee = yuan;
        if (fee == null || fee.compareTo(BigDecimal.ZERO) <= 0) {
            fee = BigDecimal.valueOf(Math.max(hotelLateCheckoutFeeYuan, 0));
        }
        if (fee.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("请填写加收金额");
        }
        db().update("UPDATE " + RESV + " SET late_checkout_fee_yuan=? WHERE id=?", fee, resvId);
        return getReservation(resvId);
    }

    /** 管理端登记客房定金/尾款/早餐券/加床/查房清单等 */
    public static Map<String, Object> patchHotel(long resvId, Map<String, Object> body) {
        requireEnabled();
        Map<String, Object> m = getReservation(resvId);
        if (m == null) throw new IllegalArgumentException("预约不存在");
        Map<String, Object> b = body == null ? Map.of() : body;
        if (b.containsKey("idNo") && hasResvColumn("id_no")) {
            String idNo = str(b.get("idNo"));
            if (idNo.length() > 32) idNo = idNo.substring(0, 32);
            db().update("UPDATE " + RESV + " SET id_no=? WHERE id=?", idNo, resvId);
        }
        if (b.containsKey("depositYuan") && hasResvColumn("deposit_yuan")) {
            db().update("UPDATE " + RESV + " SET deposit_yuan=? WHERE id=?", toDecimal(b.get("depositYuan")), resvId);
        }
        if (b.containsKey("balanceYuan") && hasResvColumn("balance_yuan")) {
            db().update("UPDATE " + RESV + " SET balance_yuan=? WHERE id=?", toDecimal(b.get("balanceYuan")), resvId);
        }
        if (b.containsKey("breakfastVouchers") && hasResvColumn("breakfast_vouchers")) {
            db().update(
                    "UPDATE " + RESV + " SET breakfast_vouchers=? WHERE id=?",
                    Math.max(0, toInt(b.get("breakfastVouchers"))),
                    resvId);
        }
        if (b.containsKey("extraBed") && hasResvColumn("extra_bed")) {
            db().update(
                    "UPDATE " + RESV + " SET extra_bed=? WHERE id=?",
                    toInt(b.get("extraBed")) > 0 ? 1 : 0,
                    resvId);
        }
        if (b.containsKey("checkoutChecklist") && hasResvColumn("checkout_checklist")) {
            String cl = str(b.get("checkoutChecklist"));
            if (cl.length() > 512) cl = cl.substring(0, 512);
            db().update("UPDATE " + RESV + " SET checkout_checklist=? WHERE id=?", cl, resvId);
        }
        return getReservation(resvId);
    }


    /** 管理端登记里程超支加收 */
    public static Map<String, Object> registerMileageOverFee(long resvId, BigDecimal yuan) {
        requireEnabled();
        Map<String, Object> m = getReservation(resvId);
        if (m == null) throw new IllegalArgumentException("预约不存在");
        if (!hasResvColumn("mileage_over_fee_yuan")) {
            throw new IllegalStateException("当前不支持里程超支加收");
        }
        BigDecimal fee = yuan;
        if (fee == null || fee.compareTo(BigDecimal.ZERO) <= 0) {
            fee = BigDecimal.valueOf(Math.max(carrentMileageOverFeeYuan, 0));
        }
        if (fee.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("请填写加收金额");
        }
        db().update("UPDATE " + RESV + " SET mileage_over_fee_yuan=? WHERE id=?", fee, resvId);
        return getReservation(resvId);
    }

    /** 管理端登记 ETC 通行费 */
    public static Map<String, Object> registerEtcFee(long resvId, BigDecimal yuan) {
        requireEnabled();
        Map<String, Object> m = getReservation(resvId);
        if (m == null) throw new IllegalArgumentException("预约不存在");
        if (!hasResvColumn("etc_fee_yuan")) {
            throw new IllegalStateException("当前不支持 ETC 通行费登记");
        }
        BigDecimal fee = yuan;
        if (fee == null || fee.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("请填写通行费金额");
        }
        db().update("UPDATE " + RESV + " SET etc_fee_yuan=? WHERE id=?", fee, resvId);
        return getReservation(resvId);
    }

    /** 管理端登记租车违章预留押/验车/保险/驾照期/违章附件等 */
    public static Map<String, Object> patchCarrent(long resvId, Map<String, Object> body) {
        requireEnabled();
        Map<String, Object> m = getReservation(resvId);
        if (m == null) throw new IllegalArgumentException("预约不存在");
        Map<String, Object> b = body == null ? Map.of() : body;
        if (b.containsKey("violationHoldYuan") && hasResvColumn("violation_hold_yuan")) {
            db().update(
                    "UPDATE " + RESV + " SET violation_hold_yuan=? WHERE id=?",
                    toDecimal(b.get("violationHoldYuan")),
                    resvId);
        }
        if (b.containsKey("violationHoldNote") && hasResvColumn("violation_hold_note")) {
            String note = str(b.get("violationHoldNote"));
            if (note.length() > 255) note = note.substring(0, 255);
            db().update("UPDATE " + RESV + " SET violation_hold_note=? WHERE id=?", note, resvId);
        }
        if (b.containsKey("inspectAck") && hasResvColumn("inspect_ack")) {
            db().update(
                    "UPDATE " + RESV + " SET inspect_ack=? WHERE id=?",
                    toInt(b.get("inspectAck")) > 0 ? 1 : 0,
                    resvId);
        }
        if (b.containsKey("insurancePkg") && hasResvColumn("insurance_pkg")) {
            String pkg = str(b.get("insurancePkg"));
            if (pkg.length() > 32) pkg = pkg.substring(0, 32);
            db().update("UPDATE " + RESV + " SET insurance_pkg=? WHERE id=?", pkg, resvId);
        }
        if (b.containsKey("licenseExpireOn") && hasResvColumn("license_expire_on")) {
            String exp = str(b.get("licenseExpireOn"));
            if (exp.length() >= 10) exp = exp.substring(0, 10);
            db().update(
                    "UPDATE " + RESV + " SET license_expire_on=? WHERE id=?",
                    exp.isBlank() ? null : exp,
                    resvId);
        }
        if (b.containsKey("violationAttach") && hasResvColumn("violation_attach")) {
            String att = str(b.get("violationAttach"));
            if (att.length() > 512) att = att.substring(0, 512);
            db().update("UPDATE " + RESV + " SET violation_attach=? WHERE id=?", att, resvId);
        }
        return getReservation(resvId);
    }

    /** 管理端登记仪器耗材领用说明 */
    public static Map<String, Object> patchInstrument(long resvId, Map<String, Object> body) {
        requireEnabled();
        Map<String, Object> m = getReservation(resvId);
        if (m == null) throw new IllegalArgumentException("预约不存在");
        Map<String, Object> b = body == null ? Map.of() : body;
        if (b.containsKey("consumableNote") && hasResvColumn("consumable_note")) {
            String note = str(b.get("consumableNote"));
            if (note.length() > 512) note = note.substring(0, 512);
            db().update("UPDATE " + RESV + " SET consumable_note=? WHERE id=?", note, resvId);
        }
        if (b.containsKey("trainingAck") && hasResvColumn("training_ack")) {
            db().update(
                    "UPDATE " + RESV + " SET training_ack=? WHERE id=?",
                    toInt(b.get("trainingAck")) > 0 ? 1 : 0,
                    resvId);
        }
        return getReservation(resvId);
    }

    private static String maskIdNo(String idNo) {
        if (idNo == null || idNo.isBlank()) return "";
        String s = idNo.trim();
        if (s.length() <= 4) return "****";
        if (s.length() <= 8) return s.substring(0, 1) + "****" + s.substring(s.length() - 1);
        return s.substring(0, 2) + "****" + s.substring(s.length() - 2);
    }

    private static BigDecimal toDecimal(Object o) {
        if (o == null) return BigDecimal.ZERO;
        if (o instanceof BigDecimal bd) return bd;
        if (o instanceof Number n) return BigDecimal.valueOf(n.doubleValue());
        try {
            String s = String.valueOf(o).trim();
            if (s.isBlank()) return BigDecimal.ZERO;
            return new BigDecimal(s);
        } catch (Exception e) {
            return BigDecimal.ZERO;
        }
    }

    private static void assertCheckinCode(Map<String, Object> resv, String code, boolean asAdmin) {
        if (asAdmin || resv == null || resv.get("itemId") == null) return;
        Map<String, Object> item;
        try {
            item = ArchiveStore.getItemRaw(((Number) resv.get("itemId")).longValue());
        } catch (Exception e) {
            return;
        }
        if (item == null) return;
        String expect = str(item.get("checkinCode"));
        if (expect.isBlank()) expect = str(item.get("checkin_code"));
        if (expect.isBlank()) return;
        String got = code == null ? "" : code.trim();
        if (!expect.equals(got)) {
            throw new IllegalStateException("报到口令不正确");
        }
    }

    private static void assertHospitalIdLimit(Map<String, Object> slot, String patient) {
        if (hospitalIdLimitPerDay <= 0 || patient == null || patient.isBlank() || slot == null) return;
        Object itemIdObj = slot.get("itemId");
        if (itemIdObj == null) return;
        String day = "";
        Object sa = slot.get("startAt");
        if (sa != null) {
            day = String.valueOf(sa).trim();
            if (day.length() >= 10) day = day.substring(0, 10);
        }
        if (day.isBlank()) return;
        long itemId = Long.parseLong(String.valueOf(itemIdObj));
        int n = mapper().countPatientDay(RESV, SLOT, patient, itemId, day);
        if (n >= hospitalIdLimitPerDay) {
            throw new IllegalStateException(
                    "同一就诊人当天在本科室已约满 " + hospitalIdLimitPerDay + " 次");
        }
    }

    private static void tryPromoteWaitlist(long slotId) {
        if (!hospitalWaitlistOn || slotId <= 0) return;
        try {
            Map<String, Object> slot = getSlot(slotId);
            if (slot == null) return;
            int remain = ((Number) slot.getOrDefault("remain", 0)).intValue();
            if (remain <= 0) return;
            List<Map<String, Object>> waiting = mapper().selectOldestWaitlist(RESV, slotId);
            if (waiting == null || waiting.isEmpty()) return;
            Map<String, Object> w = waiting.get(0);
            long rid = ((Number) w.get("id")).longValue();
            String u = String.valueOf(w.get("username"));
            String next = requireConfirm ? "pending" : "confirmed";
            mapper().updateResvStatus(RESV, rid, next);
            mapper().updateRemain(SLOT, slotId, remain - 1);
            String body = "pending".equals(next)
                    ? "您的候补号源已占位，请等待窗口确认"
                    : "您的候补号源已转正，请按时就诊";
            MessageStore.add(u, "候补已转正", body, "reservation", String.valueOf(rid));
        } catch (Exception ignored) {
        }
    }

    /** 停诊：按资源维护期取消预约并发站内信 */
    public static int notifyStopAndCancel(long itemId) {
        requireEnabled();
        if (itemId <= 0) return 0;
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) return 0;
        String from = str(item.get("maintainFrom"));
        if (from.isBlank()) from = str(item.get("maintain_from"));
        String to = str(item.get("maintainTo"));
        if (to.isBlank()) to = str(item.get("maintain_to"));
        if (from.isBlank() && to.isBlank()) return 0;
        String fromDay = from.isBlank() ? "1970-01-01" : from.substring(0, Math.min(10, from.length()));
        String toDay = to.isBlank() ? "2099-12-31" : to.substring(0, Math.min(10, to.length()));
        List<Map<String, Object>> rows = mapper().selectResvInMaintain(RESV, SLOT, itemId, fromDay, toDay);
        int n = 0;
        for (Map<String, Object> r : rows) {
            long rid = ((Number) r.get("id")).longValue();
            Map<String, Object> full = getReservation(rid);
            if (full == null) continue;
            String st = String.valueOf(full.getOrDefault("status", ""));
            if ("cancelled".equals(st) || "completed".equals(st) || "no_show".equals(st)) continue;
            String u = String.valueOf(full.get("username"));
            long sid = ((Number) full.get("slotId")).longValue();
            mapper().updateResvStatus(RESV, rid, "cancelled");
            if (!"waitlisted".equals(st)) {
                Map<String, Object> slot = getSlot(sid);
                if (slot != null) {
                    int remain = ((Number) slot.getOrDefault("remain", 0)).intValue();
                    int capacity = ((Number) slot.getOrDefault("capacity", 0)).intValue();
                    if (remain < capacity) mapper().updateRemain(SLOT, sid, remain + 1);
                }
            }
            MessageStore.add(
                    u,
                    "科室停诊通知",
                    "您预约的科室已安排停诊，原预约已取消，请改约其它时段。",
                    "reservation",
                    String.valueOf(rid));
            n++;
        }
        return n;
    }

    private static void requireEnabled() {
        if (!enabled) throw new IllegalStateException("预约功能暂不可用");
    }
}
