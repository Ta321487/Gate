package com.thesis.capability;

import com.thesis.config.MybatisSupport;
import com.thesis.mapper.ConsignMapper;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 寄卖。规则与 jdbc 相同，只换数据访问。 */
public final class ConsignStore {

    private static boolean enabled;

    private ConsignStore() {}

    public static void configure(boolean on) {
        enabled = on;
    }

    public static boolean enabled() {
        return enabled;
    }

    public static void assertOnSale(long itemId) {
        if (!enabled || itemId <= 0) return;
        Map<String, Object> row = findByProduct(itemId);
        if (row == null) return;
        if (!"on_sale".equals(str(row.get("status")))) {
            throw new IllegalArgumentException("这件还没通过质检，不能购买");
        }
    }

    public static void markSold(long itemId) {
        if (!enabled || itemId <= 0) return;
        try {
            int n = db().markSold(itemId);
            if (n > 0) db().setItemStatus(itemTable(), itemId, "unavailable");
        } catch (IllegalArgumentException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置寄卖", e);
        }
    }

    public static void settle(long orderId, List<Map<String, Object>> lines) {
        if (!enabled || orderId <= 0 || lines == null) return;
        for (Map<String, Object> line : lines) {
            long itemId = lng(line.get("itemId"));
            Map<String, Object> row = findByProduct(itemId);
            if (row == null) continue;
            String st = str(row.get("status"));
            if (!"sold".equals(st) && !"on_sale".equals(st)) continue;
            long consignId = lng(row.get("id"));
            Integer exist = db().countLedger(consignId, orderId);
            if (exist != null && exist > 0) continue;
            BigDecimal gross = money(line.get("lineYuan"));
            if (gross.signum() <= 0) {
                gross = money(line.get("priceYuan")).multiply(BigDecimal.valueOf(Math.max(1, num(line.get("qty")))));
            }
            BigDecimal rate = money(row.get("feeRate"));
            BigDecimal payout = gross.multiply(BigDecimal.ONE.subtract(rate)).setScale(2, RoundingMode.HALF_UP);
            db().insertLedger(consignId, orderId, str(row.get("username")), gross, rate, payout);
        }
    }

    public static void release(long orderId, List<Map<String, Object>> lines) {
        if (!enabled || lines == null) return;
        if (orderId > 0) {
            try {
                db().deleteUnpaid(orderId);
            } catch (Exception e) {
                throw new IllegalStateException("系统未配置寄卖", e);
            }
        }
        for (Map<String, Object> line : lines) {
            long itemId = lng(line.get("itemId"));
            if (itemId <= 0) continue;
            int n = db().restore(itemId);
            if (n > 0) db().setItemStatus(itemTable(), itemId, "available");
        }
    }

    public static Map<String, Object> rate() {
        requireOn();
        Map<String, Object> row = rateRow();
        if (row == null) throw new IllegalStateException("系统未配置寄卖");
        return rateView(row);
    }

    public static Map<String, Object> saveRate(int percent) {
        requireOn();
        if (percent < 0 || percent > 100) throw new IllegalArgumentException("抽成请填 0 到 100");
        BigDecimal rate = BigDecimal.valueOf(percent).movePointLeft(2);
        try {
            int n = db().updateRate(rate);
            if (n == 0) db().insertRate(rate);
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置寄卖", e);
        }
        return rate();
    }

    public static Map<String, Object> submit(String username, String title, Object expect, String condition) {
        requireOn();
        String uid = str(username);
        if (uid.isBlank()) throw new IllegalArgumentException("未登录");
        String t = str(title);
        if (t.isBlank()) throw new IllegalArgumentException("请填写标题");
        BigDecimal price = money(expect);
        if (price.signum() <= 0) throw new IllegalArgumentException("请填写期望价");
        Map<String, Object> rate = rateRow();
        if (rate == null) throw new IllegalStateException("系统未配置寄卖");
        try {
            db().insertItem(uid, t, price, str(condition), money(rate.get("feeRate")));
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置寄卖", e);
        }
        return mine(uid);
    }

