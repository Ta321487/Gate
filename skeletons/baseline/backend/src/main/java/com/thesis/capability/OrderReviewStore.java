package com.thesis.capability;

import com.thesis.config.JdbcSupport;
import com.thesis.service.UserStore;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/** 订单评价：已完成订单星级+文字；管理端可回复。 */
public final class OrderReviewStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final String TABLE = "order_review";
    private static boolean enabled;

    private OrderReviewStore() {}

    public static void configure(boolean on) {
        enabled = on;
        if (enabled) ensureTable();
    }

    public static boolean enabled() {
        return enabled;
    }

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    private static void ensureTable() {
        try {
            db().execute(
                    "CREATE TABLE IF NOT EXISTS " + TABLE + " ("
                            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
                            + "order_id BIGINT NOT NULL,"
                            + "username VARCHAR(64) NOT NULL,"
                            + "rating INT NOT NULL,"
                            + "body VARCHAR(500) DEFAULT '',"
                            + "reply VARCHAR(500) DEFAULT '',"
                            + "replied_at DATETIME NULL,"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "UNIQUE KEY uk_order_review (order_id),"
                            + "KEY idx_review_user (username, id)"
                            + ")");
        } catch (Exception ignored) {
        }
    }

    public static Map<String, Object> submit(String username, long orderId, int rating, String body) {
        require();
        if (rating < 1 || rating > 5) throw new IllegalArgumentException("评分须为 1～5 星");
        Map<String, Object> order = OrderStore.getOrder(orderId);
        if (order == null) throw new IllegalArgumentException("订单不存在");
        if (!username.equals(String.valueOf(order.get("username")))) {
            throw new IllegalStateException("无权评价");
        }
        if (!"completed".equals(String.valueOf(order.get("status")))) {
            throw new IllegalStateException("仅已完成订单可评价");
        }
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM " + TABLE + " WHERE order_id=?", Integer.class, orderId);
        if (n != null && n > 0) throw new IllegalStateException("该订单已评价");
        String text = body == null ? "" : body.trim();
        if (text.length() > 500) text = text.substring(0, 500);
        String finalText = text;
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO " + TABLE + " (order_id,username,rating,body,created_at) VALUES (?,?,?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, orderId);
            ps.setString(2, username);
            ps.setInt(3, rating);
            ps.setString(4, finalText);
            ps.setTimestamp(5, Timestamp.valueOf(LocalDateTime.now()));
            return ps;
        }, kh);
        Number key = kh.getKey();
        return get(key == null ? 0L : key.longValue());
    }

    public static Map<String, Object> reply(long id, String reply) {
        require();
        Map<String, Object> cur = get(id);
        if (cur == null) throw new IllegalArgumentException("评价不存在");
        String text = reply == null ? "" : reply.trim();
        if (text.isBlank()) throw new IllegalArgumentException("请填写回复");
        if (text.length() > 500) text = text.substring(0, 500);
        db().update(
                "UPDATE " + TABLE + " SET reply=?, replied_at=? WHERE id=?",
                text, Timestamp.valueOf(LocalDateTime.now()), id);
        return get(id);
    }

    public static Map<String, Object> getByOrder(long orderId) {
        if (!enabled) return null;
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM " + TABLE + " WHERE order_id=?", (rs, i) -> map(rs), orderId);
        return rows == null || rows.isEmpty() ? null : rows.get(0);
    }

    public static Map<String, Object> page(String username, int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        String where = username == null || username.isBlank() ? "" : " WHERE username=?";
        Object[] countArgs = username == null || username.isBlank() ? new Object[] {} : new Object[] {username};
        Integer total = db().queryForObject("SELECT COUNT(*) FROM " + TABLE + where, Integer.class, countArgs);
        List<Object> args = new ArrayList<>();
        if (username != null && !username.isBlank()) args.add(username);
        args.add(size);
        args.add((page - 1) * size);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM " + TABLE + where + " ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> map(rs),
                args.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list == null ? List.of() : list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    private static Map<String, Object> get(long id) {
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM " + TABLE + " WHERE id=?", (rs, i) -> map(rs), id);
        return rows == null || rows.isEmpty() ? null : rows.get(0);
    }

    private static Map<String, Object> map(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("orderId", rs.getLong("order_id"));
        m.put("username", rs.getString("username"));
        m.put("rating", rs.getInt("rating"));
        m.put("body", rs.getString("body"));
        m.put("reply", rs.getString("reply") == null ? "" : rs.getString("reply"));
        Timestamp ra = rs.getTimestamp("replied_at");
        m.put("repliedAt", ra == null ? null : ra.toLocalDateTime().format(FMT));
        m.put("createdAt", rs.getTimestamp("created_at").toLocalDateTime().format(FMT));
        try {
            m.put("displayName", UserStore.displayName(rs.getString("username")));
        } catch (Exception ignored) {
        }
        return m;
    }

    private static void require() {
        if (!enabled) throw new IllegalStateException("订单评价暂不可用");
    }
}
