package com.thesis.capability;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 寄卖。质检通过才上架，订单完成才入账。规则在这里，下单只负责调用。 */
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
            int n = db().update(
                    "UPDATE consign_item SET status='sold' WHERE product_id=? AND status='on_sale'",
                    itemId);
            if (n > 0) {
                db().update("UPDATE " + itemTable() + " SET status='unavailable' WHERE id=?", itemId);
            }
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
            Integer exist = db().queryForObject(
                    "SELECT COUNT(*) FROM consign_ledger WHERE consign_id=? AND order_id=?",
                    Integer.class, consignId, orderId);
            if (exist != null && exist > 0) continue;
            BigDecimal gross = money(line.get("lineYuan"));
            if (gross.signum() <= 0) {
                gross = money(line.get("priceYuan")).multiply(BigDecimal.valueOf(Math.max(1, num(line.get("qty")))));
            }
            BigDecimal rate = money(row.get("feeRate"));
            BigDecimal payout = gross.multiply(BigDecimal.ONE.subtract(rate)).setScale(2, RoundingMode.HALF_UP);
            db().update(
                    "INSERT INTO consign_ledger (consign_id, order_id, username, gross_yuan, fee_rate, payout_yuan, withdraw_status) "
                            + "VALUES (?,?,?,?,?,?,'ready')",
                    consignId, orderId, str(row.get("username")), gross, rate, payout);
        }
    }

    public static void release(long orderId, List<Map<String, Object>> lines) {
        if (!enabled || lines == null) return;
        if (orderId > 0) {
            try {
                db().update(
                        "DELETE FROM consign_ledger WHERE order_id=? AND withdraw_status IN ('ready','applied')",
                        orderId);
            } catch (Exception e) {
                throw new IllegalStateException("系统未配置寄卖", e);
            }
        }
        for (Map<String, Object> line : lines) {
            long itemId = lng(line.get("itemId"));
            if (itemId <= 0) continue;
            int n = db().update(
                    "UPDATE consign_item SET status='on_sale' WHERE product_id=? AND status='sold'",
                    itemId);
            if (n > 0) {
                db().update("UPDATE " + itemTable() + " SET status='available' WHERE id=?", itemId);
            }
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
            int n = db().update("UPDATE consign_item SET fee_rate=? WHERE status='rate'", rate);
            if (n == 0) {
                db().update(
                        "INSERT INTO consign_item (username, title, expect_yuan, condition_note, status, fee_rate) "
                                + "VALUES ('','',0,'','rate',?)",
                        rate);
            }
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
            db().update(
                    "INSERT INTO consign_item (username, title, expect_yuan, condition_note, status, fee_rate) "
                            + "VALUES (?,?,?,?,'pending',?)",
                    uid, t, price, str(condition), money(rate.get("feeRate")));
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
        out.put("items", db().query(
                "SELECT id, title, expect_yuan, condition_note, status, reject_reason, product_id, fee_rate "
                        + "FROM consign_item WHERE username=? AND status<>'rate' ORDER BY id DESC",
                (rs, i) -> itemRow(rs), uid));
        out.put("ledgers", db().query(
                "SELECT id, consign_id, order_id, gross_yuan, fee_rate, payout_yuan, withdraw_status "
                        + "FROM consign_ledger WHERE username=? ORDER BY id DESC",
                (rs, i) -> ledgerRow(rs), uid));
        return out;
    }

    public static List<Map<String, Object>> listAdmin() {
        requireOn();
        return db().query(
                "SELECT id, username, title, expect_yuan, condition_note, status, reject_reason, product_id, fee_rate "
                        + "FROM consign_item WHERE status<>'rate' ORDER BY id DESC",
                (rs, i) -> {
                    Map<String, Object> m = itemRow(rs);
                    m.put("username", rs.getString("username"));
                    return m;
                });
    }

    public static Map<String, Object> pass(long id) {
        requireOn();
        Map<String, Object> row = findById(id);
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
        db().update(
                "UPDATE consign_item SET status='on_sale', product_id=?, reject_reason='' WHERE id=?",
                productId, id);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("productId", productId);
        return out;
    }

    public static Map<String, Object> reject(long id, String reason) {
        requireOn();
        String why = str(reason);
        if (why.isBlank()) throw new IllegalArgumentException("请填写驳回原因");
        int n = db().update(
                "UPDATE consign_item SET status='rejected', reject_reason=? WHERE id=? AND status='pending'",
                why, id);
        if (n == 0) throw new IllegalStateException("只有待质检的可以驳回");
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("ok", true);
        return out;
    }

    public static Map<String, Object> withdraw(String username, long ledgerId) {
        requireOn();
        int n = db().update(
                "UPDATE consign_ledger SET withdraw_status='applied' WHERE id=? AND username=? AND withdraw_status='ready'",
                ledgerId, str(username));
        if (n == 0) throw new IllegalStateException("这笔现在不能申请提现");
        return mine(username);
    }

    public static List<Map<String, Object>> ledgers() {
        requireOn();
        return db().query(
                "SELECT id, consign_id, order_id, username, gross_yuan, fee_rate, payout_yuan, withdraw_status "
                        + "FROM consign_ledger ORDER BY id DESC",
                (rs, i) -> {
                    Map<String, Object> m = ledgerRow(rs);
                    m.put("username", rs.getString("username"));
                    return m;
                });
    }

    public static Map<String, Object> pay(long ledgerId) {
        requireOn();
        int n = db().update(
                "UPDATE consign_ledger SET withdraw_status='paid' WHERE id=? AND withdraw_status='applied'",
                ledgerId);
        if (n == 0) throw new IllegalStateException("只有申请中的可以确认打款");
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("ok", true);
        return out;
    }

    private static Map<String, Object> findByProduct(long itemId) {
        try {
            List<Map<String, Object>> rows = db().query(
                    "SELECT id, username, status, fee_rate FROM consign_item WHERE product_id=? AND status<>'rate'",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("id", rs.getLong("id"));
                        m.put("username", rs.getString("username"));
                        m.put("status", rs.getString("status"));
                        m.put("feeRate", rs.getBigDecimal("fee_rate"));
                        return m;
                    },
                    itemId);
            return rows.isEmpty() ? null : rows.get(0);
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置寄卖", e);
        }
    }

    private static Map<String, Object> findById(long id) {
        List<Map<String, Object>> rows = db().query(
                "SELECT id, username, title, expect_yuan, status FROM consign_item WHERE id=?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("username", rs.getString("username"));
                    m.put("title", rs.getString("title"));
                    m.put("expectYuan", rs.getBigDecimal("expect_yuan"));
                    m.put("status", rs.getString("status"));
                    return m;
                },
                id);
        return rows.isEmpty() ? null : rows.get(0);
    }

    private static Map<String, Object> rateRow() {
        try {
            List<Map<String, Object>> rows = db().query(
                    "SELECT fee_rate FROM consign_item WHERE status='rate' ORDER BY id LIMIT 1",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("feeRate", rs.getBigDecimal("fee_rate"));
                        return m;
                    });
            return rows.isEmpty() ? null : rows.get(0);
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置寄卖", e);
        }
    }

    private static Map<String, Object> rateView(Map<String, Object> row) {
        BigDecimal rate = money(row.get("feeRate"));
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("feeRate", rate);
        m.put("feePercent", percentOf(rate));
        return m;
    }

    private static Map<String, Object> itemRow(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("title", rs.getString("title"));
        m.put("expectYuan", rs.getBigDecimal("expect_yuan"));
        m.put("conditionNote", rs.getString("condition_note"));
        m.put("status", rs.getString("status"));
        m.put("rejectReason", rs.getString("reject_reason"));
        long pid = rs.getLong("product_id");
        m.put("productId", rs.wasNull() ? null : pid);
        m.put("feePercent", percentOf(rs.getBigDecimal("fee_rate")));
        return m;
    }

    private static Map<String, Object> ledgerRow(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("consignId", rs.getLong("consign_id"));
        m.put("orderId", rs.getLong("order_id"));
        m.put("grossYuan", rs.getBigDecimal("gross_yuan"));
        m.put("feePercent", percentOf(rs.getBigDecimal("fee_rate")));
        m.put("payoutYuan", rs.getBigDecimal("payout_yuan"));
        m.put("withdrawStatus", rs.getString("withdraw_status"));
        return m;
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

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
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
