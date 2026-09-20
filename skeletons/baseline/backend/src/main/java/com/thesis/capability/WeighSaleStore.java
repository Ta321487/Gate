package com.thesis.capability;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 按重量计价、损耗赔付。次日达仍走配送时段。 */
public final class WeighSaleStore {

    private static boolean enabled;

    private WeighSaleStore() {}

    public static void configure(boolean on) {
        enabled = on;
    }

    public static boolean enabled() {
        return enabled;
    }

    /** 按重量时行金额 = 单价 × 重量，件数改为 1。其他商品仍按件数。 */
    public static Map<String, Object> priceLine(Map<String, Object> item, int qty, Map<String, Object> extra) {
        BigDecimal unit = money(item == null ? null : ArchiveStore.effectiveUnitPrice(item));
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("unit", unit);
        out.put("qty", qty);
        out.put("weight", null);
        out.put("lineYuan", unit.multiply(BigDecimal.valueOf(Math.max(qty, 0))).setScale(2, RoundingMode.HALF_UP));
        if (!enabled || item == null || num(item.get("sellByWeight")) != 1) return out;
        BigDecimal weight = money(extra == null ? null : first(extra, "weightQty", "weight_qty"));
        if (weight.signum() <= 0) throw new IllegalArgumentException("请填写重量");
        out.put("qty", 1);
        out.put("weight", weight);
        out.put("lineYuan", unit.multiply(weight).setScale(2, RoundingMode.HALF_UP));
        return out;
    }

    public static void saveWeight(long orderId, long itemId, Object weight) {
        if (!enabled || weight == null || orderId <= 0 || itemId <= 0) return;
        String line = lineTable();
        try {
            db().update(
                    "UPDATE " + line + " SET weight_qty=? WHERE order_id=? AND item_id=?",
                    money(weight), orderId, itemId);
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置重量字段，无法保存", e);
        }
    }

    public static Map<String, Object> policy() {
        requireOn();
        Map<String, Object> row = policyRow();
        if (row == null) throw new IllegalStateException("系统未配置损耗赔付");
        return row;
    }

    public static Map<String, Object> savePolicy(boolean on, Object cap) {
        requireOn();
        BigDecimal yuan = money(cap);
        if (yuan.signum() < 0) throw new IllegalArgumentException("上限不能小于 0");
        try {
            int n = db().update("UPDATE loss_policy SET enabled=?, cap_yuan=? WHERE id=1", on ? 1 : 0, yuan);
            if (n == 0) {
                db().update("INSERT INTO loss_policy (id, enabled, cap_yuan) VALUES (1,?,?)", on ? 1 : 0, yuan);
            }
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置损耗赔付", e);
        }
        return policy();
    }

    public static Map<String, Object> submit(String username, long orderId, Object amount, String reason) {
        requireOn();
        String uid = str(username);
        if (uid.isBlank()) throw new IllegalArgumentException("未登录");
        Map<String, Object> pol = policyRow();
        if (pol == null || num(pol.get("enabled")) != 1) {
            throw new IllegalStateException("暂时不能申请损耗赔付");
        }
        String why = str(reason);
        if (why.isBlank()) throw new IllegalArgumentException("请填写原因");
        BigDecimal ask = money(amount);
        if (ask.signum() <= 0) throw new IllegalArgumentException("请填写金额");
        assertOwnOrder(uid, orderId);
        try {
            Integer open = db().queryForObject(
                    "SELECT COUNT(*) FROM loss_claim WHERE order_id=? AND status='pending'",
                    Integer.class, orderId);
            if (open != null && open > 0) throw new IllegalStateException("这笔订单已有待处理的申请");
            db().update(
                    "INSERT INTO loss_claim (username, order_id, amount_yuan, reason, status) VALUES (?,?,?,?,'pending')",
                    uid, orderId, ask, why);
        } catch (IllegalStateException | IllegalArgumentException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置损耗赔付", e);
        }
        return mine(uid);
    }

    public static Map<String, Object> mine(String username) {
        requireOn();
        Map<String, Object> pol = policyRow();
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("enabled", pol != null && num(pol.get("enabled")) == 1);
        out.put("capYuan", pol == null ? BigDecimal.ZERO : money(pol.get("capYuan")));
        out.put("claims", db().query(
                "SELECT id, order_id, amount_yuan, reason, status, paid_yuan FROM loss_claim WHERE username=? ORDER BY id DESC",
                (rs, i) -> claim(rs, false), str(username)));
        return out;
    }

    public static List<Map<String, Object>> listAdmin() {
        requireOn();
        return db().query(
                "SELECT id, username, order_id, amount_yuan, reason, status, paid_yuan FROM loss_claim ORDER BY id DESC",
                (rs, i) -> claim(rs, true));
    }

