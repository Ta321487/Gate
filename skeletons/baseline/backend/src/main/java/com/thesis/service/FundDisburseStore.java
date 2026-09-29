package com.thesis.service;

import com.thesis.capability.TicketStore;
import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 资助发放台账旁路岛：对已通过申请登记发放金额与日期。
 * 与额度台账（balance_ledger）分开：本表只记发放事实，不做额度扣减。
 */
public class FundDisburseStore {

    private static Boolean tableReady;

    private FundDisburseStore() {}

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    public static boolean ready() {
        if (tableReady != null) return tableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='fund_disburse'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static void require() {
        if (!ready()) throw new IllegalStateException("发放登记暂不可用");
    }

    private static String clip(String s, int max) {
        if (s == null) return "";
        String t = s.trim();
        return t.length() <= max ? t : t.substring(0, max);
    }

    private static Object blankToNull(String s) {
        return s == null || s.trim().isEmpty() ? null : s.trim();
    }

    private static String ticketTable() {
        String t = TicketStore.ticketTable();
        return t == null ? "" : t.trim();
    }

    private static String selectSql(String tail) {
        String t = ticketTable();
        if (t.isEmpty()) {
            return "SELECT d.id, d.ticket_id, '' AS username, d.amount, d.paid_at, "
                    + "d.operator, d.remark, d.created_at FROM fund_disburse d " + tail;
        }
        return "SELECT d.id, d.ticket_id, IFNULL(t.username,'') AS username, d.amount, d.paid_at, "
                + "d.operator, d.remark, d.created_at "
                + "FROM fund_disburse d LEFT JOIN `" + t + "` t ON t.id=d.ticket_id " + tail;
    }

    private static Map<String, Object> mapRow(ResultSet rs, int rowNum) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("ticketId", rs.getLong("ticket_id"));
        m.put("username", rs.getString("username"));
        BigDecimal amount = rs.getBigDecimal("amount");
        m.put("amount", amount == null ? "0" : amount.stripTrailingZeros().toPlainString());
        m.put("paidAt", rs.getString("paid_at"));
        m.put("operator", rs.getString("operator"));
        m.put("remark", rs.getString("remark"));
        m.put("createdAt", rs.getString("created_at"));
        return m;
    }

    /** 管理端：发放台账（含学生账号）。 */
    public static List<Map<String, Object>> listAdmin() {
        require();
        return db().query(selectSql("ORDER BY d.id DESC LIMIT 200"), (rs, i) -> mapRow(rs, i));
    }

    /** 登记发放：仅已通过（或已办结）的申请可发放。 */
    public static Map<String, Object> save(
            long ticketId, BigDecimal amount, String paidAt, String operator, String remark) {
        require();
        String t = ticketTable();
        if (t.isEmpty()) throw new IllegalStateException("当前系统没有资助申请单");
        if (ticketId <= 0) throw new IllegalArgumentException("请选择申请单");
        if (amount == null) throw new IllegalArgumentException("请填写发放金额");
        BigDecimal money = amount.setScale(2, RoundingMode.HALF_UP);
        if (money.compareTo(BigDecimal.ZERO) < 0) throw new IllegalArgumentException("发放金额不能为负");
        List<Map<String, Object>> rows = db().query(
                "SELECT status FROM `" + t + "` WHERE id=?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("status", rs.getString("status"));
                    return m;
                },
                ticketId);
        if (rows.isEmpty()) throw new IllegalArgumentException("申请单不存在");
        String st = String.valueOf(rows.get(0).get("status"));
        if ("pending".equals(st)
                || "pending_mid".equals(st)
                || "pending_final".equals(st)
                || "rejected".equals(st)) {
            throw new IllegalStateException("仅审核通过的申请可发放");
        }
        db().update(
                "INSERT INTO fund_disburse (ticket_id, amount, paid_at, operator, remark) "
                        + "VALUES (?,?,?,?,?)",
                ticketId,
                money,
                blankToNull(paidAt),
                clip(operator, 64),
                clip(remark, 255));
        List<Map<String, Object>> out = db().query(
                selectSql("WHERE d.ticket_id=? ORDER BY d.id DESC LIMIT 1"),
                (rs, i) -> mapRow(rs, i),
                ticketId);
        if (out.isEmpty()) throw new IllegalStateException("发放登记后未能读回");
        return out.get(0);
    }

    /** 合计：某申请单已发放总额（答辩口径：台账只记事实）。 */
    public static String totalOf(long ticketId) {
        require();
        BigDecimal sum = db().queryForObject(
                "SELECT IFNULL(SUM(amount),0) FROM fund_disburse WHERE ticket_id=?",
                BigDecimal.class,
                ticketId);
        return sum == null ? "0" : sum.stripTrailingZeros().toPlainString();
    }

    public static void remove(long id) {
        require();
        int n = db().update("DELETE FROM fund_disburse WHERE id=?", id);
        if (n == 0) throw new IllegalArgumentException("发放记录不存在");
    }
}
