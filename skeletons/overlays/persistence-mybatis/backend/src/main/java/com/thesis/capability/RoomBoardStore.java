package com.thesis.capability;

import com.thesis.config.MybatisSupport;
import com.thesis.config.MbSql;

import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 酒店房态：房间实例状态与日志。开题挂 room_board 后启用。 */
public final class RoomBoardStore {

    public static final String VACANT = "空房";
    public static final String BOOKED = "已订";
    public static final String STAYING = "入住中";
    public static final String DIRTY = "待打扫";
    public static final String REPAIR = "维修";

    private static boolean enabled;

    private RoomBoardStore() {}

    public static void configure(boolean on) {
        enabled = on;
    }

    public static boolean enabled() {
        return enabled;
    }

    private static void requireOn() {
        if (!enabled) throw new IllegalStateException("未开启房态板");
    }

    private static MbSql db() {
        return MybatisSupport.db();
    }

    public static List<Map<String, Object>> listRooms() {
        requireOn();
        return db().query(
                "SELECT r.id, r.room_type_id, r.room_no, r.status, r.order_id, r.checkin_id, r.note, "
                        + "t.title AS room_type_title FROM room_instance r "
                        + "LEFT JOIN room_type t ON t.id=r.room_type_id ORDER BY r.room_no",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("roomTypeId", rs.getLong("room_type_id"));
                    m.put("roomNo", rs.getString("room_no"));
                    m.put("status", rs.getString("status"));
                    m.put("orderId", rs.getObject("order_id"));
                    m.put("checkinId", rs.getObject("checkin_id"));
                    m.put("note", rs.getString("note"));
                    m.put("roomTypeTitle", rs.getString("room_type_title"));
                    return m;
                });
    }

    public static List<Map<String, Object>> dirtyRooms() {
        requireOn();
        List<Map<String, Object>> all = listRooms();
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> r : all) {
            if (DIRTY.equals(String.valueOf(r.get("status")))) out.add(r);
        }
        return out;
    }

    public static Map<String, Object> setStatus(long roomId, String newStatus, String operator, String note) {
        requireOn();
        if (roomId <= 0) throw new IllegalArgumentException("请选择房间");
        String ns = newStatus == null ? "" : newStatus.trim();
        if (!VACANT.equals(ns) && !BOOKED.equals(ns) && !STAYING.equals(ns)
                && !DIRTY.equals(ns) && !REPAIR.equals(ns)) {
            throw new IllegalArgumentException("房间状态无效");
        }
        List<Map<String, Object>> rows = db().query(
                "SELECT id, status FROM room_instance WHERE id=?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("status", rs.getString("status"));
                    return m;
                },
                roomId);
        if (rows.isEmpty()) throw new IllegalArgumentException("房间不存在");
        String old = String.valueOf(rows.get(0).get("status"));
        db().update(
                "UPDATE room_instance SET status=?, note=?, updated_at=? WHERE id=?",
                ns,
                note == null ? "" : note,
                new Timestamp(System.currentTimeMillis()),
                roomId);
        log(roomId, old, ns, operator, note);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", roomId);
        out.put("status", ns);
        return out;
    }

    public static void assignOrder(long roomId, long orderId, String operator) {
        requireOn();
        setStatus(roomId, BOOKED, operator, "分房");
        db().update(
                "UPDATE room_instance SET order_id=?, updated_at=? WHERE id=?",
                orderId > 0 ? orderId : null,
                new Timestamp(System.currentTimeMillis()),
                roomId);
    }

    public static void markStaying(long roomId, long orderId, long checkinId, String operator) {
        requireOn();
        db().update(
                "UPDATE room_instance SET status=?, order_id=?, checkin_id=?, updated_at=? WHERE id=?",
                STAYING,
                orderId > 0 ? orderId : null,
                checkinId > 0 ? checkinId : null,
                new Timestamp(System.currentTimeMillis()),
                roomId);
        log(roomId, BOOKED, STAYING, operator, "入住");
    }

    public static void markDirtyAfterCheckout(long roomId, String operator) {
        requireOn();
        db().update(
                "UPDATE room_instance SET status=?, order_id=NULL, checkin_id=NULL, updated_at=? WHERE id=?",
                DIRTY,
                new Timestamp(System.currentTimeMillis()),
                roomId);
        log(roomId, STAYING, DIRTY, operator, "退房待打扫");
    }

    public static Map<String, Object> completeClean(long roomId, String operator) {
        requireOn();
        return setStatus(roomId, VACANT, operator, "打扫完成");
    }

    private static void log(long roomId, String oldStatus, String newStatus, String operator, String note) {
        db().update(
                "INSERT INTO room_status_log(room_id, old_status, new_status, operator_username, note, created_at) "
                        + "VALUES(?,?,?,?,?,?)",
                roomId,
                oldStatus == null ? "" : oldStatus,
                newStatus == null ? "" : newStatus,
                operator == null ? "" : operator,
                note == null ? "" : note,
                new Timestamp(System.currentTimeMillis()));
    }
}