    public static Map<String, Object> approve(long id) {
        requireOn();
        Map<String, Object> row = findClaim(id);
        if (row == null || !"pending".equals(str(row.get("status")))) {
            throw new IllegalStateException("只有待处理的申请可以通过");
        }
        Map<String, Object> pol = policyRow();
        if (pol == null) throw new IllegalStateException("系统未配置损耗赔付");
        BigDecimal cap = money(pol.get("capYuan"));
        BigDecimal ask = money(row.get("amountYuan"));
        BigDecimal paid = ask.min(cap).setScale(2, RoundingMode.HALF_UP);
        credit(str(row.get("username")), paid);
        db().update("UPDATE loss_claim SET status='approved', paid_yuan=? WHERE id=?", paid, id);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("paidYuan", paid);
        return out;
    }

    public static Map<String, Object> reject(long id, String reason) {
        requireOn();
        String why = str(reason);
        if (why.isBlank()) throw new IllegalArgumentException("请填写驳回原因");
        int n = db().update(
                "UPDATE loss_claim SET status='rejected', reason=? WHERE id=? AND status='pending'",
                why, id);
        if (n == 0) throw new IllegalStateException("只有待处理的申请可以驳回");
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("ok", true);
        return out;
    }

    private static void credit(String username, BigDecimal yuan) {
        if (yuan.signum() <= 0) return;
        try {
            int n = db().update(
                    "UPDATE sys_user SET balance_yuan=IFNULL(balance_yuan,0)+? WHERE username=?",
                    yuan, username);
            if (n == 0) throw new IllegalStateException("系统未配置余额");
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置余额", e);
        }
    }

    private static void assertOwnOrder(String username, long orderId) {
        if (orderId <= 0) throw new IllegalArgumentException("请选择订单");
        String table = orderTable();
        List<Map<String, Object>> rows;
        try {
            rows = db().query(
                    "SELECT username, status FROM " + table + " WHERE id=?",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("username", rs.getString("username"));
                        m.put("status", rs.getString("status"));
                        return m;
                    },
                    orderId);
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置损耗赔付", e);
        }
        if (rows.isEmpty()) throw new IllegalArgumentException("订单不存在");
        Map<String, Object> row = rows.get(0);
        if (!username.equals(str(row.get("username")))) throw new IllegalArgumentException("只能申请自己的订单");
        String st = str(row.get("status"));
        if ("cancelled".equals(st) || "pending".equals(st)) {
            throw new IllegalStateException("这单还不能申请损耗赔付");
        }
    }

    private static Map<String, Object> policyRow() {
        try {
            List<Map<String, Object>> rows = db().query(
                    "SELECT enabled, cap_yuan FROM loss_policy WHERE id=1",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("enabled", rs.getInt("enabled"));
                        m.put("capYuan", rs.getBigDecimal("cap_yuan"));
                        return m;
                    });
            return rows.isEmpty() ? null : rows.get(0);
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置损耗赔付", e);
        }
    }

    private static Map<String, Object> findClaim(long id) {
        List<Map<String, Object>> rows = db().query(
                "SELECT id, username, amount_yuan, status FROM loss_claim WHERE id=?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("username", rs.getString("username"));
                    m.put("amountYuan", rs.getBigDecimal("amount_yuan"));
                    m.put("status", rs.getString("status"));
                    return m;
                },
                id);
        return rows.isEmpty() ? null : rows.get(0);
    }

    private static Map<String, Object> claim(java.sql.ResultSet rs, boolean withUser) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        if (withUser) m.put("username", rs.getString("username"));
        m.put("orderId", rs.getLong("order_id"));
        m.put("amountYuan", rs.getBigDecimal("amount_yuan"));
        m.put("reason", rs.getString("reason"));
        m.put("status", rs.getString("status"));
        m.put("paidYuan", rs.getBigDecimal("paid_yuan"));
        return m;
    }

    private static String lineTable() {
        String t = OrderStore.lineTable();
        if (t == null || !t.matches("[A-Za-z_][A-Za-z0-9_]*")) {
            throw new IllegalStateException("系统未配置重量字段，无法保存");
        }
        return t;
    }

    private static String orderTable() {
        String t = OrderStore.orderTable();
        if (t == null || !t.matches("[A-Za-z_][A-Za-z0-9_]*")) t = "biz_order";
        return t;
    }

    private static void requireOn() {
        if (!enabled) throw new IllegalStateException("按重量未开启");
    }

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    private static Object first(Map<String, Object> extra, String... keys) {
        for (String key : keys) {
            if (extra.containsKey(key) && extra.get(key) != null) return extra.get(key);
        }
        return null;
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static int num(Object o) {
        if (o instanceof Number n) return n.intValue();
        if (o instanceof Boolean b) return b ? 1 : 0;
        return 0;
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
