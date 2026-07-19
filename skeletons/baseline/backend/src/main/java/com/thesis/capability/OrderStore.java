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
        AddressStore.resetCache();
        if (enabled) ensureDeliveryColumns();
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
        return placeOrder(username, remark, null, null, null, null, null, null);
    }

    /**
     * @param addressId 地址簿 id；也可直接传 receiver/phone/address 快照
     * @param tasteNote 口味 / 忌口等（点餐常用）
     */
    public static Map<String, Object> placeOrder(
            String username,
            String remark,
            Long addressId,
            String receiverName,
            String receiverPhone,
            String addressLine,
            String deliveryType,
            String tasteNote) {
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
        String taste = tasteNote == null ? "" : tasteNote.trim();
        String dtype = deliveryType == null ? "" : deliveryType.trim();
        String rName = receiverName == null ? "" : receiverName.trim();
        String rPhone = receiverPhone == null ? "" : receiverPhone.trim();
        String addr = addressLine == null ? "" : addressLine.trim();
        if (addressId != null && addressId > 0 && AddressStore.available()) {
            Map<String, Object> a = AddressStore.get(addressId, username);
            if (a == null) throw new IllegalArgumentException("收货地址不存在");
            if (rName.isBlank()) rName = String.valueOf(a.getOrDefault("contactName", ""));
            if (rPhone.isBlank()) rPhone = String.valueOf(a.getOrDefault("phone", ""));
            if (addr.isBlank()) addr = String.valueOf(a.getOrDefault("addressLine", ""));
        }
        // 配送到家类：地址必填；到店自提可空地址
        boolean needAddr = dtype.isBlank() || dtype.contains("配送") || dtype.contains("快递") || "配送到家".equals(dtype);
        if (needAddr && (rName.isBlank() || rPhone.isBlank() || addr.isBlank())) {
            throw new IllegalArgumentException("请选择或填写收货人、手机与地址");
        }
        if (!needAddr && rName.isBlank()) {
            rName = username;
        }
        KeyHolder kh = new GeneratedKeyHolder();
        double finalTotal = total;
        String fName = rName, fPhone = rPhone, fAddr = addr, fType = dtype, fTaste = taste;
        boolean hasDelivery = hasOrderColumn("receiver_name");
        db().update(con -> {
            PreparedStatement ps;
            Timestamp now = Timestamp.valueOf(LocalDateTime.now());
            if (hasDelivery) {
                ps = con.prepareStatement(
                        "INSERT INTO " + ORDER
                                + " (username,status,total_yuan,remark,receiver_name,receiver_phone,address_line,delivery_type,taste_note,created_at,updated_at)"
                                + " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setString(1, username);
                ps.setString(2, "pending");
                ps.setBigDecimal(3, BigDecimal.valueOf(finalTotal).setScale(2, RoundingMode.HALF_UP));
                ps.setString(4, note);
                ps.setString(5, fName);
                ps.setString(6, fPhone);
                ps.setString(7, fAddr);
                ps.setString(8, fType);
                ps.setString(9, fTaste);
                ps.setTimestamp(10, now);
                ps.setTimestamp(11, now);
            } else {
                ps = con.prepareStatement(
                        "INSERT INTO " + ORDER + " (username,status,total_yuan,remark,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setString(1, username);
                ps.setString(2, "pending");
                ps.setBigDecimal(3, BigDecimal.valueOf(finalTotal).setScale(2, RoundingMode.HALF_UP));
                String merged = note;
                if (!fTaste.isBlank()) merged = (merged.isBlank() ? "" : merged + "；") + "口味:" + fTaste;
                if (!fAddr.isBlank()) merged = (merged.isBlank() ? "" : merged + "；") + "地址:" + fName + " " + fPhone + " " + fAddr;
                ps.setString(4, merged);
                ps.setTimestamp(5, now);
                ps.setTimestamp(6, now);
            }
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
        return placeSimple(username, itemId, title, priceYuan, qty, remark, null);
    }

    public static Map<String, Object> placeSimple(
            String username, long itemId, String title, double priceYuan, int qty, String remark, Long reservationId) {
        if (!enabled) return null;
        if (qty < 1) qty = 1;
        KeyHolder kh = new GeneratedKeyHolder();
        int q = qty;
        boolean withResv = reservationId != null && reservationId > 0 && hasOrderColumn("reservation_id");
        db().update(con -> {
            PreparedStatement ps;
            Timestamp now = Timestamp.valueOf(LocalDateTime.now());
            double total = round2(priceYuan * q);
            if (withResv) {
                ps = con.prepareStatement(
                        "INSERT INTO " + ORDER
                                + " (username,status,total_yuan,remark,reservation_id,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setString(1, username);
                ps.setString(2, "pending");
                ps.setBigDecimal(3, BigDecimal.valueOf(total).setScale(2, RoundingMode.HALF_UP));
                ps.setString(4, remark == null ? "" : remark);
                ps.setLong(5, reservationId);
                ps.setTimestamp(6, now);
                ps.setTimestamp(7, now);
            } else {
                ps = con.prepareStatement(
                        "INSERT INTO " + ORDER + " (username,status,total_yuan,remark,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setString(1, username);
                ps.setString(2, "pending");
                ps.setBigDecimal(3, BigDecimal.valueOf(total).setScale(2, RoundingMode.HALF_UP));
                ps.setString(4, remark == null ? "" : remark);
                ps.setTimestamp(5, now);
                ps.setTimestamp(6, now);
            }
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
        return advance(orderId, action, null);
    }

    public static Map<String, Object> advance(long orderId, String action, Map<String, Object> opts) {
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
        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        if ("shipped".equals(next) && hasOrderColumn("tracking_no")) {
            String tracking = opts == null ? "" : String.valueOf(opts.getOrDefault("trackingNo", "")).trim();
            String pickup = opts == null ? "" : String.valueOf(opts.getOrDefault("pickupCode", "")).trim();
            if (pickup.isBlank() && hasOrderColumn("pickup_code")) {
                // 点餐自取：自动生成取餐码
                String dtype = String.valueOf(m.getOrDefault("deliveryType", ""));
                if (dtype.contains("自取") || dtype.contains("堂食")) {
                    pickup = String.format("%04d", (int) (orderId % 10000));
                }
            }
            if (hasOrderColumn("shipped_at")) {
                db().update(
                        "UPDATE " + ORDER + " SET status=?, tracking_no=?, pickup_code=?, shipped_at=?, updated_at=? WHERE id=?",
                        next, tracking, pickup, now, now, orderId);
            } else {
                db().update(
                        "UPDATE " + ORDER + " SET status=?, tracking_no=?, pickup_code=?, updated_at=? WHERE id=?",
                        next, tracking, pickup, now, orderId);
            }
        } else {
            db().update(
                    "UPDATE " + ORDER + " SET status=?, updated_at=? WHERE id=?",
                    next, now, orderId);
        }
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
        m.put("receiverName", safeStr(rs, "receiver_name"));
        m.put("receiverPhone", safeStr(rs, "receiver_phone"));
        m.put("addressLine", safeStr(rs, "address_line"));
        m.put("deliveryType", safeStr(rs, "delivery_type"));
        m.put("tasteNote", safeStr(rs, "taste_note"));
        m.put("trackingNo", safeStr(rs, "tracking_no"));
        m.put("pickupCode", safeStr(rs, "pickup_code"));
        m.put("shippedAt", fmt(safeTs(rs, "shipped_at")));
        long rid = safeLong(rs, "reservation_id");
        if (rid > 0) m.put("reservationId", rid);
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        m.put("updatedAt", fmt(rs.getTimestamp("updated_at")));
        return m;
    }

    private static Timestamp safeTs(java.sql.ResultSet rs, String col) {
        try {
            return rs.getTimestamp(col);
        } catch (Exception e) {
            return null;
        }
    }

    private static long safeLong(java.sql.ResultSet rs, String col) {
        try {
            long v = rs.getLong(col);
            return rs.wasNull() ? 0L : v;
        } catch (Exception e) {
            return 0L;
        }
    }

    private static String safeStr(java.sql.ResultSet rs, String col) {
        try {
            String v = rs.getString(col);
            return v == null ? "" : v;
        } catch (Exception e) {
            return "";
        }
    }

    private static boolean hasOrderColumn(String col) {
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=? AND COLUMN_NAME=?",
                    Integer.class, ORDER, col);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    private static void ensureDeliveryColumns() {
        ensureOrderColumn("receiver_name", "VARCHAR(64) DEFAULT ''");
        ensureOrderColumn("receiver_phone", "VARCHAR(32) DEFAULT ''");
        ensureOrderColumn("address_line", "VARCHAR(255) DEFAULT ''");
        ensureOrderColumn("delivery_type", "VARCHAR(32) DEFAULT ''");
        ensureOrderColumn("taste_note", "VARCHAR(255) DEFAULT ''");
        ensureOrderColumn("tracking_no", "VARCHAR(64) DEFAULT ''");
        ensureOrderColumn("pickup_code", "VARCHAR(32) DEFAULT ''");
        ensureOrderColumn("shipped_at", "DATETIME NULL");
        ensureOrderColumn("reservation_id", "BIGINT NULL");
    }

    private static void ensureOrderColumn(String col, String ddlType) {
        if (hasOrderColumn(col)) return;
        try {
            db().execute("ALTER TABLE " + ORDER + " ADD COLUMN " + col + " " + ddlType);
        } catch (Exception ignored) {
        }
    }

    private static void requireEnabled() {
        if (!enabled) throw new IllegalStateException("订单能力未启用");
    }

    private static double round2(double v) {
        return Math.round(v * 100.0) / 100.0;
    }
}