    public static Map<String, Object> mine(String username) {
        requireOn();
        String uid = str(username);
        Map<String, Object> out = new LinkedHashMap<>();
        Map<String, Object> rate = rateRow();
        out.put("feePercent", rate == null ? 0 : percentOf(money(rate.get("feeRate"))));
        out.put("items", withPercent(db().mineItems(uid)));
        out.put("ledgers", withPercent(db().mineLedgers(uid)));
        return out;
    }

    public static List<Map<String, Object>> listAdmin() {
        requireOn();
        return withPercent(db().adminItems());
    }

    public static Map<String, Object> pass(long id) {
        requireOn();
        Map<String, Object> row = first(db().findById(id));
        if (row == null || "rate".equals(str(row.get("status")))) {
            throw new IllegalArgumentException("寄卖不存在");
        }
        if (!"pending".equals(str(row.get("status")))) {
            throw new IllegalStateException("只有待质检的可以上架");
        }
        BigDecimal price = money(row.get("expectYuan"));
        Map<String, Object> created = ArchiveStore.addItem(
                str(row.get("title")),
                price.setScale(2, RoundingMode.HALF_UP).toPlainString(),
                "CS-" + id,
                1L,
                1,
                "");
        if (created == null || lng(created.get("id")) <= 0) {
            throw new IllegalStateException("上架失败");
        }
        long productId = lng(created.get("id"));
        db().pass(id, productId);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("productId", productId);
        return out;
    }

    public static Map<String, Object> reject(long id, String reason) {
        requireOn();
        String why = str(reason);
        if (why.isBlank()) throw new IllegalArgumentException("请填写驳回原因");
        int n = db().reject(id, why);
        if (n == 0) throw new IllegalStateException("只有待质检的可以驳回");
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("ok", true);
        return out;
    }

    public static Map<String, Object> withdraw(String username, long ledgerId) {
        requireOn();
        int n = db().withdraw(ledgerId, str(username));
        if (n == 0) throw new IllegalStateException("这笔现在不能申请提现");
        return mine(username);
    }

    public static List<Map<String, Object>> ledgers() {
        requireOn();
        return withPercent(db().ledgers());
    }

    public static Map<String, Object> pay(long ledgerId) {
        requireOn();
        int n = db().pay(ledgerId);
        if (n == 0) throw new IllegalStateException("只有申请中的可以确认打款");
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("ok", true);
        return out;
    }

    private static Map<String, Object> findByProduct(long itemId) {
        try {
            return first(db().findByProduct(itemId));
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置寄卖", e);
        }
    }

    private static Map<String, Object> rateRow() {
        try {
            return first(db().rate());
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置寄卖", e);
        }
    }

    private static List<Map<String, Object>> withPercent(List<Map<String, Object>> rows) {
        if (rows == null) return List.of();
        for (Map<String, Object> row : rows) {
            if (row.containsKey("feeRate")) {
                row.put("feePercent", percentOf(money(row.get("feeRate"))));
            }
        }
        return rows;
    }

    private static Map<String, Object> rateView(Map<String, Object> row) {
        BigDecimal rate = money(row.get("feeRate"));
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("feeRate", rate);
        m.put("feePercent", percentOf(rate));
        return m;
    }

    private static Map<String, Object> first(List<Map<String, Object>> rows) {
        return rows == null || rows.isEmpty() ? null : rows.get(0);
    }

    private static int percentOf(BigDecimal rate) {
        return rate.movePointRight(2).setScale(0, RoundingMode.HALF_UP).intValue();
    }

    private static String itemTable() {
        String t = ArchiveStore.itemTable();
        if (t == null || !t.matches("[A-Za-z_][A-Za-z0-9_]*")) {
            throw new IllegalStateException("系统未配置寄卖");
        }
        return t;
    }

    private static void requireOn() {
        if (!enabled) throw new IllegalStateException("寄卖未开启");
    }

    private static ConsignMapper db() {
        return MybatisSupport.mapper(ConsignMapper.class);
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static int num(Object o) {
        if (o instanceof Number n) return n.intValue();
        return 0;
    }

    private static long lng(Object o) {
        if (o instanceof Number n) return n.longValue();
        if (o == null || String.valueOf(o).isBlank()) return 0L;
        try {
            return Long.parseLong(String.valueOf(o).trim());
        } catch (NumberFormatException e) {
            return 0L;
        }
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
