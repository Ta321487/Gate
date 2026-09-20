package com.thesis.capability;

import com.thesis.config.JpaDb;
import com.thesis.config.JpaSupport;

import java.math.BigDecimal;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 约拍套餐与交片。时段冲突仍由预约占用判断。 */
public final class ShootStore {

    private static boolean enabled;

    private ShootStore() {}

    public static void configure(boolean on) {
        enabled = on;
    }

    public static boolean enabled() {
        return enabled;
    }

    public static void assertBook(Map<String, Object> extras) {
        if (!enabled) return;
        if (bundle(extras) == null) throw new IllegalArgumentException("请选择套餐");
    }

    public static double bundlePrice(Map<String, Object> extras) {
        Map<String, Object> row = bundle(extras);
        if (row == null) return 0;
        return money(row.get("priceYuan")).doubleValue();
    }

    public static void attach(long reservationId, Map<String, Object> extras) {
        if (!enabled || reservationId <= 0) return;
        Map<String, Object> row = bundle(extras);
        if (row == null) throw new IllegalArgumentException("请选择套餐");
        try {
            db().update(
                    "UPDATE reservation SET bundle_id=?, bundle_yuan=? WHERE id=?",
                    lng(row.get("id")), money(row.get("priceYuan")), reservationId);
            db().update(
                    "INSERT INTO deliverable (reservation_id, file_url, delivered) VALUES (?, '', 0)",
                    reservationId);
        } catch (IllegalArgumentException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置约拍", e);
        }
    }

    public static List<Map<String, Object>> photographers() {
        if (!enabled) return List.of();
        String table = itemTable();
        return db().query(
                "SELECT id, title FROM " + table + " WHERE status='available' ORDER BY id",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("title", rs.getString("title"));
                    return m;
                });
    }

    public static List<Map<String, Object>> bundles(boolean onlyEnabled) {
        requireOn();
        String sql = onlyEnabled
                ? "SELECT id, name, price_yuan, detail FROM service_bundle WHERE enabled=1 ORDER BY id"
                : "SELECT id, name, price_yuan, detail, enabled FROM service_bundle ORDER BY id";
        return db().query(sql, (rs, i) -> bundleRow(rs, !onlyEnabled));
    }

    public static Map<String, Object> saveBundle(Map<String, Object> body) {
        requireOn();
        long id = lng(body == null ? null : body.get("id"));
        String name = str(body == null ? null : body.get("name"));
        if (name.isBlank()) throw new IllegalArgumentException("请填写套餐名称");
        BigDecimal price = money(body == null ? null : body.get("priceYuan"));
        if (price.signum() < 0) throw new IllegalArgumentException("请填写价格");
        String detail = str(body == null ? null : body.get("detail"));
        int on = body != null && body.containsKey("enabled") && !flag(body.get("enabled")) ? 0 : 1;
        try {
            if (id > 0) {
                db().update(
                        "UPDATE service_bundle SET name=?, price_yuan=?, detail=?, enabled=? WHERE id=?",
                        name, price, detail, on, id);
            } else {
                db().update(
                        "INSERT INTO service_bundle (name, price_yuan, detail, enabled) VALUES (?,?,?,?)",
                        name, price, detail, on);
            }
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置约拍", e);
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("ok", true);
        return out;
    }

    public static List<Map<String, Object>> mine(String username) {
        requireOn();
        List<Map<String, Object>> rows = db().query(
                "SELECT d.id, d.reservation_id, d.file_url, d.delivered, r.username "
                        + "FROM deliverable d JOIN reservation r ON r.id=d.reservation_id "
                        + "WHERE r.username=? ORDER BY d.id DESC",
                (rs, i) -> fileRow(rs, true),
                str(username));
        for (Map<String, Object> row : rows) hideIfPending(row);
        return rows;
    }

    public static List<Map<String, Object>> files() {
        requireOn();
        return db().query(
                "SELECT d.id, d.reservation_id, d.file_url, d.delivered, r.username "
                        + "FROM deliverable d JOIN reservation r ON r.id=d.reservation_id ORDER BY d.id DESC",
                (rs, i) -> fileRow(rs, false));
    }

    public static Map<String, Object> saveFile(Map<String, Object> body) {
        requireOn();
        long id = lng(body == null ? null : body.get("id"));
        if (id <= 0) throw new IllegalArgumentException("交片不存在");
        String url = str(body == null ? null : body.get("fileUrl"));
        int delivered = flag(body == null ? null : body.get("delivered")) ? 1 : 0;
        try {
            int n = db().update(
                    "UPDATE deliverable SET file_url=?, delivered=? WHERE id=?",
                    url, delivered, id);
            if (n == 0) throw new IllegalArgumentException("交片不存在");
        } catch (IllegalArgumentException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置约拍", e);
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("ok", true);
        return out;
    }

    private static void hideIfPending(Map<String, Object> row) {
        if (num(row.get("delivered")) != 1) row.put("fileUrl", "");
    }

    private static Map<String, Object> bundle(Map<String, Object> extras) {
        long id = lng(extras == null ? null : extras.get("bundleId"));
        if (id <= 0 && extras != null) id = lng(extras.get("bundle_id"));
        if (id <= 0) return null;
        try {
            List<Map<String, Object>> rows = db().query(
                    "SELECT id, name, price_yuan FROM service_bundle WHERE id=? AND enabled=1",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("id", rs.getLong("id"));
                        m.put("name", rs.getString("name"));
                        m.put("priceYuan", rs.getBigDecimal("price_yuan"));
                        return m;
                    },
                    id);
            return rows.isEmpty() ? null : rows.get(0);
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置约拍", e);
        }
    }

    private static Map<String, Object> bundleRow(java.sql.ResultSet rs, boolean withEnabled) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("name", rs.getString("name"));
        m.put("priceYuan", rs.getBigDecimal("price_yuan"));
        m.put("detail", rs.getString("detail"));
        if (withEnabled) m.put("enabled", rs.getInt("enabled") != 0);
        return m;
    }

    private static Map<String, Object> fileRow(java.sql.ResultSet rs, boolean mine) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("reservationId", rs.getLong("reservation_id"));
        m.put("fileUrl", rs.getString("file_url"));
        m.put("delivered", rs.getInt("delivered"));
        if (!mine) m.put("username", rs.getString("username"));
        return m;
    }

    private static String itemTable() {
        String t = ArchiveStore.itemTable();
        if (t == null || !t.matches("[A-Za-z_][A-Za-z0-9_]*")) {
            throw new IllegalStateException("系统未配置约拍");
        }
        return t;
    }

    private static void requireOn() {
        if (!enabled) throw new IllegalStateException("约拍未开启");
    }

    private static JpaDb db() {
        return JpaSupport.db();
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static int num(Object o) {
        if (o instanceof Number n) return n.intValue();
        if (o instanceof Boolean b) return b ? 1 : 0;
        return 0;
    }

    private static long lng(Object o) {
        if (o instanceof Number n) return n.longValue();
        return 0L;
    }

    private static boolean flag(Object o) {
        if (o instanceof Boolean b) return b;
        if (o instanceof Number n) return n.intValue() != 0;
        return "1".equals(str(o)) || "true".equalsIgnoreCase(str(o));
    }

    private static BigDecimal money(Object o) {
        if (o instanceof BigDecimal b) return b;
        if (o instanceof Number n) return BigDecimal.valueOf(n.doubleValue());
        if (o == null || String.valueOf(o).isBlank()) return BigDecimal.ZERO;
        try {
            return new BigDecimal(String.valueOf(o).trim());
        } catch (NumberFormatException e) {
            return BigDecimal.ZERO;
        }
    }
}
