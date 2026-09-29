package com.thesis.service;

import com.thesis.capability.TicketStore;
import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 资助公示旁路岛：申请通过后登记公示期，用户端可查阅。
 * 挂在单据之后，不扩 ticket 状态机；未建表时 ready()=false，接口给「暂不可用」。
 */
public class FundPublicityStore {

    private static Boolean tableReady;

    private FundPublicityStore() {}

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    public static boolean ready() {
        if (tableReady != null) return tableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='fund_publicity'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static void require() {
        if (!ready()) throw new IllegalStateException("公示登记暂不可用");
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
            return "SELECT p.id, p.ticket_id, '' AS username, p.title, p.start_at, p.end_at, "
                    + "p.status, p.operator, p.created_at FROM fund_publicity p " + tail;
        }
        return "SELECT p.id, p.ticket_id, IFNULL(t.username,'') AS username, p.title, "
                + "p.start_at, p.end_at, p.status, p.operator, p.created_at "
                + "FROM fund_publicity p LEFT JOIN `" + t + "` t ON t.id=p.ticket_id " + tail;
    }

    private static Map<String, Object> mapRow(ResultSet rs, int rowNum) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("ticketId", rs.getLong("ticket_id"));
        m.put("username", rs.getString("username"));
        m.put("title", rs.getString("title"));
        m.put("startAt", rs.getString("start_at"));
        m.put("endAt", rs.getString("end_at"));
        m.put("status", rs.getString("status"));
        m.put("operator", rs.getString("operator"));
        m.put("createdAt", rs.getString("created_at"));
        return m;
    }

    /** 管理端：全部公示记录（含学生账号）。 */
    public static List<Map<String, Object>> listAdmin() {
        require();
        return db().query(selectSql("ORDER BY p.id DESC LIMIT 200"), (rs, i) -> mapRow(rs, i));
    }

    /** 用户端：本人申请的公示（按单据归属人过滤）。 */
    public static List<Map<String, Object>> listMine(String username) {
        require();
        String u = clip(username, 64);
        if (u.isEmpty() || ticketTable().isEmpty()) return List.of();
        return db().query(
                selectSql("WHERE t.username=? ORDER BY p.id DESC LIMIT 200"), (rs, i) -> mapRow(rs, i), u);
    }

    /** 登记公示：仅已通过（或已办结）的申请可公示。 */
    public static Map<String, Object> save(
            long ticketId, String title, String startAt, String endAt, String operator) {
        require();
        String t = ticketTable();
        if (t.isEmpty()) throw new IllegalStateException("当前系统没有资助申请单");
        if (ticketId <= 0) throw new IllegalArgumentException("请选择申请单");
        String label = clip(title, 128);
        if (label.isEmpty()) throw new IllegalArgumentException("请填写公示标题");
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
            throw new IllegalStateException("仅审核通过的申请可公示");
        }
        db().update(
                "INSERT INTO fund_publicity (ticket_id, title, start_at, end_at, status, operator) "
                        + "VALUES (?,?,?,?,?,?)",
                ticketId,
                label,
                blankToNull(startAt),
                blankToNull(endAt),
                "publicizing",
                clip(operator, 64));
        List<Map<String, Object>> out = db().query(
                selectSql("WHERE p.ticket_id=? ORDER BY p.id DESC LIMIT 1"),
                (rs, i) -> mapRow(rs, i),
                ticketId);
        if (out.isEmpty()) throw new IllegalStateException("公示登记后未能读回");
        return out.get(0);
    }

    /** 结束公示（公示期已满）。 */
    public static void close(long id, String operator) {
        require();
        int n = db().update(
                "UPDATE fund_publicity SET status='closed', operator=? WHERE id=?",
                clip(operator, 64),
                id);
        if (n == 0) throw new IllegalArgumentException("公示记录不存在");
    }

    public static void remove(long id) {
        require();
        int n = db().update("DELETE FROM fund_publicity WHERE id=?", id);
        if (n == 0) throw new IllegalArgumentException("公示记录不存在");
    }
}
