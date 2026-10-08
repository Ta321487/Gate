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

/** 订单评价：已完成订单星级+文字；管理端可回复；T-09 晒图/追评/好评率。 */
public final class OrderReviewStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final String TABLE = "order_review";
    private static boolean enabled;
    private static Boolean hasImageUrl;
    private static Boolean hasFollowBody;

    private OrderReviewStore() {}

    public static void configure(boolean on) {
        enabled = on;
        hasImageUrl = null;
        hasFollowBody = null;
        if (enabled) ensureTable();
    }

    public static boolean enabled() {
        return enabled;
    }

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    private static boolean hasCol(String col) {
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE()"
                            + " AND TABLE_NAME=? AND COLUMN_NAME=?",
                    Integer.class, TABLE, col);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    private static boolean hasImageUrl() {
        if (hasImageUrl == null) hasImageUrl = hasCol("image_url");
        return hasImageUrl;
    }

    private static boolean hasFollowBody() {
        if (hasFollowBody == null) hasFollowBody = hasCol("follow_body");
        return hasFollowBody;
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
        return submit(username, orderId, rating, body, null);
    }

    public static Map<String, Object> submit(
            String username, long orderId, int rating, String body, String imageUrl) {
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
        String img = imageUrl == null ? "" : imageUrl.trim();
        if (img.length() > 255) img = img.substring(0, 255);
        String finalText = text;
        String finalImg = img;
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps;
            if (hasImageUrl() && !finalImg.isBlank()) {
                ps = con.prepareStatement(
                        "INSERT INTO " + TABLE
                                + " (order_id,username,rating,body,image_url,created_at) VALUES (?,?,?,?,?,?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setLong(1, orderId);
                ps.setString(2, username);
                ps.setInt(3, rating);
                ps.setString(4, finalText);
                ps.setString(5, finalImg);
                ps.setTimestamp(6, Timestamp.valueOf(LocalDateTime.now()));
            } else {
                ps = con.prepareStatement(
                        "INSERT INTO " + TABLE + " (order_id,username,rating,body,created_at) VALUES (?,?,?,?,?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setLong(1, orderId);
                ps.setString(2, username);
                ps.setInt(3, rating);
                ps.setString(4, finalText);
                ps.setTimestamp(5, Timestamp.valueOf(LocalDateTime.now()));
            }
            return ps;
        }, kh);
        Number key = kh.getKey();
        return get(key == null ? 0L : key.longValue());
    }

    /** T-09：确认收货评价后再补一次追评。 */
    public static Map<String, Object> follow(String username, long reviewId, String followBody) {
        require();
        if (!hasFollowBody()) throw new IllegalStateException("系统未开通追评");
        Map<String, Object> cur = get(reviewId);
        if (cur == null) throw new IllegalArgumentException("评价不存在");
        if (!username.equals(String.valueOf(cur.get("username")))) {
            throw new IllegalStateException("无权追评");
        }
        String existing = String.valueOf(cur.getOrDefault("followBody", "")).trim();
        if (!existing.isBlank()) throw new IllegalStateException("已追评过");
        String text = followBody == null ? "" : followBody.trim();
        if (text.isBlank()) throw new IllegalArgumentException("请填写追评");
        if (text.length() > 500) text = text.substring(0, 500);
        db().update(
                "UPDATE " + TABLE + " SET follow_body=?, follow_at=? WHERE id=?",
                text, Timestamp.valueOf(LocalDateTime.now()), reviewId);
        return get(reviewId);
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

    /** 商品详情：按订单明细 item_id 汇总评价（公开只读）；附好评率。 */
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
            empty.put("goodRate", null);
            empty.put("goodCount", 0);
            empty.put("ratedCount", 0);
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
        attachGoodRate(out, itemId, lineTable);
        return out;
    }

    private static void attachGoodRate(Map<String, Object> out, long itemId, String lineTable) {
        try {
            Integer rated = db().queryForObject(
                    "SELECT COUNT(DISTINCT r.id) FROM " + TABLE + " r"
                            + " INNER JOIN " + lineTable + " l ON l.order_id=r.order_id"
                            + " WHERE l.item_id=?",
                    Integer.class, itemId);
            Integer good = db().queryForObject(
                    "SELECT COUNT(DISTINCT r.id) FROM " + TABLE + " r"
                            + " INNER JOIN " + lineTable + " l ON l.order_id=r.order_id"
                            + " WHERE l.item_id=? AND r.rating>=4",
                    Integer.class, itemId);
            int r = rated == null ? 0 : rated;
            int g = good == null ? 0 : good;
            out.put("ratedCount", r);
            out.put("goodCount", g);
            if (r <= 0) {
                out.put("goodRate", null);
            } else {
                out.put("goodRate", Math.round(g * 1000.0 / r) / 10.0);
            }
        } catch (Exception e) {
            out.put("ratedCount", 0);
            out.put("goodCount", 0);
            out.put("goodRate", null);
        }
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
        if (hasImageUrl()) {
            try {
                String img = rs.getString("image_url");
                m.put("imageUrl", img == null ? "" : img);
            } catch (Exception ignored) {
                m.put("imageUrl", "");
            }
        }
        if (hasFollowBody()) {
            try {
                String fb = rs.getString("follow_body");
                m.put("followBody", fb == null ? "" : fb);
                Timestamp fa = rs.getTimestamp("follow_at");
                m.put("followAt", fa == null ? null : fa.toLocalDateTime().format(FMT));
            } catch (Exception ignored) {
                m.put("followBody", "");
                m.put("followAt", null);
            }
        }
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
