package com.thesis.service;

import com.thesis.config.AppPolicy;
import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** 一级佣金：下单人资料里的邀请人账号，按订单金额记一笔。无多级。 */
public final class CommissionStore {

    private static final Pattern INVITER = Pattern.compile("\"inviter\"\\s*:\\s*\"([^\"]+)\"");
    private static Boolean tableReady;

    private CommissionStore() {}

    public static void onOrderPaid(String buyer, long orderId, double totalYuan) {
        if (!AppPolicy.COMMISSION_ENABLED) return;
        if (buyer == null || buyer.isBlank() || totalYuan <= 0) return;
        ensureTable();
        if (!Boolean.TRUE.equals(tableReady)) return;
        String inviter = inviterOf(buyer);
        if (inviter.isBlank() || inviter.equals(buyer)) return;
        double amount = Math.round(totalYuan * 5.0) / 100.0;
        if (amount <= 0) return;
        try {
            JdbcTemplate db = JdbcSupport.jdbc();
            Integer n = db.queryForObject(
                    "SELECT COUNT(*) FROM sys_commission WHERE order_id=? AND inviter=?",
                    Integer.class,
                    orderId,
                    inviter);
            if (n != null && n > 0) return;
            db.update(
                    "INSERT INTO sys_commission (order_id, buyer, inviter, amount_yuan) VALUES (?,?,?,?)",
                    orderId,
                    buyer,
                    inviter,
                    amount);
        } catch (Exception ignored) {
        }
    }

    public static List<Map<String, Object>> list() {
        ensureTable();
        if (!Boolean.TRUE.equals(tableReady)) return List.of();
        return JdbcSupport.jdbc().query(
                "SELECT id, order_id AS orderId, buyer, inviter, amount_yuan AS amountYuan, created_at AS createdAt "
                        + "FROM sys_commission ORDER BY id DESC LIMIT 200",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("orderId", rs.getLong("orderId"));
                    m.put("buyer", rs.getString("buyer"));
                    m.put("inviter", rs.getString("inviter"));
                    m.put("amountYuan", rs.getBigDecimal("amountYuan"));
                    m.put("createdAt", String.valueOf(rs.getTimestamp("createdAt")));
                    return m;
                });
    }

    private static String inviterOf(String buyer) {
        try {
            String raw = JdbcSupport.jdbc().queryForObject(
                    "SELECT profile_json FROM sys_user WHERE username=?",
                    String.class,
                    buyer);
            if (raw == null) return "";
            Matcher m = INVITER.matcher(raw);
            return m.find() ? m.group(1).trim() : "";
        } catch (Exception e) {
            return "";
        }
    }

    private static synchronized void ensureTable() {
        if (Boolean.TRUE.equals(tableReady)) return;
        try {
            JdbcSupport.jdbc().execute(
                    "CREATE TABLE IF NOT EXISTS sys_commission ("
                            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
                            + "order_id BIGINT NOT NULL,"
                            + "buyer VARCHAR(64) NOT NULL,"
                            + "inviter VARCHAR(64) NOT NULL,"
                            + "amount_yuan DECIMAL(10,2) NOT NULL,"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "UNIQUE KEY uk_commission_order (order_id, inviter)"
                            + ")");
            tableReady = true;
        } catch (Exception e) {
            tableReady = false;
        }
    }
}
