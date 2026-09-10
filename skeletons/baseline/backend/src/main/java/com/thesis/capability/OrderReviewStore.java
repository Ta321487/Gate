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
        if (!"completed".equals(String.valueOf(order.get("status")))
                && !"signed".equals(String.valueOf(order.get("status")))) {
            throw new IllegalStateException("确认收货后方可评价");
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

    public static boolean delete(long id) {
        require();
        return db().update("DELETE FROM " + TABLE + " WHERE id=?", id) > 0;
    }

    /** 商品详情：按订单明细 item_id 汇总评价（公开只读）。 */
    public static Map<String, Object> pageByItem(long itemId, int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        String lineTable = OrderStore.lineTable();
        if (itemId <= 0 || lineTable == null || lineTable.isBlank()) {
            Map<String, Object> empty = new LinkedHashMap<>();
            empty.put("list", List.of());
            empty.put("total", 0);
            empty.put("page", page);
            empty.put("size", size);
            return empty;
        }
        String joinSql =
                " FROM " + TABLE + " r"
                        + " INNER JOIN " + lineTable + " l ON l.order_id=r.order_id"
                        + " WHERE l.item_id=?";
        Integer total = db().queryForObject("SELECT COUNT(DISTINCT r.id)" + joinSql, Integer.class, itemId);
        List<Map<String, Object>> list = db().query(
                "SELECT r.*" + joinSql + " GROUP BY r.id ORDER BY r.id DESC LIMIT ? OFFSET ?",
                (rs, i) -> map(rs),
                itemId,
                size,
                (page - 1) * size);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list == null ? List.of() : list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
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
                (rs, i) -> enrichReview(map(rs)),
                args.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list == null ? List.of() : list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    /** 多店商家：仅本店商品所在订单的评价。 */
    public static Map<String, Object> pageForMerchant(String ownerUsername, int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        String owner = ownerUsername == null ? "" : ownerUsername.trim();
        if (owner.isBlank()) {
            Map<String, Object> empty = new LinkedHashMap<>();
            empty.put("list", List.of());
            empty.put("total", 0);
            empty.put("page", page);
            empty.put("size", size);
            return empty;
        }
        String lineTable = OrderStore.lineTable();
        String itemTable = ArchiveStore.itemTable();
        if (lineTable == null || lineTable.isBlank() || itemTable == null || itemTable.isBlank()
                || !ArchiveStore.hasOwnerUsername()) {
            return page(null, page, size);
        }
        String join =
                " FROM " + TABLE + " r"
                        + " INNER JOIN " + lineTable + " l ON l.order_id=r.order_id"
                        + " INNER JOIN " + itemTable + " i ON i.id=l.item_id AND i.owner_username=?"
                        + " ";
        Integer total = db().queryForObject(
                "SELECT COUNT(DISTINCT r.id)" + join, Integer.class, owner);
        List<Map<String, Object>> list = db().query(
                "SELECT r.*" + join + " GROUP BY r.id ORDER BY r.id DESC LIMIT ? OFFSET ?",
                (rs, i) -> enrichReview(map(rs)),
                owner,
                size,
                (page - 1) * size);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list == null ? List.of() : list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    public static boolean merchantOwnsReview(String ownerUsername, long reviewId) {
        Map<String, Object> cur = get(reviewId);
        if (cur == null) return false;
        long orderId = toLong(cur.get("orderId"));
        return OrderStore.merchantOwnsOrder(ownerUsername, orderId);
    }

    private static Map<String, Object> enrichReview(Map<String, Object> m) {
        if (m == null) return null;
        try {
            long orderId = toLong(m.get("orderId"));
            if (orderId > 0) {
                Map<String, Object> order = OrderStore.getOrder(orderId);
                if (order != null && order.get("lines") instanceof List<?> lines && !lines.isEmpty()) {
                    List<String> titles = new ArrayList<>();
                    String shop = "";
                    for (Object o : lines) {
                        if (!(o instanceof Map<?, ?> line)) continue;
                        Object t = line.get("title");
                        if (t != null && !String.valueOf(t).isBlank()) titles.add(String.valueOf(t));
                        if (shop.isBlank() && line.get("shopName") != null) {
                            shop = String.valueOf(line.get("shopName")).trim();
                        }
                    }
                    if (!titles.isEmpty()) m.put("itemTitles", String.join("；", titles));
                    if (!shop.isBlank()) m.put("shopName", shop);
                }
            }
        } catch (Exception ignored) {
        }
        return m;
    }

    private static long toLong(Object o) {
        if (o instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(String.valueOf(o));
        } catch (Exception e) {
            return 0L;
        }
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
