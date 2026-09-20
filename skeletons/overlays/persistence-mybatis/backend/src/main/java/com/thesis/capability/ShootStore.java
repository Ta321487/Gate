package com.thesis.capability;

import com.thesis.config.MybatisSupport;
import com.thesis.mapper.ShootMapper;

import java.math.BigDecimal;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 约拍。规则与 jdbc 相同，只换数据访问。 */
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
            db().snap(reservationId, lng(row.get("id")), money(row.get("priceYuan")));
            db().insertFile(reservationId);
        } catch (IllegalArgumentException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置约拍", e);
        }
    }

    public static List<Map<String, Object>> photographers() {
        if (!enabled) return List.of();
        List<Map<String, Object>> rows = db().photographers(itemTable());
        return rows == null ? List.of() : rows;
    }

    public static List<Map<String, Object>> bundles(boolean onlyEnabled) {
        requireOn();
        List<Map<String, Object>> rows = onlyEnabled ? db().enabledBundles() : db().allBundles();
        if (rows == null) return List.of();
        if (!onlyEnabled) {
            for (Map<String, Object> row : rows) row.put("enabled", num(row.get("enabled")) != 0);
        }
        return rows;
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
            if (id > 0) db().updateBundle(id, name, price, detail, on);
            else db().insertBundle(name, price, detail, on);
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置约拍", e);
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("ok", true);
        return out;
    }

    public static List<Map<String, Object>> mine(String username) {
        requireOn();
        List<Map<String, Object>> rows = db().mine(str(username));
        if (rows == null) return List.of();
        for (Map<String, Object> row : rows) hideIfPending(row);
        return rows;
    }

    public static List<Map<String, Object>> files() {
        requireOn();
        List<Map<String, Object>> rows = db().files();
        return rows == null ? List.of() : rows;
    }

    public static Map<String, Object> saveFile(Map<String, Object> body) {
        requireOn();
        long id = lng(body == null ? null : body.get("id"));
        if (id <= 0) throw new IllegalArgumentException("交片不存在");
        int n = db().saveFile(id, str(body == null ? null : body.get("fileUrl")), flag(body.get("delivered")) ? 1 : 0);
        if (n == 0) throw new IllegalArgumentException("交片不存在");
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("ok", true);
        return out;
    }

    private static void hideIfPending(Map<String, Object> row) {
        if (num(row.get("delivered")) != 1) row.put("fileUrl", "");
    }

    private static Map<String, Object> bundle(Map<String, Object> extras) {
        long id = lng(extras == null ? null : extras.get("bundleId"));
        if (id <= 0) return null;
        try {
            List<Map<String, Object>> rows = db().bundle(id);
            return rows == null || rows.isEmpty() ? null : rows.get(0);
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置约拍", e);
        }
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

    private static ShootMapper db() {
        return MybatisSupport.mapper(ShootMapper.class);
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
