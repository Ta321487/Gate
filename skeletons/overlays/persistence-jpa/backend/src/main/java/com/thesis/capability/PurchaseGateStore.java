package com.thesis.capability;

import com.thesis.config.JpaDb;
import com.thesis.config.JpaSupport;

import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 购买审核与每月限购。加购和下单仍走 OrderStore，这里只做校验和审核单。
 */
public final class PurchaseGateStore {

    private static boolean enabled;

    private PurchaseGateStore() {}

    public static void configure(boolean on) {
        enabled = on;
    }

    public static boolean enabled() {
        return enabled;
    }

    public static Map<String, Object> check(String username, long itemId, int qty) {
        requireOn();
        Map<String, Object> item = loadItem(itemId);
        Map<String, Object> out = new LinkedHashMap<>();
        int need = num(item.get("needPermit"));
        int limit = num(item.get("monthLimit"));
        long cat = lng(item.get("categoryId"));
        boolean approved = need != 1 || approved(username, itemId, cat);
        int bought = limit > 0 ? monthQty(username, itemId) : 0;
        out.put("needPermit", need);
        out.put("monthLimit", limit);
        out.put("bought", bought);
        out.put("remain", limit > 0 ? Math.max(0, limit - bought) : null);
        out.put("approved", approved);
        out.put("message", denyMessage(username, itemId, cat, need, approved));
        out.put("qtyOk", limit <= 0 || bought + Math.max(qty, 1) <= limit);
        return out;
    }

    public static void assertCanBuy(String username, long itemId, int qty) {
        if (!enabled || qty <= 0) return;
        Map<String, Object> item = loadItem(itemId);
        int need = num(item.get("needPermit"));
        long cat = lng(item.get("categoryId"));
        if (need == 1 && !approved(username, itemId, cat)) {
            throw new IllegalArgumentException(denyMessage(username, itemId, cat, need, false));
        }
        int limit = num(item.get("monthLimit"));
        if (limit > 0) {
            int bought = monthQty(username, itemId);
            if (bought + qty > limit) {
                throw new IllegalArgumentException("本月该商品限购 " + limit + " 件，已购 " + bought + " 件");
            }
        }
    }

