package com.thesis.capability;

import com.thesis.config.JdbcSupport;
import com.thesis.service.MessageStore;
import com.thesis.service.UserStore;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;

import java.math.BigDecimal;
import java.sql.PreparedStatement;
import java.sql.Statement;
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
    /** 开始前 N 小时可免费取消；0=不限制 */
    private static int cancelFreeHours = 0;
    /** 单条预约改约次数上限；0=不限制 */
    private static int rescheduleMaxTimes = 0;
    /** 开始前 N 分钟发站内提醒；0=关闭 */
    private static int remindAheadMinutes = 0;
    /** 累计爽约次数上限；0=不限制 */
    private static int noShowLimit = 0;
    /** 签到迟到宽限分钟 */
    private static int lateGraceMinutes = 15;
    /** 预约黑名单开关 */
    private static boolean reserveBlacklistOn = false;
    /** HOSPITAL：开诊前可退号分钟；0=沿用 cancelFreeHours */
    private static int hospitalCancelCutoffMinutes = 0;
    /** HOSPITAL：同就诊人同科室同日限号；0=不限 */
    private static int hospitalIdLimitPerDay = 0;
    /** HOSPITAL：满号可候补 */
    private static boolean hospitalWaitlistOn = false;
    /** PARKING：小时费率（元） */
    private static int parkingHourlyYuan = 0;
    /** PARKING：超时加收默认（元） */
    private static int parkingOvertimeYuan = 0;
    /** PARKING：次卡开关 */
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

    /** §1.7 R-01 通识规则 */
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

    /** §1.7 R-02 HOSPITAL */
    public static void configureHospital(
            int cancelCutoffMinutes, int idLimitPerDay, boolean waitlistOn) {
        hospitalCancelCutoffMinutes = Math.max(0, cancelCutoffMinutes);
        hospitalIdLimitPerDay = Math.max(0, idLimitPerDay);
        hospitalWaitlistOn = waitlistOn;
    }

    /** §1.7 R-03 PARKING */
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

    public static boolean requireConfirm() {
        return requireConfirm;
    }

    public static boolean allowRating() {
        return allowRating;
    }

    public static int remindAheadMinutes() {
        return remindAheadMinutes;
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

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    private static String fmt(Timestamp ts) {
        return ts == null ? null : ts.toLocalDateTime().format(FMT);
    }

    public static List<Map<String, Object>> listSlots(Long itemId, String day) {
        return listSlots(itemId, day, false);
    }

    /** @param bookableOnly 用户预约：只列未开始时段 */
    public static List<Map<String, Object>> listSlots(Long itemId, String day, boolean bookableOnly) {
        requireEnabled();
        StringBuilder sql = new StringBuilder("SELECT * FROM " + SLOT + " WHERE 1=1");
        List<Object> args = new ArrayList<>();
        if (itemId != null && itemId > 0) {
            sql.append(" AND item_id=?");
            args.add(itemId);
        }
        if (day != null && !day.isBlank()) {
            sql.append(" AND DATE(start_at)=?");
            args.add(day.trim());
        }
        if (bookableOnly) {
            sql.append(" AND start_at > NOW()");
        }
        sql.append(" ORDER BY start_at, id");
        return db().query(sql.toString(), (rs, i) -> enrichSlot(mapSlot(rs)), args.toArray());
    }

    public static Map<String, Object> getSlot(long id) {
        requireEnabled();
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM " + SLOT + " WHERE id=?", (rs, i) -> enrichSlot(mapSlot(rs)), id);
        return list.isEmpty() ? null : list.get(0);
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
            Integer exists = db().queryForObject(
                    "SELECT COUNT(*) FROM " + SLOT + " WHERE item_id=? AND start_at=? AND end_at=?",
                    Integer.class, itemId, Timestamp.valueOf(cursor), Timestamp.valueOf(slotEnd));
            if (exists == null || exists == 0) {
                db().update(
                        "INSERT INTO " + SLOT + " (item_id,start_at,end_at,capacity,booked) VALUES (?,?,?,?,0)",
                        itemId, Timestamp.valueOf(cursor), Timestamp.valueOf(slotEnd), capacity);
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
                if (hospitalWaitlistOn) {
                    asWaitlist = true;
                } else {
                    throw new IllegalStateException("该时段已约满");
                }
            }
        }
        Integer dup = db().queryForObject(
                "SELECT COUNT(*) FROM " + RESV
                        + " WHERE username=? AND slot_id=? AND status IN ('pending','confirmed','waitlisted')",
                Integer.class, username, slotId);
        if (dup != null && dup > 0) throw new IllegalStateException("您已预约该时段");

        String rawNote = remark == null ? "" : remark.trim();
        final String note = rawNote.length() > 255 ? rawNote.substring(0, 255) : rawNote;
        Map<String, Object> ex = extras == null ? Map.of() : extras;
        String plate = str(ex.get("plateNo"));
        String patient = str(ex.get("patientName"));
        String visit = str(ex.get("visitType"));
        assertParkingOverlap(plate, slot);
        assertMeetingMinDuration(slot);
        assertSalonServiceDuration(slot);
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
        // 先校验再占坑，避免校验失败泄漏 booked
        ShootStore.assertBook(ex);
        LessonStore.assertRemain(username);
        String leaveDay = "";
        if (slot.get("startAt") != null) {
            String sa = String.valueOf(slot.get("startAt"));
            if (sa.length() >= 10) leaveDay = sa.substring(0, 10);
        }
        StaffRosterStore.assertNotOnLeave(stylist, leaveDay);
        if (requireRemark && noteFilled.isBlank()) {
            throw new IllegalStateException("请填写备注后再预约");
        }
        requireResvColIfPresent("plate_no", "车牌号", !plate.isBlank());
        requireResvColIfPresent("patient_name", "就诊人", !patient.isBlank());
        requireResvColIfPresent("visit_type", "就诊类型", !visit.isBlank());
        requireResvColIfPresent("symptom_note", "症状说明", !symptom.isBlank());
        requireResvColIfPresent("subject", "主题", !subject.isBlank());
        requireResvColIfPresent("party_size", "人数", party > 0);
        requireResvColIfPresent("guest_name", "入住姓名", !guest.isBlank());
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

        if (!rangeHeld && !"waitlisted".equals(statusToUse)) {
            int updated = db().update(
                    "UPDATE " + SLOT + " SET booked=booked+1 WHERE id=? AND booked<capacity", slotId);
            if (updated == 0) {
                if (hospitalWaitlistOn) {
                    statusToUse = "waitlisted";
                } else {
                    throw new IllegalStateException("该时段已约满");
                }
            }
        }
        final String initialStatus = statusToUse;
        KeyHolder kh = new GeneratedKeyHolder();
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
            String note = str(ex.get("violationHoldNote"));
            if (note.length() > 255) note = note.substring(0, 255);
            extraCols.put("violation_hold_note", note);
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
        // boarding 可能改写 slotId；lambda 只能捕获 effectively-final
        final long slotIdFinal = slotId;
        try {
            db().update(con -> {
                StringBuilder cols = new StringBuilder(
                        "slot_id,username,status,remark");
                StringBuilder marks = new StringBuilder("?,?,?,?");
                List<Object> args = new ArrayList<>();
                args.add(slotIdFinal);
                args.add(username);
                args.add(initialStatus);
                args.add(noteFinal);
                for (Map.Entry<String, Object> e : extraCols.entrySet()) {
                    cols.append(',').append(e.getKey());
                    marks.append(",?");
                    args.add(e.getValue());
                }
                cols.append(",created_at");
                marks.append(",?");
                args.add(Timestamp.valueOf(LocalDateTime.now()));
                PreparedStatement ps = con.prepareStatement(
                        "INSERT INTO " + RESV + " (" + cols + ") VALUES (" + marks + ")",
                        Statement.RETURN_GENERATED_KEYS);
                for (int i = 0; i < args.size(); i++) {
                    Object v = args.get(i);
                    if (v instanceof Timestamp ts) ps.setTimestamp(i + 1, ts);
                    else if (v instanceof Integer n) ps.setInt(i + 1, n);
                    else if (v instanceof Long n) ps.setLong(i + 1, n);
                    else ps.setString(i + 1, v == null ? "" : String.valueOf(v));
                }
                return ps;
            }, kh);
        } catch (RuntimeException e) {
            if (rangeHeld) BoardingStore.releaseRange(stayItemId, stayFromHeld, stayToHeld);
            else db().update(
                    "UPDATE " + SLOT + " SET booked=GREATEST(booked-1,0) WHERE id=?", slotId);
            throw e;
        }
        long resvId = kh.getKey() == null ? 0L : kh.getKey().longValue();
        ShootStore.attach(resvId, ex);
        if (parkingPassOn && !plate.isBlank() && hasResvColumn("parking_pass_used")) {
            if (com.thesis.service.ParkingPassStore.spendOne(username)) {
                db().update("UPDATE " + RESV + " SET parking_pass_used=1 WHERE id=?", resvId);
            }
        }
        try {
            LessonStore.spend(username, resvId);
        } catch (RuntimeException lessonEx) {
            try {
                LessonStore.refund(resvId);
                db().update("DELETE FROM " + RESV + " WHERE id=?", resvId);
            } catch (Exception ignored) {
            }
            if (rangeHeld) BoardingStore.releaseRange(stayItemId, stayFromHeld, stayToHeld);
            else db().update(
                    "UPDATE " + SLOT + " SET booked=GREATEST(booked-1,0) WHERE id=?", slotId);
            throw lessonEx;
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
                    db().update("DELETE FROM " + RESV + " WHERE id=?", resvId);
                } catch (Exception ignored) {
                }
                if (rangeHeld) BoardingStore.releaseRange(stayItemId, stayFromHeld, stayToHeld);
                else db().update(
                        "UPDATE " + SLOT + " SET booked=GREATEST(booked-1,0) WHERE id=?", slotId);
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
            } else if ("waitlisted".equals(initialStatus)) {
                MessageStore.send(
                        username,
                        "已加入候补",
                        "「" + slot.get("itemTitle") + "」" + slot.get("startAt") + " ~ " + slot.get("endAt")
                                + " 号源已满，已为您加入候补。",
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
        db().update("UPDATE " + RESV + " SET status='confirmed' WHERE id=?", resvId);
        if (hasResvColumn("checkin_token")) {
            Map<String, Object> cur = getReservation(resvId);
            String tok = cur == null ? "" : str(cur.get("checkinToken"));
            if (tok.isBlank()) {
                db().update("UPDATE " + RESV + " SET checkin_token=? WHERE id=?", newCheckinToken(), resvId);
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
            db().update(
                    "UPDATE " + RESV + " SET status='completed', entry_at=NOW() WHERE id=?",
                    resvId);
        } else {
            db().update("UPDATE " + RESV + " SET status='completed' WHERE id=?", resvId);
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
        db().update("UPDATE " + RESV + " SET status='cancelled' WHERE id=?", resvId);
        if (!isPastSlot(m)) LessonStore.refund(resvId);
        if (!BoardingStore.releaseStay(RESV, SLOT, resvId)) {
            db().update(
                    "UPDATE " + SLOT + " SET booked=GREATEST(booked-1,0) WHERE id=?",
                    ((Number) m.get("slotId")).longValue());
        }
        OrderStore.cancelByReservation(resvId);
        if (parkingPassOn && hasResvColumn("parking_pass_used")) {
            Object used = m.get("parkingPassUsed");
            int u = used instanceof Number ? ((Number) used).intValue() : toInt(used);
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
        db().update(
                "UPDATE " + RESV + " SET rating=?, rating_remark=?, rated_at=NOW() WHERE id=?",
                rating,
                remark,
                resvId);
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
        // 先取消原单（放号源、关联动订单），再占新坑
        cancel(resvId, username, true);
        try {
            return reserve(username, newSlotId, remark, extras);
        } catch (RuntimeException e) {
            // 尽力提示：原约已取消
            throw new IllegalStateException("原预约已取消，但新时段预约失败：" + e.getMessage());
        }
    }

    /** 用户/管理签到；超过开始时间+宽限记迟到；科室有报到口令时须核对 */
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
                LocalDateTime deadline = start.plusMinutes(Math.max(0, lateGraceMinutes));
                late = LocalDateTime.now().isAfter(deadline);
            }
        } catch (Exception ignored) {
        }
        if (hasResvColumn("checked_in_at") && hasResvColumn("late_flag")) {
            db().update(
                    "UPDATE " + RESV + " SET checked_in_at=NOW(), late_flag=? WHERE id=?",
                    late ? 1 : 0,
                    resvId);
        } else if (hasResvColumn("checked_in_at")) {
            db().update("UPDATE " + RESV + " SET checked_in_at=NOW() WHERE id=?", resvId);
        } else {
            throw new IllegalStateException("当前不支持签到");
        }
        return getReservation(resvId);
    }

    /** 管理端标记爽约 */
    public static Map<String, Object> markNoShow(long resvId) {
        requireEnabled();
        Map<String, Object> m = getReservation(resvId);
        if (m == null) throw new IllegalArgumentException("预约不存在");
        String st = String.valueOf(m.get("status"));
        if (!"confirmed".equals(st) && !"pending".equals(st)) {
            throw new IllegalStateException("当前状态不可记爽约");
        }
        if (hasResvColumn("no_show")) {
            db().update(
                    "UPDATE " + RESV + " SET status='cancelled', no_show=1 WHERE id=?",
                    resvId);
        } else {
            db().update("UPDATE " + RESV + " SET status='cancelled' WHERE id=?", resvId);
        }
        if (!BoardingStore.releaseStay(RESV, SLOT, resvId)) {
            db().update(
                    "UPDATE " + SLOT + " SET booked=GREATEST(booked-1,0) WHERE id=?",
                    ((Number) m.get("slotId")).longValue());
        }
        OrderStore.cancelByReservation(resvId);
        return getReservation(resvId);
    }

    /** 开始前提醒扫：写 remind_sent + 站内信 */
    public static int remindDueSweep() {
        if (!enabled || remindAheadMinutes <= 0 || !hasResvColumn("remind_sent")) return 0;
        List<Map<String, Object>> rows;
        try {
            rows = db().query(
                    "SELECT r.id, r.username, s.start_at, s.end_at, s.item_id FROM "
                            + RESV + " r JOIN " + SLOT + " s ON r.slot_id=s.id "
                            + "WHERE r.status IN ('pending','confirmed') AND r.remind_sent=0 "
                            + "AND s.start_at > NOW() "
                            + "AND s.start_at <= DATE_ADD(NOW(), INTERVAL ? MINUTE)",
                    (rs, i) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("id", rs.getLong("id"));
                        row.put("username", rs.getString("username"));
                        row.put("startAt", fmt(rs.getTimestamp("start_at")));
                        row.put("endAt", fmt(rs.getTimestamp("end_at")));
                        row.put("itemId", rs.getLong("item_id"));
                        return row;
                    },
                    remindAheadMinutes);
        } catch (Exception e) {
            return 0;
        }
        int n = 0;
        for (Map<String, Object> row : rows) {
            long id = ((Number) row.get("id")).longValue();
            try {
                String title = "";
                Object iid = row.get("itemId");
                if (iid != null) {
                    Map<String, Object> item = ArchiveStore.getItemRaw(((Number) iid).longValue());
                    if (item != null) title = String.valueOf(item.getOrDefault("title", ""));
                }
                MessageStore.send(
                        String.valueOf(row.get("username")),
                        "预约即将开始",
                        "「" + title + "」" + row.get("startAt") + " ~ " + row.get("endAt") + " 即将开始，请按时到场。",
                        "reservation",
                        id);
                db().update("UPDATE " + RESV + " SET remind_sent=1 WHERE id=?", id);
                n++;
            } catch (Exception ignored) {
            }
        }
        return n;
    }

    /** 资源按日容量着色：ok / warn / full */
    public static List<Map<String, Object>> dayFill(long itemId, String month) {
        requireEnabled();
        String ym = month == null ? "" : month.trim();
        if (ym.length() < 7) {
            ym = LocalDate.now().toString().substring(0, 7);
        } else {
            ym = ym.substring(0, 7);
        }
        String like = ym + "%";
        try {
            return db().query(
                    "SELECT DATE_FORMAT(start_at,'%Y-%m-%d') AS day, "
                            + "SUM(capacity) AS capacity, SUM(booked) AS booked FROM "
                            + SLOT + " WHERE item_id=? AND start_at LIKE ? "
                            + "GROUP BY DATE_FORMAT(start_at,'%Y-%m-%d') ORDER BY day",
                    (rs, i) -> {
                        int cap = rs.getInt("capacity");
                        int booked = rs.getInt("booked");
                        int remain = Math.max(0, cap - booked);
                        String tone = "ok";
                        if (remain <= 0) tone = "full";
                        else if (cap > 0 && remain * 1.0 / cap <= 0.25) tone = "warn";
                        else if (remain <= 2) tone = "warn";
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("day", rs.getString("day"));
                        row.put("capacity", cap);
                        row.put("booked", booked);
                        row.put("remain", remain);
                        row.put("tone", tone);
                        return row;
                    },
                    itemId,
                    like);
        } catch (Exception e) {
            return List.of();
        }
    }

    public static Map<String, Object> getReservation(long id) {
        requireEnabled();
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM " + RESV + " WHERE id=?", (rs, i) -> mapResv(rs), id);
        if (list.isEmpty()) return null;
        return enrichResv(list.get(0));
    }

    public static Map<String, Object> pageReservations(String username, String status, int page, int size) {
        requireEnabled();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        StringBuilder where = new StringBuilder(" WHERE 1=1");
        List<Object> args = new ArrayList<>();
        if (username != null && !username.isBlank()) {
            where.append(" AND username=?");
            args.add(username);
        }
        if (status != null && !status.isBlank()) {
            where.append(" AND status=?");
            args.add(status);
        }
        Integer total = db().queryForObject("SELECT COUNT(*) FROM " + RESV + where, Integer.class, args.toArray());
        args.add(size);
        args.add((page - 1) * size);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM " + RESV + where + " ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> enrichResv(mapResv(rs)),
                args.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    public static Map<String, Object> dashboard() {
        if (!enabled) return Map.of();
        Map<String, Object> m = new LinkedHashMap<>();
        Long pending = db().queryForObject(
                "SELECT COUNT(*) FROM " + RESV + " WHERE status='pending'", Long.class);
        Long confirmed = db().queryForObject(
                "SELECT COUNT(*) FROM " + RESV + " WHERE status='confirmed'", Long.class);
        Long completed = db().queryForObject(
                "SELECT COUNT(*) FROM " + RESV + " WHERE status='completed'", Long.class);
        m.put("pendingReservations", pending == null ? 0 : pending);
        m.put("confirmedReservations", confirmed == null ? 0 : confirmed);
        m.put("completedReservations", completed == null ? 0 : completed);
        return m;
    }

    public static Map<String, Object> chartStats() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("statusSeries", List.of());
        out.put("trendSeries", List.of());
        if (!enabled) return out;
        try {
            List<Map<String, Object>> status = db().query(
                    "SELECT status AS name, COUNT(*) AS value FROM " + RESV + " GROUP BY status",
                    (rs, i) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("name", rs.getString("name"));
                        row.put("value", rs.getLong("value"));
                        return row;
                    });
            out.put("statusSeries", status);
            List<Map<String, Object>> trend = db().query(
                    "SELECT DATE_FORMAT(created_at,'%Y-%m-%d') AS day, COUNT(*) AS value FROM " + RESV
                            + " WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)"
                            + " GROUP BY DATE_FORMAT(created_at,'%Y-%m-%d') ORDER BY day",
                    (rs, i) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("day", rs.getString("day"));
                        row.put("value", rs.getLong("value"));
                        return row;
                    });
            out.put("trendSeries", trend);
        } catch (Exception ignored) {
        }
        return out;
    }

    private static Map<String, Object> mapSlot(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("itemId", rs.getLong("item_id"));
        m.put("startAt", fmt(rs.getTimestamp("start_at")));
        m.put("endAt", fmt(rs.getTimestamp("end_at")));
        m.put("capacity", rs.getInt("capacity"));
        m.put("booked", rs.getInt("booked"));
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

    private static Map<String, Object> mapResv(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("slotId", rs.getLong("slot_id"));
        m.put("username", rs.getString("username"));
        m.put("status", rs.getString("status"));
        m.put("remark", rs.getString("remark"));
        m.put("plateNo", safeStr(rs, "plate_no"));
        m.put("patientName", safeStr(rs, "patient_name"));
        m.put("visitType", safeStr(rs, "visit_type"));
        m.put("symptomNote", safeStr(rs, "symptom_note"));
        m.put("subject", safeStr(rs, "subject"));
        m.put("partySize", safeInt(rs, "party_size"));
        m.put("recordingUrl", safeStr(rs, "recording_url"));
        m.put("videoUrl", safeStr(rs, "video_url"));
        m.put("doorCode", safeStr(rs, "door_code"));
        m.put("serviceTea", safeInt(rs, "service_tea"));
        m.put("serviceDevice", safeInt(rs, "service_device"));
        m.put("equipBorrow", safeInt(rs, "equip_borrow"));
        m.put("minutesAttach", safeStr(rs, "minutes_attach"));
        m.put("meetingStage", safeStr(rs, "meeting_stage"));
        m.put("checkinToken", safeStr(rs, "checkin_token"));
        m.put("guestName", safeStr(rs, "guest_name"));
        m.put("guestCount", safeInt(rs, "guest_count"));
        m.put("preferredStylist", safeStr(rs, "preferred_stylist"));
        m.put("queueNo", safeInt(rs, "queue_no"));
        m.put("stayFrom", safeStr(rs, "stay_from"));
        m.put("stayTo", safeStr(rs, "stay_to"));
        String idNo = safeStr(rs, "id_no");
        m.put("idNo", idNo);
        m.put("idNoMasked", maskIdNo(idNo));
        try {
            java.math.BigDecimal dep = rs.getBigDecimal("deposit_yuan");
            m.put("depositYuan", dep == null ? 0 : dep);
        } catch (Exception ignored) {
            m.put("depositYuan", 0);
        }
        try {
            java.math.BigDecimal bal = rs.getBigDecimal("balance_yuan");
            m.put("balanceYuan", bal == null ? 0 : bal);
        } catch (Exception ignored) {
            m.put("balanceYuan", 0);
        }
        m.put("breakfastVouchers", safeInt(rs, "breakfast_vouchers"));
        m.put("noticeAck", safeInt(rs, "notice_ack"));
        m.put("extraBed", safeInt(rs, "extra_bed"));
        try {
            java.math.BigDecimal late = rs.getBigDecimal("late_checkout_fee_yuan");
            m.put("lateCheckoutFeeYuan", late == null ? 0 : late);
        } catch (Exception ignored) {
            m.put("lateCheckoutFeeYuan", 0);
        }
        m.put("checkoutChecklist", safeStr(rs, "checkout_checklist"));
        try {
            java.math.BigDecimal vh = rs.getBigDecimal("violation_hold_yuan");
            m.put("violationHoldYuan", vh == null ? 0 : vh);
        } catch (Exception ignored) {
            m.put("violationHoldYuan", 0);
        }
        m.put("violationHoldNote", safeStr(rs, "violation_hold_note"));
        m.put("inspectAck", safeInt(rs, "inspect_ack"));
        m.put("trainingAck", safeInt(rs, "training_ack"));
        m.put("consumableNote", safeStr(rs, "consumable_note"));
        try {
            java.math.BigDecimal mo = rs.getBigDecimal("mileage_over_fee_yuan");
            m.put("mileageOverFeeYuan", mo == null ? 0 : mo);
        } catch (Exception ignored) {
            m.put("mileageOverFeeYuan", 0);
        }
        m.put("insurancePkg", safeStr(rs, "insurance_pkg"));
        m.put("licenseExpireOn", safeStr(rs, "license_expire_on"));
        m.put("violationAttach", safeStr(rs, "violation_attach"));
        try {
            java.math.BigDecimal etc = rs.getBigDecimal("etc_fee_yuan");
            m.put("etcFeeYuan", etc == null ? 0 : etc);
        } catch (Exception ignored) {
            m.put("etcFeeYuan", 0);
        }
        try {
            java.math.BigDecimal fee = rs.getBigDecimal("reschedule_fee_yuan");
            m.put("rescheduleFeeYuan", fee == null ? 0 : fee);
        } catch (Exception ignored) {
            m.put("rescheduleFeeYuan", 0);
        }
        m.put("rescheduleCount", safeInt(rs, "reschedule_count"));
        m.put("remindSent", safeInt(rs, "remind_sent"));
        m.put("noShow", safeInt(rs, "no_show"));
        m.put("lateFlag", safeInt(rs, "late_flag"));
        try {
            Timestamp cia = rs.getTimestamp("checked_in_at");
            m.put("checkedInAt", fmt(cia));
        } catch (Exception ignored) {
            m.put("checkedInAt", null);
        }
        try {
            Timestamp ea = rs.getTimestamp("entry_at");
            m.put("entryAt", fmt(ea));
        } catch (Exception ignored) {
            m.put("entryAt", null);
        }
        try {
            int r = rs.getInt("rating");
            m.put("rating", rs.wasNull() ? null : r);
        } catch (Exception ignored) {
            m.put("rating", null);
        }
        m.put("ratingRemark", safeStr(rs, "rating_remark"));
        try {
            Timestamp ra = rs.getTimestamp("rated_at");
            m.put("ratedAt", fmt(ra));
        } catch (Exception ignored) {
            m.put("ratedAt", null);
        }
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        return m;
    }

    private static String safeStr(java.sql.ResultSet rs, String col) {
        try {
            String v = rs.getString(col);
            return v == null ? "" : v;
        } catch (Exception e) {
            return "";
        }
    }

    private static int safeInt(java.sql.ResultSet rs, String col) {
        try {
            return rs.getInt(col);
        } catch (Exception e) {
            return 0;
        }
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
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=? AND COLUMN_NAME=?",
                    Integer.class, RESV, col);
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

    private static void requireEnabled() {
        if (!enabled) throw new IllegalStateException("预约功能暂不可用");
    }

    private static void assertReserveAllowed(String username, Map<String, Object> slot) {
        if (reserveBlacklistOn) {
            com.thesis.service.ReserveBlacklistStore.assertNotBlocked(username);
        }
        if (noShowLimit > 0 && hasResvColumn("no_show")) {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM " + RESV + " WHERE username=? AND no_show=1",
                    Integer.class,
                    username);
            if (n != null && n >= noShowLimit) {
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

    private static void assertHospitalIdLimit(Map<String, Object> slot, String patientName) {
        if (hospitalIdLimitPerDay <= 0 || patientName == null || patientName.isBlank()) return;
        if (!hasResvColumn("patient_name") || slot == null || slot.get("itemId") == null) return;
        String day = "";
        Object sa = slot.get("startAt");
        if (sa != null) day = String.valueOf(sa).trim();
        if (day.length() < 10) return;
        day = day.substring(0, 10);
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM " + RESV + " r JOIN " + SLOT + " s ON r.slot_id=s.id "
                            + "WHERE r.patient_name=? AND s.item_id=? AND DATE(s.start_at)=? "
                            + "AND r.status IN ('pending','confirmed','waitlisted')",
                    Integer.class,
                    patientName.trim(),
                    ((Number) slot.get("itemId")).longValue(),
                    day);
            if (n != null && n >= hospitalIdLimitPerDay) {
                throw new IllegalStateException(
                        "同一就诊人当天在本科室已约满 " + hospitalIdLimitPerDay + " 次");
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
            Map<String, Object> item = null;
            if (slot.get("itemId") != null) {
                item = ArchiveStore.getItemRaw(((Number) slot.get("itemId")).longValue());
            }
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
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM " + RESV + " WHERE username=? AND checked_in_at IS NOT NULL",
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
        db().update("UPDATE " + RESV + " SET reschedule_fee_yuan=? WHERE id=?", fee, resvId);
        return getReservation(resvId);
    }

    public static List<Map<String, Object>> listSlotOccupants(long slotId) {
        requireEnabled();
        if (slotId <= 0) return List.of();
        try {
            return db().query(
                    "SELECT id, username, subject, status, party_size FROM " + RESV
                            + " WHERE slot_id=? AND status IN ('pending','confirmed','waitlisted','completed') ORDER BY id",
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
        LocalDate day;
        try {
            day = LocalDate.parse(startDay);
        } catch (Exception e) {
            throw new IllegalArgumentException("日期格式不正确");
        }
        int total = 0;
        for (int w = 0; w < weeks; w++) {
            String d = day.plusWeeks(w).toString();
            total += generateDaySlots(itemId, d, startHour, endHour, slotMinutes, capacity);
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
            db().update("UPDATE " + RESV + " SET door_code=? WHERE id=?", v, resvId);
        }
        if (recordingUrl != null && hasResvColumn("recording_url")) {
            String v = recordingUrl.trim();
            if (v.length() > 255) v = v.substring(0, 255);
            db().update("UPDATE " + RESV + " SET recording_url=? WHERE id=?", v, resvId);
        }
        if (videoUrl != null && hasResvColumn("video_url")) {
            String v = videoUrl.trim();
            if (v.length() > 255) v = v.substring(0, 255);
            db().update("UPDATE " + RESV + " SET video_url=? WHERE id=?", v, resvId);
        }
        if (stage != null && hasResvColumn("meeting_stage")) {
            String v = stage.trim();
            if (!v.isEmpty() && !"in_progress".equals(v) && !"ended".equals(v) && !"".equals(v)) {
                throw new IllegalArgumentException("会议状态不正确");
            }
            db().update("UPDATE " + RESV + " SET meeting_stage=? WHERE id=?", v, resvId);
        }
        if (minutesAttach != null && hasResvColumn("minutes_attach")) {
            String v = minutesAttach.trim();
            if (v.length() > 512) v = v.substring(0, 512);
            db().update("UPDATE " + RESV + " SET minutes_attach=? WHERE id=?", v, resvId);
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
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM " + RESV + " r JOIN " + SLOT + " s ON r.slot_id=s.id "
                            + "WHERE r.plate_no=? AND r.status IN ('pending','confirmed') "
                            + "AND s.start_at < ? AND s.end_at > ?",
                    Integer.class,
                    plate,
                    ea.replace('T', ' ').length() >= 19 ? ea.replace('T', ' ').substring(0, 19) : ea,
                    sa.replace('T', ' ').length() >= 19 ? sa.replace('T', ' ').substring(0, 19) : sa);
            if (n != null && n > 0) {
                throw new IllegalStateException("同一车牌在重叠时段不可重复预约，请改选其它时段");
            }
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception ignored) {
        }
    }

    /** 登记离场并按小时费率估算时长费 */
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
            // 未入场则先记入场
            if (hasResvColumn("entry_at") && !"completed".equals(st)) {
                db().update(
                        "UPDATE " + RESV + " SET status='completed', entry_at=NOW() WHERE id=?", resvId);
                entryDt = LocalDateTime.now();
            } else if (hasResvColumn("entry_at")) {
                db().update("UPDATE " + RESV + " SET entry_at=NOW() WHERE id=? AND entry_at IS NULL", resvId);
                entryDt = LocalDateTime.now();
            }
        }
        LocalDateTime exitDt = LocalDateTime.now();
        BigDecimal fee = BigDecimal.ZERO;
        if (parkingHourlyYuan > 0 && entryDt != null) {
            long minutes = java.time.Duration.between(entryDt, exitDt).toMinutes();
            if (minutes < 0) minutes = 0;
            long hours = (minutes + 59) / 60;
            if (hours < 1) hours = 1;
            fee = BigDecimal.valueOf(parkingHourlyYuan).multiply(BigDecimal.valueOf(hours));
        }
        if (hasResvColumn("duration_fee_yuan")) {
            db().update(
                    "UPDATE " + RESV + " SET exit_at=?, duration_fee_yuan=?, status='completed' WHERE id=?",
                    Timestamp.valueOf(exitDt),
                    fee,
                    resvId);
        } else {
            db().update(
                    "UPDATE " + RESV + " SET exit_at=?, status='completed' WHERE id=?",
                    Timestamp.valueOf(exitDt),
                    resvId);
        }
        return getReservation(resvId);
    }

    /** 管理端登记超时加收 */
    public static Map<String, Object> registerOvertimeFee(long resvId, BigDecimal yuan) {
        requireEnabled();
        Map<String, Object> m = getReservation(resvId);
        if (m == null) throw new IllegalArgumentException("预约不存在");
        if (!hasResvColumn("overtime_fee_yuan")) throw new IllegalStateException("当前不支持超时加收");
        BigDecimal fee = yuan;
        if (fee == null || fee.compareTo(BigDecimal.ZERO) <= 0) {
            int def = Math.max(parkingOvertimeYuan, instrumentOvertimeYuan);
            fee = BigDecimal.valueOf(Math.max(def, 0));
        }
        if (fee.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("请填写加收金额");
        }
        db().update("UPDATE " + RESV + " SET overtime_fee_yuan=? WHERE id=?", fee, resvId);
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

    /** 取消后：同号源最早候补转正（占坑+确认信） */
    private static void tryPromoteWaitlist(long slotId) {
        if (!hospitalWaitlistOn || slotId <= 0) return;
        try {
            List<Map<String, Object>> rows = db().query(
                    "SELECT id, username FROM " + RESV
                            + " WHERE slot_id=? AND status='waitlisted' ORDER BY id ASC LIMIT 1",
                    (rs, i) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("id", rs.getLong("id"));
                        row.put("username", rs.getString("username"));
                        return row;
                    },
                    slotId);
            if (rows.isEmpty()) return;
            long wid = ((Number) rows.get(0).get("id")).longValue();
            int bumped = db().update(
                    "UPDATE " + SLOT + " SET booked=booked+1 WHERE id=? AND booked<capacity", slotId);
            if (bumped == 0) return;
            String next = requireConfirm ? "pending" : "confirmed";
            db().update("UPDATE " + RESV + " SET status=? WHERE id=?", next, wid);
            Map<String, Object> m = getReservation(wid);
            if (m != null) {
                String body = "pending".equals(next)
                        ? "您的候补预约「" + m.get("itemTitle") + "」"
                                + m.get("startAt") + " ~ " + m.get("endAt")
                                + " 已占到号源，请等待确认。"
                        : "您的候补预约「" + m.get("itemTitle") + "」"
                                + m.get("startAt") + " ~ " + m.get("endAt")
                                + " 已转为正式预约，请按时到场。";
                MessageStore.send(
                        String.valueOf(m.get("username")),
                        "候补已转正",
                        body,
                        "reservation",
                        wid);
            }
        } catch (Exception ignored) {
        }
    }

    /**
     * 停诊：将资源维护期内预约取消并发站内信（管理端触发）。
     */
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
        List<Map<String, Object>> rows;
        try {
            rows = db().query(
                    "SELECT r.id FROM " + RESV + " r JOIN " + SLOT + " s ON r.slot_id=s.id "
                            + "WHERE s.item_id=? AND r.status IN ('pending','confirmed','waitlisted') "
                            + "AND DATE(s.start_at) BETWEEN ? AND ?",
                    (rs, i) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("id", rs.getLong("id"));
                        return row;
                    },
                    itemId,
                    fromDay,
                    toDay);
        } catch (Exception e) {
            return 0;
        }
        int n = 0;
        for (Map<String, Object> row : rows) {
            long id = ((Number) row.get("id")).longValue();
            try {
                Map<String, Object> m = getReservation(id);
                if (m == null) continue;
                cancel(id, String.valueOf(m.get("username")), true);
                MessageStore.send(
                        String.valueOf(m.get("username")),
                        "科室停诊通知",
                        "您预约的「" + m.get("itemTitle") + "」"
                                + m.get("startAt") + " ~ " + m.get("endAt")
                                + " 已因停诊取消，请改约其它时段。",
                        "reservation",
                        id);
                n++;
            } catch (Exception ignored) {
            }
        }
        return n;
    }
}
