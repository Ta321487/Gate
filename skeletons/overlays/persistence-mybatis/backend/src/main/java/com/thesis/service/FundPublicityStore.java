package com.thesis.service;

import com.thesis.capability.TicketStore;
import com.thesis.config.MybatisSupport;
import com.thesis.config.MbSql;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 资助公示旁路岛：申请通过后登记公示期，用户端可查阅。
 * 挂在单据之后，不扩 ticket 状态机；未建表时 ready()=false，接口给「暂不可用」。
 */
public class FundPublicityStore {

    private static Boolean tableReady;
    /** 公示异议登记窗口（开题扫 FUND）：开关 + 天数（公示结束日 + N 天） */
    private static boolean objectionWindow = false;
    private static int objectionDays = 0;

    private FundPublicityStore() {}

    private static MbSql db() {
        return MybatisSupport.db();
    }

    /** 异议窗口：days<=0 视为未开；写入申请单 objection_due_at。 */
    public static void configureObjection(boolean on, int days) {
        objectionWindow = on;
        objectionDays = Math.max(0, Math.min(60, days));
    }

    public static boolean objectionEnabled() {
        return objectionWindow && objectionDays > 0;
    }

    public static int objectionDays() {
        return objectionDays;
    }

    private static LocalDate parseDay(String raw) {
        String s = raw == null ? "" : raw.trim();
        if (s.isEmpty()) return null;
        if (s.length() > 10) s = s.substring(0, 10);
        try {
            return LocalDate.parse(s);
        } catch (Exception e) {
            return null;
        }
    }

    /** 窗口截止日：公示结束日 + N 天（无结束日退起算日，再无则今天）。 */
    static java.sql.Date windowDue(String startAt, String endAt) {
        if (!objectionEnabled()) return null;
        LocalDate base = parseDay(endAt);
        if (base == null) base = parseDay(startAt);
        if (base == null) base = LocalDate.now();
        return java.sql.Date.valueOf(base.plusDays(objectionDays));
    }

    /** 申请单是否已注入异议扩展列（由 bake 按 ticket.allowObjectionWindow 注入）。 */
    static boolean hasObjectionCols() {
        String t = ticketTable();
        if (t.isEmpty()) return false;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.columns "
                            + "WHERE table_schema=DATABASE() AND table_name=? "
                            + "AND column_name='objection_due_at'",
                    Integer.class,
                    t);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    private static String cellStr(ResultSet rs, String col) {
        try {
            Object v = rs.getObject(col);
            return v == null ? "" : String.valueOf(v);
        } catch (Exception e) {
            return "";
        }
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
        String objection = hasObjectionCols()
                ? "t.objection_due_at AS objection_due_at, t.objection_note AS objection_note, "
                        + "t.objection_at AS objection_at "
                : "NULL AS objection_due_at, '' AS objection_note, NULL AS objection_at ";
        if (t.isEmpty()) {
            return "SELECT p.id, p.ticket_id, '' AS username, p.title, p.start_at, p.end_at, "
                    + "p.status, p.operator, p.created_at, "
                    + "NULL AS objection_due_at, '' AS objection_note, NULL AS objection_at "
                    + "FROM fund_publicity p " + tail;
        }
        return "SELECT p.id, p.ticket_id, IFNULL(t.username,'') AS username, p.title, "
                + "p.start_at, p.end_at, p.status, p.operator, p.created_at, " + objection
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
        m.put("objectionDueAt", cellStr(rs, "objection_due_at"));
        m.put("objectionNote", cellStr(rs, "objection_note"));
        m.put("objectionAt", cellStr(rs, "objection_at"));
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
        // 异议登记窗口：公示结束日 + N 天写回申请单（用户端超期拒收）
        java.sql.Date due = windowDue(startAt, endAt);
        if (due != null && hasObjectionCols()) {
            db().update(
                    "UPDATE `" + t + "` SET objection_due_at=?, objection_note='', objection_at=NULL WHERE id=?",
                    due,
                    ticketId);
        }
        List<Map<String, Object>> out = db().query(
                selectSql("WHERE p.ticket_id=? ORDER BY p.id DESC LIMIT 1"),
                (rs, i) -> mapRow(rs, i),
                ticketId);
        if (out.isEmpty()) throw new IllegalStateException("公示登记后未能读回");
        return out.get(0);
    }

