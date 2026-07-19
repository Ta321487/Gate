package com.thesis.capability;

import com.thesis.config.JdbcSupport;
import com.thesis.service.MessageStore;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;

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

    private SlotStore() {}

    public static void bind(String slotTable, String reservationTable) {
        SLOT = slotTable == null ? "" : slotTable.trim();
        RESV = reservationTable == null ? "" : reservationTable.trim();
        enabled = !SLOT.isBlank() && !RESV.isBlank();
    }

    public static void unbind() {
        enabled = false;
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
        if (ArchiveStore.getItemRaw(itemId) == null) throw new IllegalArgumentException("资源不存在");
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
        requireEnabled();
        Map<String, Object> slot = getSlot(slotId);
        if (slot == null) throw new IllegalArgumentException("时段不存在");
        int capacity = ((Number) slot.get("capacity")).intValue();
        int booked = ((Number) slot.get("booked")).intValue();
        if (booked >= capacity) throw new IllegalStateException("该时段已约满");
        Integer dup = db().queryForObject(
                "SELECT COUNT(*) FROM " + RESV
                        + " WHERE username=? AND slot_id=? AND status IN ('pending','confirmed')",
                Integer.class, username, slotId);
        if (dup != null && dup > 0) throw new IllegalStateException("您已预约该时段");
        int updated = db().update(
                "UPDATE " + SLOT + " SET booked=booked+1 WHERE id=? AND booked<capacity", slotId);
        if (updated == 0) throw new IllegalStateException("该时段已约满");
        KeyHolder kh = new GeneratedKeyHolder();
        String note = remark == null ? "" : remark.trim();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO " + RESV + " (slot_id,username,status,remark,created_at) VALUES (?,?,?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, slotId);
            ps.setString(2, username);
            ps.setString(3, "confirmed");
            ps.setString(4, note);
            ps.setTimestamp(5, Timestamp.valueOf(LocalDateTime.now()));
            return ps;
        }, kh);
        long resvId = kh.getKey() == null ? 0L : kh.getKey().longValue();
        // 联动订单（酒店等同时具备 order_lines）
        if (OrderStore.enabled()) {
            long itemId = ((Number) slot.get("itemId")).longValue();
            Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
            String title = item == null ? "预约" : String.valueOf(item.get("title"));
            double price = 0;
            if (item != null) {
                try {
                    price = Double.parseDouble(String.valueOf(item.get("author")).replace("¥", "").trim());
                } catch (Exception ignored) {
                    price = 0;
                }
            }
            String body = title + " · " + slot.get("startAt") + " ~ " + slot.get("endAt");
            OrderStore.placeSimple(username, itemId, body, price, 1, "reservation:" + resvId);
        }
        try {
            MessageStore.send(
                    username,
                    "预约成功",
                    "已预约「" + slot.get("itemTitle") + "」" + slot.get("startAt") + " ~ " + slot.get("endAt"),
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
        db().update("UPDATE " + RESV + " SET status='cancelled' WHERE id=?", resvId);
        db().update(
                "UPDATE " + SLOT + " SET booked=GREATEST(booked-1,0) WHERE id=?",
                ((Number) m.get("slotId")).longValue());
        return getReservation(resvId);
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
        m.put("pendingReservations", pending == null ? 0 : pending);
        m.put("confirmedReservations", confirmed == null ? 0 : confirmed);
        return m;
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
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        return m;
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
        return m;
    }

    private static void requireEnabled() {
        if (!enabled) throw new IllegalStateException("预约能力未启用");
    }
}
