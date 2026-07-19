package com.thesis.capability;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 能力 order_lines：购物车 + 多明细订单（无真支付）。
 */
public final class OrderStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private static String CART = "";
    private static String ORDER = "";
    private static String LINE = "";
    private static boolean enabled = false;
    private static boolean useQuota = true;

    private OrderStore() {}

    public static void bind(String cartTable, String orderTable, String lineTable, boolean quota) {
        CART = cartTable == null ? "" : cartTable.trim();
        ORDER = orderTable == null ? "" : orderTable.trim();
        LINE = lineTable == null ? "" : lineTable.trim();
        enabled = !CART.isBlank() && !ORDER.isBlank() && !LINE.isBlank();
        useQuota = quota;
    }

    public static void unbind() {
        enabled = false;
        CART = ORDER = LINE = "";
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

    private static double priceOf(Map<String, Object> item) {
        // 约定：author 存单价（元）
        Object raw = item.get("author");
        if (raw == null) return 0;
        try {
            return Double.parseDouble(String.valueOf(raw).replace("¥", "").trim());
        } catch (Exception e) {
            return 0;
        }
    }

    public static List<Map<String, Object>> listCart(String username) {
        requireEnabled();
        return db().query(
                "SELECT c.id, c.item_id, c.qty FROM " + CART + " c WHERE c.username=? ORDER BY c.id",
                (rs, i) -> enrichCartRow(rs.getLong("id"), rs.getLong("item_id"), rs.getInt("qty")),
                username);
    }

    private static Map<String, Object> enrichCartRow(long id, long itemId, int qty) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", id);
        m.put("itemId", itemId);
        m.put("qty", qty);
        Map<String, Object> item = ArchiveStore.getItem(itemId);
        if (item != null) {
            m.put("title", item.get("title"));
            m.put("priceYuan", priceOf(item));
            m.put("stock", item.get("stock"));
            m.put("coverUrl", item.get("coverUrl"));
            m.put("categoryName", item.get("categoryName"));
        } else {
            m.put("title", "");
            m.put("priceYuan", 0);
            m.put("stock", 0);
        }
        double price = ((Number) m.get("priceYuan")).doubleValue();
        m.put("lineYuan", round2(price * qty));
        return m;
    }

    public static Map<String, Object> upsertCart(String username, long itemId, int qty) {
        requireEnabled();
        if (qty <= 0) {
            removeCart(username, itemId);
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("removed", true);
            return out;
        }
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) throw new IllegalArgumentException("商品不存在");
        Integer exist = db().queryForObject(
                "SELECT COUNT(*) FROM " + CART + " WHERE username=? AND item_id=?",
                Integer.class, username, itemId);
        if (exist != null && exist > 0) {
            db().update("UPDATE " + CART + " SET qty=? WHERE username=? AND item_id=?", qty, username, itemId);
        } else {
            db().update("INSERT INTO " + CART + " (username,item_id,qty) VALUES (?,?,?)", username, itemId, qty);
        }
        List<Map<String, Object>> rows = db().query(
                "SELECT id, item_id, qty FROM " + CART + " WHERE username=? AND item_id=?",
                (rs, i) -> enrichCartRow(rs.getLong("id"), rs.getLong("item_id"), rs.getInt("qty")),
                username, itemId);
        return rows.isEmpty() ? Map.of() : rows.get(0);
    }

    public static boolean removeCart(String username, long itemId) {
        requireEnabled();
        return db().update("DELETE FROM " + CART + " WHERE username=? AND item_id=?", username, itemId) > 0;
    }

    public static void clearCart(String username) {
        requireEnabled();
        db().update("DELETE FROM " + CART + " WHERE username=?", username);
    }

    public static Map<String, Object> placeOrder(String username, String remark) {
        requireEnabled();
        List<Map<String, Object>> cart = listCart(username);
        if (cart.isEmpty()) throw new IllegalStateException("购物车为空");
        double total = 0;
        for (Map<String, Object> line : cart) {
            int qty = ((Number) line.get("qty")).intValue();
            long itemId = ((Number) line.get("itemId")).longValue();
            Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
            if (item == null) throw new IllegalStateException("商品不存在：" + line.get("title"));
            int stock = item.get("stock") instanceof Number n ? n.intValue() : 0;
            if (useQuota && stock < qty) {
                throw new IllegalStateException("库存不足：「" + item.get("title") + "」仅剩 " + stock);
            }
            total += priceOf(item) * qty;
        }
        total = round2(total);
        String note = remark == null ? "" : remark.trim();
        KeyHolder kh = new GeneratedKeyHolder();
        double finalTotal = total;
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO " + ORDER + " (username,status,total_yuan,remark,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            Timestamp now = Timestamp.valueOf(LocalDateTime.now());
            ps.setString(1, username);
            ps.setString(2, "pending");
            ps.setBigDecimal(3, BigDecimal.valueOf(finalTotal).setScale(2, RoundingMode.HALF_UP));
            ps.setString(4, note);
            ps.setTimestamp(5, now);
            ps.setTimestamp(6, now);
            return ps;
        }, kh);
        long orderId = kh.getKey() == null ? 0L : kh.getKey().longValue();
        for (Map<String, Object> line : cart) {
            long itemId = ((Number) line.get("itemId")).longValue();
            int qty = ((Number) line.get("qty")).intValue();
            Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
            double price = priceOf(item);
            db().update(
                    "INSERT INTO " + LINE + " (order_id,item_id,title,price_yuan,qty) VALUES (?,?,?,?,?)",
                    orderId, itemId, String.valueOf(item.get("title")), price, qty);
            if (useQuota) {
                ArchiveStore.adjustStock(itemId, -qty);
            }
        }
        clearCart(username);
        return getOrder(orderId);
    }

    /** 预约域联动：单明细订单 */
    public static Map<String, Object> placeSimple(
            String username, long itemId, String title, double priceYuan, int qty, String remark) {
        if (!enabled) return null;
        if (qty < 1) qty = 1;
        KeyHolder kh = new GeneratedKeyHolder();
        int q = qty;
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO " + ORDER + " (username,status,total_yuan,remark,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            Timestamp now = Timestamp.valueOf(LocalDateTime.now());
            double total = round2(priceYuan * q);
            ps.setString(1, username);
            ps.setString(2, "pending");
            ps.setBigDecimal(3, BigDecimal.valueOf(total).setScale(2, RoundingMode.HALF_UP));
            ps.setString(4, remark == null ? "" : remark);
            ps.setTimestamp(5, now);
            ps.setTimestamp(6, now);
            return ps;
        }, kh);
        long orderId = kh.getKey() == null ? 0L : kh.getKey().longValue();
        db().update(
                "INSERT INTO " + LINE + " (order_id,item_id,title,price_yuan,qty) VALUES (?,?,?,?,?)",
                orderId, itemId, title == null ? "" : title, priceYuan, q);
        return getOrder(orderId);
    }

    public static Map<String, Object> getOrder(long id) {
        requireEnabled();
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM " + ORDER + " WHERE id=?", (rs, i) -> mapOrder(rs), id);
        if (list.isEmpty()) return null;
        Map<String, Object> m = list.get(0);
        m.put("lines", listLines(id));
        return m;
    }

    private static List<Map<String, Object>> listLines(long orderId) {
        return db().query(
                "SELECT * FROM " + LINE + " WHERE order_id=? ORDER BY id",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("orderId", rs.getLong("order_id"));
                    m.put("itemId", rs.getLong("item_id"));
                    m.put("title", rs.getString("title"));
                    m.put("priceYuan", rs.getDouble("price_yuan"));
                    m.put("qty", rs.getInt("qty"));
                    m.put("lineYuan", round2(rs.getDouble("price_yuan") * rs.getInt("qty")));
                    return m;
                },
                orderId);
    }

    public static Map<String, Object> pageOrders(String username, String status, int page, int size) {
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
        Integer total = db().queryForObject("SELECT COUNT(*) FROM " + ORDER + where, Integer.class, args.toArray());
        args.add(size);
        args.add((page - 1) * size);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM " + ORDER + where + " ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = mapOrder(rs);
                    m.put("lines", listLines(rs.getLong("id")));
                    return m;
                },
                args.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    public static Map<String, Object> advance(long orderId, String action) {
        requireEnabled();
        Map<String, Object> m = getOrder(orderId);
        if (m == null) throw new IllegalArgumentException("订单不存在");
        String st = String.valueOf(m.get("status"));
        String act = action == null ? "" : action.trim().toLowerCase(Locale.ROOT);
        String next;
        if ("confirm".equals(act) && "pending".equals(st)) next = "confirmed";
        else if ("ship".equals(act) && ("pending".equals(st) || "confirmed".equals(st))) next = "shipped";
        else if ("complete".equals(act) && ("confirmed".equals(st) || "shipped".equals(st) || "pending".equals(st)))
            next = "completed";
        else if ("cancel".equals(act) && ("pending".equals(st) || "confirmed".equals(st))) next = "cancelled";
        else throw new IllegalStateException("当前状态不可执行：" + act);
        db().update(
                "UPDATE " + ORDER + " SET status=?, updated_at=? WHERE id=?",
                next, Timestamp.valueOf(LocalDateTime.now()), orderId);
        if ("cancelled".equals(next) && useQuota) {
            for (Map<String, Object> line : listLines(orderId)) {
                ArchiveStore.adjustStock(
                        ((Number) line.get("itemId")).longValue(),
                        ((Number) line.get("qty")).intValue());
            }
        }
        return getOrder(orderId);
    }

    public static Map<String, Object> dashboard() {
        if (!enabled) return Map.of();
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("pendingOrders", countStatus("pending"));
        m.put("confirmedOrders", countStatus("confirmed"));
        m.put("shippedOrders", countStatus("shipped"));
        m.put("completedOrders", countStatus("completed"));
        return m;
    }

    public static Map<String, Object> chartStats() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("statusSeries", List.of());
        out.put("trendSeries", List.of());
        if (!enabled) return out;
        try {
            List<Map<String, Object>> status = db().query(
                    "SELECT status AS name, COUNT(*) AS value FROM " + ORDER + " GROUP BY status",
                    (rs, i) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("name", rs.getString("name"));
                        row.put("value", rs.getLong("value"));
                        return row;
                    });
            out.put("statusSeries", status);
            List<Map<String, Object>> trend = db().query(
                    "SELECT DATE_FORMAT(created_at,'%Y-%m-%d') AS day, COUNT(*) AS value FROM " + ORDER
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

    private static long countStatus(String st) {
        Long n = db().queryForObject("SELECT COUNT(*) FROM " + ORDER + " WHERE status=?", Long.class, st);
        return n == null ? 0 : n;
    }

    private static Map<String, Object> mapOrder(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("status", rs.getString("status"));
        m.put("totalYuan", rs.getDouble("total_yuan"));
        m.put("remark", rs.getString("remark"));
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        m.put("updatedAt", fmt(rs.getTimestamp("updated_at")));
        return m;
    }

    private static void requireEnabled() {
        if (!enabled) throw new IllegalStateException("订单能力未启用");
    }

    private static double round2(double v) {
        return Math.round(v * 100.0) / 100.0;
    }
}
