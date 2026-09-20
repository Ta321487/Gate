package com.thesis.capability;

import com.thesis.config.MybatisSupport;
import com.thesis.mapper.PurchaseGateMapper;

import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 购买审核与每月限购。规则与 jdbc 相同，只换数据访问。
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
        int need = num(item.get("needPermit"));
        int limit = num(item.get("monthLimit"));
        long cat = lng(item.get("categoryId"));
        boolean ok = need != 1 || approved(username, itemId, cat);
        int bought = limit > 0 ? monthQty(username, itemId) : 0;
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("needPermit", need);
        out.put("monthLimit", limit);
        out.put("bought", bought);
        out.put("remain", limit > 0 ? Math.max(0, limit - bought) : null);
        out.put("approved", ok);
        out.put("message", denyMessage(username, itemId, need, ok));
        out.put("qtyOk", limit <= 0 || bought + Math.max(qty, 1) <= limit);
        return out;
    }

    public static void assertCanBuy(String username, long itemId, int qty) {
        if (!enabled || qty <= 0) return;
        Map<String, Object> item = loadItem(itemId);
        int need = num(item.get("needPermit"));
        long cat = lng(item.get("categoryId"));
        if (need == 1 && !approved(username, itemId, cat)) {
            throw new IllegalArgumentException(denyMessage(username, itemId, need, false));
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
        return db().targets(itemTable());
    }

    public static List<Map<String, Object>> mine(String username) {
        requireOn();
        return db().mine(username);
    }

    public static List<Map<String, Object>> listAll() {
        requireOn();
        return db().listAll();
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
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("username", username);
        row.put("itemId", itemId > 0 ? itemId : null);
        row.put("categoryId", categoryId > 0 ? categoryId : null);
        row.put("imageUrl", image);
        db().insert(row);
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
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", id);
        row.put("status", status);
        row.put("reviewer", reviewer);
        row.put("rejectReason", reason);
        if (db().review(row) <= 0) throw new IllegalArgumentException("审核单不存在");
        return Map.of("ok", true);
    }

    private static void requireOn() {
        if (!enabled) throw new IllegalStateException("购买审核未开启");
    }

    private static Map<String, Object> loadItem(long itemId) {
        Map<String, Object> row;
        try {
            row = db().gate(itemTable(), itemId);
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置购买审核字段", e);
        }
        if (row == null || row.isEmpty()) throw new IllegalArgumentException("商品不存在");
        return row;
    }

    private static boolean approved(String username, long itemId, long categoryId) {
        String latest = db().latestStatus(username, itemId);
        if ("approved".equals(latest)) return true;
        if ("pending".equals(latest) || "rejected".equals(latest)) return false;
        if (categoryId <= 0) return false;
        Integer n = db().categoryApproved(username, categoryId);
        return n != null && n > 0;
    }

    private static String denyMessage(String username, long itemId, int need, boolean approved) {
        if (need != 1 || approved) return "";
        String latest = db().latestStatus(username, itemId);
        if ("rejected".equals(latest)) return "审核未通过，不能购买";
        if ("pending".equals(latest)) return "审核尚未通过，不能购买";
        return "请先上传资料并等待审核";
    }

    private static int monthQty(String username, long itemId) {
        LocalDate start = LocalDate.now().withDayOfMonth(1);
        Integer n = db().monthQty(
                safeIdent(OrderStore.orderTable(), "biz_order"),
                safeIdent(OrderStore.lineTable(), "order_line"),
                username,
                itemId,
                start.toString(),
                start.plusMonths(1).toString());
        return n == null ? 0 : n;
    }

    private static PurchaseGateMapper db() {
        return MybatisSupport.mapper(PurchaseGateMapper.class);
    }

    private static String itemTable() {
        return safeIdent(ArchiveStore.itemTable(), "product");
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
}