    /** 用户端：对本人公示登记异议（窗口内可写，超期/未开拒绝）。 */
    public static Map<String, Object> submitObjection(long publicityId, String username, String note) {
        require();
        String t = ticketTable();
        if (t.isEmpty()) throw new IllegalStateException("当前系统没有资助申请单");
        if (!objectionEnabled() || !hasObjectionCols()) {
            throw new IllegalStateException("未开通公示异议登记");
        }
        String u = clip(username, 64);
        String text = clip(note, 255);
        if (text.isEmpty()) throw new IllegalArgumentException("请填写异议说明");
        List<Map<String, Object>> rows = db().query(
                "SELECT p.ticket_id, p.status, IFNULL(t.username,'') AS username "
                        + "FROM fund_publicity p LEFT JOIN `" + t + "` t ON t.id=p.ticket_id "
                        + "WHERE p.id=?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("ticketId", rs.getLong("ticket_id"));
                    m.put("status", rs.getString("status"));
                    m.put("username", rs.getString("username"));
                    return m;
                },
                publicityId);
        if (rows.isEmpty()) throw new IllegalArgumentException("公示记录不存在");
        Map<String, Object> row = rows.get(0);
        if (!"publicizing".equals(String.valueOf(row.get("status")))) {
            throw new IllegalStateException("公示已结束，无法登记异议");
        }
        String owner = String.valueOf(row.get("username"));
        if (!u.isEmpty() && !u.equals(owner)) {
            throw new IllegalStateException("只能对本人申请的公示登记异议");
        }
        long ticketId = row.get("ticketId") instanceof Number n ? n.longValue() : 0L;
        String due = dueOf(ticketId);
        LocalDate dueDay = parseDay(due);
        if (dueDay != null && LocalDate.now().isAfter(dueDay)) {
            throw new IllegalStateException("异议登记窗口已于 " + dueDay + " 关闭");
        }
        db().update(
                "UPDATE `" + t + "` SET objection_note=?, objection_at=NOW() WHERE id=?",
                text,
                ticketId);
        try {
            MessageStore.notifyAdmins(
                    "公示异议",
                    UserStore.displayName(u) + " 对「" + titleOf(publicityId) + "」提出异议：" + text,
                    "fund_publicity",
                    publicityId);
        } catch (Exception ignored) {
            // 站内信失败不影响异议落库
        }
        List<Map<String, Object>> out = db().query(
                selectSql("WHERE p.id=? LIMIT 1"), (rs, i) -> mapRow(rs, i), publicityId);
        if (out.isEmpty()) throw new IllegalStateException("异议登记后未能读回");
        return out.get(0);
    }

    private static String dueOf(long ticketId) {
        String t = ticketTable();
        if (t.isEmpty() || ticketId <= 0 || !hasObjectionCols()) return "";
        try {
            List<String> rows = db().query(
                    "SELECT objection_due_at FROM `" + t + "` WHERE id=?",
                    (rs, i) -> {
                        Object v = rs.getObject("objection_due_at");
                        return v == null ? "" : String.valueOf(v);
                    },
                    ticketId);
            return rows.isEmpty() ? "" : rows.get(0);
        } catch (Exception e) {
            return "";
        }
    }

    private static String titleOf(long publicityId) {
        try {
            List<String> rows = db().query(
                    "SELECT title FROM fund_publicity WHERE id=?",
                    (rs, i) -> String.valueOf(rs.getString("title")),
                    publicityId);
            return rows.isEmpty() ? ("公示#" + publicityId) : rows.get(0);
        } catch (Exception e) {
            return "公示#" + publicityId;
        }
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
