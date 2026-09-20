package com.thesis.capability;

import com.thesis.config.MybatisSupport;
import com.thesis.config.MbSql;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/** 数字商品：付款后写入激活码/链接，跳过发货。 */
public final class DigitalGoodsStore {

    private static boolean enabled;

    private DigitalGoodsStore() {}

    public static void configure(boolean on) {
        enabled = on;
    }

    public static boolean enabled() {
        return enabled;
    }

    public static void deliverOnPay(long orderId) {
        if (!enabled || orderId <= 0) return;
        Map<String, Object> order = OrderStore.getOrder(orderId);
        if (order == null) return;
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> lines = (List<Map<String, Object>>) order.get("lines");
        if (lines == null) lines = List.of();
        for (Map<String, Object> line : lines) {
            long itemId = ((Number) line.getOrDefault("itemId", 0L)).longValue();
            Map<String, Object> payload = takeOrMake(itemId);
            try {
                db().update(
                        "INSERT INTO digital_delivery (order_id, item_id, kind, code_value, link_url, created_at) VALUES (?,?,?,?,?,?)",
                        orderId,
                        itemId,
                        payload.get("kind"),
                        payload.get("codeValue"),
                        payload.get("linkUrl"),
                        Timestamp.valueOf(LocalDateTime.now()));
            } catch (Exception e) {
                throw new IllegalStateException("系统未配置数字交付，无法下单", e);
            }
        }
        String orderTable = OrderStore.orderTable();
        if (orderTable == null || orderTable.isBlank()) orderTable = "biz_order";
        db().update(
                "UPDATE " + orderTable + " SET status='confirmed', updated_at=? WHERE id=? AND status='pending'",
                Timestamp.valueOf(LocalDateTime.now()),
                orderId);
        try {
            db().update("UPDATE " + orderTable + " SET fulfill_mode='digital' WHERE id=?", orderId);
        } catch (Exception ignored) {
        }
    }

    public static List<Map<String, Object>> mine(String username) {
        requireOn();
        String order = OrderStore.orderTable();
        if (order == null || order.isBlank()) order = "biz_order";
        return db().query(
                "SELECT d.id, d.order_id, d.item_id, d.kind, d.code_value, d.link_url, d.created_at"
                        + " FROM digital_delivery d INNER JOIN " + order + " o ON o.id=d.order_id"
                        + " WHERE o.username=? ORDER BY d.id DESC",
                (rs, i) -> row(rs),
                username);
    }

    public static List<Map<String, Object>> listCodes() {
        requireOn();
        return db().query(
                "SELECT id, item_id, code_value, link_url, kind, used_order_id, enabled FROM digital_code ORDER BY id",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("itemId", rs.getLong("item_id"));
                    m.put("codeValue", rs.getString("code_value"));
                    m.put("linkUrl", rs.getString("link_url"));
                    m.put("kind", rs.getString("kind"));
                    long used = rs.getLong("used_order_id");
                    m.put("usedOrderId", rs.wasNull() ? null : used);
                    m.put("enabled", rs.getInt("enabled") == 1);
                    return m;
                });
    }

    public static Map<String, Object> saveCode(Map<String, Object> body) {
        requireOn();
        long itemId = num(body.get("itemId"));
        String kind = str(body.get("kind"));
        if (kind.isBlank()) kind = "code";
        String code = str(body.get("codeValue"));
        String link = str(body.get("linkUrl"));
        boolean on = body.get("enabled") == null || Boolean.TRUE.equals(body.get("enabled"))
                || "1".equals(String.valueOf(body.get("enabled")));
        Object idObj = body.get("id");
        if (idObj != null && num(idObj) > 0) {
            db().update(
                    "UPDATE digital_code SET item_id=?, code_value=?, link_url=?, kind=?, enabled=? WHERE id=?",
                    itemId, code, link, kind, on ? 1 : 0, num(idObj));
        } else {
            db().update(
                    "INSERT INTO digital_code (item_id, code_value, link_url, kind, enabled) VALUES (?,?,?,?,?)",
                    itemId, code, link, kind, on ? 1 : 0);
        }
        return Map.of("ok", true);
    }

    private static Map<String, Object> takeOrMake(long itemId) {
        String kind = "code";
        try {
            List<String> kinds = db().query(
                    "SELECT digital_kind FROM " + itemTable() + " WHERE id=?",
                    (rs, i) -> rs.getString(1),
                    itemId);
            if (!kinds.isEmpty() && kinds.get(0) != null && !kinds.get(0).isBlank()) {
                kind = kinds.get(0);
            }
        } catch (Exception ignored) {
        }
        try {
            List<Map<String, Object>> pool = db().query(
                    "SELECT id, code_value, link_url, kind FROM digital_code"
                            + " WHERE enabled=1 AND (used_order_id IS NULL OR used_order_id=0)"
                            + " AND (item_id=? OR item_id IS NULL OR item_id=0) ORDER BY id LIMIT 1",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("id", rs.getLong("id"));
                        m.put("codeValue", rs.getString("code_value"));
                        m.put("linkUrl", rs.getString("link_url"));
                        m.put("kind", rs.getString("kind"));
                        return m;
                    },
                    itemId);
            if (!pool.isEmpty()) {
                Map<String, Object> row = pool.get(0);
                return row;
            }
        } catch (Exception ignored) {
        }
        Map<String, Object> made = new LinkedHashMap<>();
        made.put("kind", kind);
        if ("link".equals(kind)) {
            made.put("codeValue", "");
            made.put("linkUrl", "/files/digital-" + itemId + ".pdf");
        } else if ("permit".equals(kind)) {
            made.put("codeValue", "PERMIT-" + itemId + "-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase());
            made.put("linkUrl", "");
        } else {
            made.put("codeValue", "ACT-" + UUID.randomUUID().toString().substring(0, 10).toUpperCase());
            made.put("linkUrl", "");
        }
        return made;
    }

    private static Map<String, Object> row(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("orderId", rs.getLong("order_id"));
        m.put("itemId", rs.getLong("item_id"));
        m.put("kind", rs.getString("kind"));
        m.put("codeValue", rs.getString("code_value"));
        m.put("linkUrl", rs.getString("link_url"));
        Timestamp ts = rs.getTimestamp("created_at");
        m.put("createdAt", ts == null ? "" : ts.toLocalDateTime().toString().replace('T', ' '));
        return m;
    }

    private static String itemTable() {
        String t = ArchiveStore.itemTable();
        return t == null || t.isBlank() ? "product" : t;
    }

    private static void requireOn() {
        if (!enabled) throw new IllegalStateException("未开启数字商品");
    }

    private static String str(Object v) {
        return v == null ? "" : String.valueOf(v).trim();
    }

    private static long num(Object v) {
        if (v instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(String.valueOf(v));
        } catch (Exception e) {
            return 0;
        }
    }

    private static MbSql db() {
        return MybatisSupport.db();
    }
}
