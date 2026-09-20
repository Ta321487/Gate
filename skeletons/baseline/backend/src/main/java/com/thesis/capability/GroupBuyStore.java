package com.thesis.capability;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 拼团。下单和订单列表仍走 OrderStore，这里只做开团、参团和过期扫描。
 */
public final class GroupBuyStore {

    private static final DateTimeFormatter TS = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static boolean enabled;

    private GroupBuyStore() {}

    public static void configure(boolean on) {
        enabled = on;
    }

    public static boolean enabled() {
        return enabled;
    }

    public static void sweep() {
        if (!enabled) return;
        List<Map<String, Object>> rows;
        try {
            rows = db().query(
                    "SELECT id, target_size, deadline, status FROM group_campaign WHERE status='open'",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("id", rs.getLong("id"));
                        m.put("target", rs.getInt("target_size"));
                        m.put("deadline", rs.getTimestamp("deadline"));
                        return m;
                    });
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置拼团表", e);
        }
        LocalDateTime now = LocalDateTime.now();
        for (Map<String, Object> row : rows) {
            long id = ((Number) row.get("id")).longValue();
            int target = ((Number) row.get("target")).intValue();
            int joined = countMembers(id);
            if (joined >= target) {
                form(id);
                continue;
            }
            Object dl = row.get("deadline");
            LocalDateTime deadline = dl instanceof java.sql.Timestamp ts ? ts.toLocalDateTime() : null;
            if (deadline != null && !deadline.isAfter(now)) {
                fail(id);
            }
        }
    }

    public static void assertJoin(long campaignId, String username, List<Long> itemIds) {
        if (!enabled) throw new IllegalStateException("拼团未开启");
        Map<String, Object> camp = loadOpen(campaignId);
        long itemId = ((Number) camp.get("itemId")).longValue();
        boolean hit = false;
        if (itemIds != null) {
            for (Long id : itemIds) {
                if (id != null && id == itemId) hit = true;
            }
        }
        if (!hit) throw new IllegalArgumentException("购物车里没有这个团的商品");
        Integer mine = db().queryForObject(
                "SELECT COUNT(*) FROM group_member WHERE campaign_id=? AND username=?",
                Integer.class, campaignId, username);
        if (mine != null && mine > 0) throw new IllegalArgumentException("你已经在这个团里");
    }

    public static void join(String username, long orderId, long campaignId) {
        if (!enabled) return;
        db().update(
                "INSERT INTO group_member (campaign_id, order_id, username) VALUES (?,?,?)",
                campaignId, orderId, username);
        Map<String, Object> camp = loadOpen(campaignId);
        int target = ((Number) camp.get("target")).intValue();
        if (countMembers(campaignId) >= target) form(campaignId);
    }

    public static List<Map<String, Object>> listOpen() {
        requireOn();
        sweep();
        String item = itemTable();
        return db().query(
                "SELECT c.id, c.item_id, c.target_size, c.deadline, c.status, i.title, "
                        + "(SELECT COUNT(*) FROM group_member m WHERE m.campaign_id=c.id) AS joined "
                        + "FROM group_campaign c LEFT JOIN " + item + " i ON i.id=c.item_id "
                        + "WHERE c.status='open' AND c.deadline>NOW() ORDER BY c.deadline, c.id",
                (rs, i) -> mapOpen(rs));
    }

    public static List<Map<String, Object>> listAll() {
        requireOn();
        String item = itemTable();
        return db().query(
                "SELECT c.id, c.item_id, c.target_size, c.deadline, c.status, i.title, "
                        + "(SELECT COUNT(*) FROM group_member m WHERE m.campaign_id=c.id) AS joined "
                        + "FROM group_campaign c LEFT JOIN " + item + " i ON i.id=c.item_id ORDER BY c.id DESC",
                (rs, i) -> mapOpen(rs));
    }

    public static List<Map<String, Object>> products() {
        requireOn();
        return db().query(
                "SELECT id, title FROM " + itemTable() + " ORDER BY id",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("title", rs.getString("title"));
                    return m;
                });
    }

    public static Map<String, Object> save(Map<String, Object> body) {
        requireOn();
        if (body == null) body = Map.of();
        long itemId = lng(body.get("itemId"));
        int target = num(body.get("targetSize"));
        LocalDateTime deadline = parseTs(str(body.get("deadline")));
        if (itemId <= 0) throw new IllegalArgumentException("请选择商品");
        if (target < 2) throw new IllegalArgumentException("成团人数至少 2");
        if (deadline == null) throw new IllegalArgumentException("请选择截止时间");
        long id = lng(body.get("id"));
        if (id > 0) {
            int n = db().update(
                    "UPDATE group_campaign SET item_id=?, target_size=?, deadline=? WHERE id=? AND status='open'",
                    itemId, target, java.sql.Timestamp.valueOf(deadline), id);
            if (n <= 0) throw new IllegalArgumentException("只能修改仍开放的团");
        } else {
            db().update(
                    "INSERT INTO group_campaign (item_id, target_size, deadline, status) VALUES (?,?,?, 'open')",
                    itemId, target, java.sql.Timestamp.valueOf(deadline));
        }
        sweep();
        return Map.of("ok", true);
    }

    private static void form(long campaignId) {
        db().update("UPDATE group_campaign SET status='formed' WHERE id=? AND status='open'", campaignId);
        String order = orderTable();
        List<Long> ids = memberOrders(campaignId);
        for (Long orderId : ids) {
            db().update(
                    "UPDATE " + order + " SET status='confirmed', updated_at=NOW() WHERE id=? AND status='grouping'",
                    orderId);
        }
    }

    private static void fail(long campaignId) {
        db().update("UPDATE group_campaign SET status='failed' WHERE id=? AND status='open'", campaignId);
        String order = orderTable();
        List<Map<String, Object>> rows = db().query(
                "SELECT m.order_id, m.username, o.total_yuan FROM group_member m JOIN " + order
                        + " o ON o.id=m.order_id WHERE m.campaign_id=? AND o.status='grouping'",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("orderId", rs.getLong("order_id"));
                    m.put("username", rs.getString("username"));
                    m.put("paid", rs.getDouble("total_yuan"));
                    return m;
                },
                campaignId);
        for (Map<String, Object> row : rows) {
            long orderId = ((Number) row.get("orderId")).longValue();
            db().update(
                    "UPDATE " + order + " SET status='cancelled', updated_at=NOW() WHERE id=? AND status='grouping'",
                    orderId);
            double paid = row.get("paid") instanceof Number n ? n.doubleValue() : 0;
            if (paid > 0) {
                LoyaltyStore.refundOrderPay(String.valueOf(row.get("username")), orderId, paid);
            }
        }
    }

    private static Map<String, Object> loadOpen(long campaignId) {
        List<Map<String, Object>> rows = db().query(
                "SELECT id, item_id, target_size, deadline, status FROM group_campaign WHERE id=?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("itemId", rs.getLong("item_id"));
                    m.put("target", rs.getInt("target_size"));
                    m.put("status", rs.getString("status"));
                    java.sql.Timestamp dl = rs.getTimestamp("deadline");
                    m.put("deadline", dl == null ? null : dl.toLocalDateTime());
                    return m;
                },
                campaignId);
        if (rows == null || rows.isEmpty()) throw new IllegalArgumentException("拼团不存在");
        Map<String, Object> camp = rows.get(0);
        if (!"open".equals(camp.get("status"))) throw new IllegalArgumentException("这个团已结束");
        LocalDateTime deadline = (LocalDateTime) camp.get("deadline");
        if (deadline == null || !deadline.isAfter(LocalDateTime.now())) {
            throw new IllegalArgumentException("这个团已过截止时间");
        }
        return camp;
    }

    private static int countMembers(long campaignId) {
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM group_member WHERE campaign_id=?", Integer.class, campaignId);
        return n == null ? 0 : n;
    }

    private static List<Long> memberOrders(long campaignId) {
        List<Long> ids = db().query(
                "SELECT order_id FROM group_member WHERE campaign_id=?",
                (rs, i) -> rs.getLong("order_id"),
                campaignId);
        return ids == null ? List.of() : ids;
    }

    private static Map<String, Object> mapOpen(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        int joined = rs.getInt("joined");
        int target = rs.getInt("target_size");
        m.put("id", rs.getLong("id"));
        m.put("itemId", rs.getLong("item_id"));
        m.put("title", rs.getString("title"));
        m.put("targetSize", target);
        m.put("joined", joined);
        m.put("deadline", rs.getString("deadline"));
        m.put("status", rs.getString("status"));
        m.put("verb", joined <= 0 ? "开团" : "参团");
        return m;
    }

    private static void requireOn() {
        if (!enabled) throw new IllegalStateException("拼团未开启");
    }

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    private static String itemTable() {
        return safeIdent(ArchiveStore.itemTable(), "product");
    }

    private static String orderTable() {
        return safeIdent(OrderStore.orderTable(), "biz_order");
    }

    private static String safeIdent(String raw, String fallback) {
        String t = raw == null ? "" : raw.trim();
        if (!t.matches("[A-Za-z_][A-Za-z0-9_]*")) return fallback;
        return t;
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static int num(Object o) {
        if (o instanceof Number n) return n.intValue();
        if (o == null || String.valueOf(o).isBlank()) return 0;
        return Integer.parseInt(String.valueOf(o).trim());
    }

    private static long lng(Object o) {
        if (o instanceof Number n) return n.longValue();
        if (o == null || String.valueOf(o).isBlank()) return 0;
        try {
            return Long.parseLong(String.valueOf(o).trim());
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    private static LocalDateTime parseTs(String raw) {
        if (raw == null || raw.isBlank()) return null;
        String s = raw.trim().replace('T', ' ');
        if (s.length() == 16) s = s + ":00";
        try {
            return LocalDateTime.parse(s, TS);
        } catch (Exception e) {
            return null;
        }
    }
}
