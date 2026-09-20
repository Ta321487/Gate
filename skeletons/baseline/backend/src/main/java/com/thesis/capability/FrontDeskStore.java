package com.thesis.capability;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.math.BigDecimal;
import java.sql.Timestamp;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 前台登记 / 挂账 / 退房结算。开题挂 front_desk 后启用。 */
public final class FrontDeskStore {

    private static boolean enabled;

    private FrontDeskStore() {}

    public static void configure(boolean on) {
        enabled = on;
    }

    public static boolean enabled() {
        return enabled;
    }

    private static void requireOn() {
        if (!enabled) throw new IllegalStateException("未开启前台登记");
    }

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    public static List<Map<String, Object>> pendingCheckin() {
        requireOn();
        return db().query(
                "SELECT o.id, o.username, o.status, o.total_yuan "
                        + "FROM biz_order o "
                        + "WHERE o.status IN ('confirmed','pending') "
                        + "AND NOT EXISTS (SELECT 1 FROM checkin c WHERE c.order_id=o.id AND c.status='checked_in') "
                        + "ORDER BY o.id DESC LIMIT 50",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("username", rs.getString("username"));
                    m.put("status", rs.getString("status"));
                    m.put("totalAmount", rs.getBigDecimal("total_yuan"));
                    m.put("nickname", rs.getString("username"));
                    return m;
                });
    }

    public static List<Map<String, Object>> pendingCheckout() {
        requireOn();
        return db().query(
                "SELECT c.id, c.order_id, c.room_id, c.guest_name, c.deposit_yuan, c.checked_in_at, "
                        + "r.room_no FROM checkin c "
                        + "LEFT JOIN room_instance r ON r.id=c.room_id "
                        + "WHERE c.status='checked_in' ORDER BY c.id DESC LIMIT 50",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("orderId", rs.getObject("order_id"));
                    m.put("roomId", rs.getObject("room_id"));
                    m.put("guestName", rs.getString("guest_name"));
                    m.put("depositYuan", rs.getBigDecimal("deposit_yuan"));
                    m.put("checkedInAt", rs.getTimestamp("checked_in_at"));
                    m.put("roomNo", rs.getString("room_no"));
                    return m;
                });
    }

    public static Map<String, Object> checkin(
            long orderId,
            long roomId,
            String guestName,
            String idNo,
            BigDecimal deposit,
            String operator) {
        requireOn();
        if (orderId <= 0) throw new IllegalArgumentException("请选择订单");
        if (roomId <= 0) throw new IllegalArgumentException("请选择房间");
        if (guestName == null || guestName.isBlank()) throw new IllegalArgumentException("请填写入住人");
        if (deposit == null) deposit = BigDecimal.ZERO;
        Integer open = db().queryForObject(
                "SELECT COUNT(1) FROM checkin WHERE order_id=? AND status='checked_in'",
                Integer.class,
                orderId);
        if (open != null && open > 0) throw new IllegalStateException("该订单已登记");
        Timestamp now = new Timestamp(System.currentTimeMillis());
        db().update(
                "INSERT INTO checkin(order_id, room_id, guest_name, id_no, deposit_yuan, status, checked_in_at, created_at) "
                        + "VALUES(?,?,?,?,?,'checked_in',?,?)",
                orderId,
                roomId,
                guestName.trim(),
                idNo == null ? "" : idNo.trim(),
                deposit,
                now,
                now);
        Long checkinId = db().queryForObject("SELECT MAX(id) FROM checkin WHERE order_id=?", Long.class, orderId);
        long cid = checkinId == null ? 0L : checkinId;
        if (RoomBoardStore.enabled()) {
            RoomBoardStore.markStaying(roomId, orderId, cid, operator);
        }
        try {
            OrderStore.advance(orderId, "ship");
        } catch (Exception ignored) {
            // 订单态若已推进则忽略
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", cid);
        out.put("orderId", orderId);
        out.put("roomId", roomId);
        return out;
    }

    public static Map<String, Object> addConsumption(long checkinId, String title, BigDecimal amount) {
        requireOn();
        if (checkinId <= 0) throw new IllegalArgumentException("请选择登记");
        if (title == null || title.isBlank()) throw new IllegalArgumentException("请填写消费项");
        if (amount == null) amount = BigDecimal.ZERO;
        Long orderId = db().queryForObject(
                "SELECT order_id FROM checkin WHERE id=?", Long.class, checkinId);
        db().update(
                "INSERT INTO consumption(checkin_id, order_id, title, amount_yuan, created_at) VALUES(?,?,?,?,?)",
                checkinId,
                orderId,
                title.trim(),
                amount,
                new Timestamp(System.currentTimeMillis()));
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("checkinId", checkinId);
        out.put("title", title.trim());
        out.put("amountYuan", amount);
        return out;
    }

    public static List<Map<String, Object>> consumptions(long checkinId) {
        requireOn();
        return db().query(
                "SELECT id, title, amount_yuan, created_at FROM consumption WHERE checkin_id=? ORDER BY id",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("title", rs.getString("title"));
                    m.put("amountYuan", rs.getBigDecimal("amount_yuan"));
                    m.put("createdAt", rs.getTimestamp("created_at"));
                    return m;
                },
                checkinId);
    }

    public static Map<String, Object> checkout(long checkinId, String note, String operator) {
        requireOn();
        if (checkinId <= 0) throw new IllegalArgumentException("请选择登记");
        List<Map<String, Object>> rows = db().query(
                "SELECT id, order_id, room_id, deposit_yuan, status FROM checkin WHERE id=?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("orderId", rs.getObject("order_id"));
                    m.put("roomId", rs.getObject("room_id"));
                    m.put("depositYuan", rs.getBigDecimal("deposit_yuan"));
                    m.put("status", rs.getString("status"));
                    return m;
                },
                checkinId);
        if (rows.isEmpty()) throw new IllegalArgumentException("登记不存在");
        Map<String, Object> c = rows.get(0);
        if (!"checked_in".equals(String.valueOf(c.get("status")))) {
            throw new IllegalStateException("已退房");
        }
        BigDecimal consume = BigDecimal.ZERO;
        List<BigDecimal> sums = db().query(
                "SELECT COALESCE(SUM(amount_yuan),0) FROM consumption WHERE checkin_id=?",
                (rs, i) -> rs.getBigDecimal(1),
                checkinId);
        if (!sums.isEmpty() && sums.get(0) != null) consume = sums.get(0);
        BigDecimal deposit = (BigDecimal) c.get("depositYuan");
        if (deposit == null) deposit = BigDecimal.ZERO;
        BigDecimal back = deposit.subtract(consume);
        if (back.compareTo(BigDecimal.ZERO) < 0) back = BigDecimal.ZERO;
        Timestamp now = new Timestamp(System.currentTimeMillis());
        Long orderId = c.get("orderId") == null ? null : ((Number) c.get("orderId")).longValue();
        Long roomId = c.get("roomId") == null ? null : ((Number) c.get("roomId")).longValue();
        db().update(
                "INSERT INTO checkout(checkin_id, order_id, room_id, settle_yuan, deposit_back_yuan, note, checked_out_at, created_at) "
                        + "VALUES(?,?,?,?,?,?,?,?)",
                checkinId,
                orderId,
                roomId,
                consume,
                back,
                note == null ? "" : note,
                now,
                now);
        db().update("UPDATE checkin SET status='checked_out' WHERE id=?", checkinId);
        if (roomId != null && roomId > 0 && RoomBoardStore.enabled()) {
            RoomBoardStore.markDirtyAfterCheckout(roomId, operator);
        }
        if (orderId != null && orderId > 0) {
            try {
                OrderStore.advance(orderId, "complete");
            } catch (Exception ignored) {
            }
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("checkinId", checkinId);
        out.put("settleYuan", consume);
        out.put("depositBackYuan", back);
        return out;
    }
}
