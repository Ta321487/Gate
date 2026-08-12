package com.thesis.capability;

import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.thesis.config.MybatisSupport;
import com.thesis.mapper.SchemaMapper;
import com.thesis.mapper.SlotMapper;
import com.thesis.service.MessageStore;
import com.thesis.service.UserStore;

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
    }

    public static void configureRemark(boolean required) {
        requireRemark = required;
    }

    public static void configureConfirm(boolean required) {
        requireConfirm = required;
    }

    public static boolean requireConfirm() {
        return requireConfirm;
    }

    public static void unbind() {
        enabled = false;
        requireRemark = false;
        requireConfirm = false;
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
        if (ArchiveStore.getItemRaw(itemId) == null) throw new IllegalArgumentException("资源不存在");
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
        Map<String, Object> slot = getSlot(slotId);
        if (slot == null) throw new IllegalArgumentException("时段不存在");
        if (isPastSlot(slot)) throw new IllegalStateException("该时段已过，不可预约");
        int capacity = ((Number) slot.get("capacity")).intValue();
        int booked = ((Number) slot.get("booked")).intValue();
        if (booked >= capacity) throw new IllegalStateException("该时段已约满");
        if (mapper().countActiveResv(RESV, username, slotId) > 0) {
            throw new IllegalStateException("您已预约该时段");
        }

        String rawNote = remark == null ? "" : remark.trim();
        final String note = rawNote.length() > 255 ? rawNote.substring(0, 255) : rawNote;
        Map<String, Object> ex = extras == null ? Map.of() : extras;
        String plate = str(ex.get("plateNo"));
        String patient = str(ex.get("patientName"));
        String visit = str(ex.get("visitType"));
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
        final String noteFinal = noteFilled.length() > 255 ? noteFilled.substring(0, 255) : noteFilled;
        final String initialStatus = requireConfirm ? "pending" : "confirmed";

        if (mapper().bumpBooked(SLOT, slotId) == 0) throw new IllegalStateException("该时段已约满");
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
        if (hasResvColumn("queue_no")) {
            extraCols.put("queue_no", queue > 0 ? queue : (int) (slotId % 1000) + 1);
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
        } catch (RuntimeException e) {
            mapper().releaseBooked(SLOT, slotId);
            throw e;
        }
        if (OrderStore.enabled()) {
            long itemId = ((Number) slot.get("itemId")).longValue();
            Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
            String title = item == null ? "预约" : String.valueOf(item.get("title"));
            double price = 0;
            if (item != null) {
                price = OrderStore.unitPriceOf(item);
            }
            String body = title + " · " + slot.get("startAt") + " ~ " + slot.get("endAt");
            try {
                OrderStore.placeSimple(username, itemId, body, price, 1, "reservation:" + resvId, resvId);
            } catch (RuntimeException e) {
                try {
                    mapper().deleteReservation(RESV, resvId);
                } catch (Exception ignored) {
                }
                mapper().releaseBooked(SLOT, slotId);
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

    /** 管理端：pending → confirmed */
    public static Map<String, Object> confirm(long resvId) {
        requireEnabled();
        Map<String, Object> m = getReservation(resvId);
        if (m == null) throw new IllegalArgumentException("预约不存在");
        if (!"pending".equals(String.valueOf(m.get("status")))) {
            throw new IllegalStateException("当前状态不可确认");
        }
        mapper().updateResvStatus(RESV, resvId, "confirmed");
        try {
            String user = String.valueOf(m.get("username"));
            MessageStore.send(
                    user,
                    "预约已确认",
                    "「" + m.get("itemTitle") + "」" + m.get("startAt") + " ~ " + m.get("endAt") + " 已确认。",
                    "reservation",
                    resvId);
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
        if (hasResvColumn("entry_at")) {
            mapper().completeWithEntry(RESV, resvId);
        } else {
            mapper().updateResvStatus(RESV, resvId, "completed");
        }
        try {
            OrderStore.completeByReservation(resvId);
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
        if (!"pending".equals(st) && !"confirmed".equals(st)) {
            throw new IllegalStateException("当前状态不可取消");
        }
        mapper().updateResvStatus(RESV, resvId, "cancelled");
        mapper().releaseBooked(SLOT, ((Number) m.get("slotId")).longValue());
        try {
            OrderStore.cancelByReservation(resvId);
        } catch (Exception ignored) {
        }
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
                return false;
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
        m.put("partySize", toInt(first(raw, "partySize", "party_size")));
        m.put("guestName", str(first(raw, "guestName", "guest_name")));
        m.put("guestCount", toInt(first(raw, "guestCount", "guest_count")));
        m.put("preferredStylist", str(first(raw, "preferredStylist", "preferred_stylist")));
        m.put("queueNo", toInt(first(raw, "queueNo", "queue_no")));
        m.put("entryAt", fmt(first(raw, "entryAt", "entry_at")));
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

    private static void requireEnabled() {
        if (!enabled) throw new IllegalStateException("预约功能暂不可用");
    }
}