    public static List<Map<String, Object>> targets() {
        requireOn();
        String item = itemTable();
        return db().query(
                "SELECT id, title, category_id AS categoryId, month_limit AS monthLimit FROM " + item
                        + " WHERE need_permit=1 ORDER BY id",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("title", rs.getString("title"));
                    m.put("categoryId", rs.getLong("categoryId"));
                    m.put("monthLimit", rs.getInt("monthLimit"));
                    return m;
                });
    }

    public static List<Map<String, Object>> mine(String username) {
        requireOn();
        return db().query(
                "SELECT id, username, item_id, category_id, image_url, status, reviewer, reject_reason, created_at, reviewed_at "
                        + "FROM purchase_permit WHERE username=? ORDER BY id DESC",
                (rs, i) -> mapRow(rs),
                username);
    }

    public static List<Map<String, Object>> listAll() {
        requireOn();
        return db().query(
                "SELECT id, username, item_id, category_id, image_url, status, reviewer, reject_reason, created_at, reviewed_at "
                        + "FROM purchase_permit ORDER BY id DESC",
                (rs, i) -> mapRow(rs));
    }

    public static Map<String, Object> submit(String username, Map<String, Object> body) {
        requireOn();
        if (body == null) body = Map.of();
        long itemId = lng(body.get("itemId"));
        long categoryId = lng(body.get("categoryId"));
        String image = str(body.get("imageUrl"));
        if (image.isBlank()) throw new IllegalArgumentException("请上传审核图片");
        if (image.length() > 255) image = image.substring(0, 255);
        if (itemId <= 0 && categoryId <= 0) throw new IllegalArgumentException("请选择商品或分类");
        if (itemId > 0) loadItem(itemId);
        db().update(
                "INSERT INTO purchase_permit (username, item_id, category_id, image_url, status) VALUES (?,?,?,?, 'pending')",
                username,
                itemId > 0 ? itemId : null,
                categoryId > 0 ? categoryId : null,
                image);
        return Map.of("ok", true);
    }

    public static Map<String, Object> review(String reviewer, Map<String, Object> body) {
        requireOn();
        if (body == null) body = Map.of();
        long id = lng(body.get("id"));
        String status = str(body.get("status"));
        if (id <= 0) throw new IllegalArgumentException("缺少审核单");
        if (!"approved".equals(status) && !"rejected".equals(status)) {
            throw new IllegalArgumentException("请选择通过或驳回");
        }
        String reason = str(body.get("rejectReason"));
        if ("rejected".equals(status) && reason.isBlank()) {
            throw new IllegalArgumentException("请填写驳回原因");
        }
        if (reason.length() > 255) reason = reason.substring(0, 255);
        int n = db().update(
                "UPDATE purchase_permit SET status=?, reviewer=?, reject_reason=?, reviewed_at=NOW() WHERE id=?",
                status, reviewer, reason, id);
        if (n <= 0) throw new IllegalArgumentException("审核单不存在");
        return Map.of("ok", true);
    }

    private static void requireOn() {
        if (!enabled) throw new IllegalStateException("购买审核未开启");
    }

    private static Map<String, Object> loadItem(long itemId) {
        String item = itemTable();
        List<Map<String, Object>> rows;
        try {
            rows = db().query(
                    "SELECT id, title, category_id, need_permit, month_limit FROM " + item + " WHERE id=?",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("id", rs.getLong("id"));
                        m.put("title", rs.getString("title"));
                        m.put("categoryId", rs.getLong("category_id"));
                        m.put("needPermit", rs.getInt("need_permit"));
                        m.put("monthLimit", rs.getInt("month_limit"));
                        return m;
                    },
                    itemId);
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置购买审核字段", e);
        }
        if (rows == null || rows.isEmpty()) throw new IllegalArgumentException("商品不存在");
        return rows.get(0);
    }

    private static boolean approved(String username, long itemId, long categoryId) {
        String latest = latestItemStatus(username, itemId);
        if ("approved".equals(latest)) return true;
        if ("pending".equals(latest) || "rejected".equals(latest)) return false;
        if (categoryId <= 0) return false;
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM purchase_permit WHERE username=? AND status='approved' "
                        + "AND category_id=? AND (item_id IS NULL OR item_id=0)",
                Integer.class, username, categoryId);
        return n != null && n > 0;
    }

    private static String latestItemStatus(String username, long itemId) {
        List<String> rows = db().query(
                "SELECT status FROM purchase_permit WHERE username=? AND item_id=? ORDER BY id DESC LIMIT 1",
                (rs, i) -> rs.getString("status"),
                username, itemId);
        return rows == null || rows.isEmpty() ? "" : rows.get(0);
    }

    private static String denyMessage(String username, long itemId, long categoryId, int need, boolean approved) {
        if (need != 1 || approved) return "";
        String latest = latestItemStatus(username, itemId);
        if ("rejected".equals(latest)) return "审核未通过，不能购买";
        if ("pending".equals(latest)) return "审核尚未通过，不能购买";
        if (categoryId > 0) return "请先上传资料并等待审核";
        return "请先上传资料并等待审核";
    }

    private static int monthQty(String username, long itemId) {
        String order = safeIdent(OrderStore.orderTable(), "biz_order");
        String line = safeIdent(OrderStore.lineTable(), "order_line");
        LocalDate start = LocalDate.now().withDayOfMonth(1);
        LocalDate end = start.plusMonths(1);
        Integer n = db().queryForObject(
                "SELECT COALESCE(SUM(l.qty),0) FROM " + line + " l JOIN " + order
                        + " o ON o.id=l.order_id WHERE o.username=? AND l.item_id=? "
                        + "AND o.status<>'cancelled' AND o.created_at>=? AND o.created_at<?",
                Integer.class, username, itemId, start.toString(), end.toString());
        return n == null ? 0 : n;
    }

    private static Map<String, Object> mapRow(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        long itemId = rs.getLong("item_id");
        if (!rs.wasNull() && itemId > 0) m.put("itemId", itemId);
        long cat = rs.getLong("category_id");
        if (!rs.wasNull() && cat > 0) m.put("categoryId", cat);
        m.put("imageUrl", rs.getString("image_url"));
        m.put("status", rs.getString("status"));
        m.put("reviewer", rs.getString("reviewer"));
        m.put("rejectReason", rs.getString("reject_reason"));
        m.put("createdAt", rs.getString("created_at"));
        m.put("reviewedAt", rs.getString("reviewed_at"));
        return m;
    }

    private static String itemTable() {
        String t = ArchiveStore.itemTable();
        return safeIdent(t, "product");
    }

    private static String safeIdent(String raw, String fallback) {
        String t = raw == null ? "" : raw.trim();
        if (!t.matches("[A-Za-z_][A-Za-z0-9_]*")) return fallback;
        return t;
    }

    private static JpaDb db() {
        return JpaSupport.db();
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
}
