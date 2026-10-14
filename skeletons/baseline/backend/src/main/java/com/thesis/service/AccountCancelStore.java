package com.thesis.service;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** XA-02：账号注销自助申请。 */
public final class AccountCancelStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static Boolean tableReady;

    private AccountCancelStore() {}

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    private static boolean ready() {
        if (tableReady != null) return tableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='sys_account_cancel'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static String fmt(Timestamp ts) {
        return ts == null ? null : ts.toLocalDateTime().format(FMT);
    }

    private static Map<String, Object> mapRow(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("reason", rs.getString("reason"));
        m.put("status", rs.getString("status"));
        m.put("adminNote", rs.getString("admin_note"));
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        m.put("reviewedAt", fmt(rs.getTimestamp("reviewed_at")));
        return m;
    }

    public static Map<String, Object> submit(String username, String reason) {
        if (!ready()) throw new IllegalStateException("注销申请暂不可用");
        String un = username == null ? "" : username.trim();
        if (un.isBlank()) throw new IllegalArgumentException("未登录");
        Integer pending = db().queryForObject(
                "SELECT COUNT(*) FROM sys_account_cancel WHERE username=? AND status='pending'",
                Integer.class,
                un);
        if (pending != null && pending > 0) {
            throw new IllegalStateException("已有待审的注销申请");
        }
        String r = reason == null ? "" : reason.trim();
        if (r.length() > 255) r = r.substring(0, 255);
        db().update(
                "INSERT INTO sys_account_cancel (username,reason,status) VALUES (?,?,?)",
                un, r, "pending");
        List<Map<String, Object>> rows = db().query(
                "SELECT id,username,reason,status,admin_note,created_at,reviewed_at FROM sys_account_cancel "
                        + "WHERE username=? ORDER BY id DESC LIMIT 1",
                (rs, i) -> mapRow(rs),
                un);
        return rows.isEmpty() ? Map.of() : rows.get(0);
    }

    public static List<Map<String, Object>> list(String status) {
        if (!ready()) return List.of();
        String st = status == null ? "" : status.trim();
        if (st.isBlank() || "all".equalsIgnoreCase(st)) {
            return db().query(
                    "SELECT id,username,reason,status,admin_note,created_at,reviewed_at FROM sys_account_cancel "
                            + "ORDER BY id DESC LIMIT 200",
                    (rs, i) -> mapRow(rs));
        }
        return db().query(
                "SELECT id,username,reason,status,admin_note,created_at,reviewed_at FROM sys_account_cancel "
                        + "WHERE status=? ORDER BY id DESC LIMIT 200",
                (rs, i) -> mapRow(rs),
                st);
    }

    public static Map<String, Object> review(long id, boolean approve, String adminNote) {
        if (!ready()) throw new IllegalStateException("注销申请暂不可用");
        List<Map<String, Object>> rows = db().query(
                "SELECT id,username,reason,status,admin_note,created_at,reviewed_at FROM sys_account_cancel WHERE id=?",
                (rs, i) -> mapRow(rs),
                id);
        if (rows.isEmpty()) throw new IllegalArgumentException("申请不存在");
        Map<String, Object> cur = rows.get(0);
        if (!"pending".equals(String.valueOf(cur.get("status")))) {
            throw new IllegalStateException("该申请已处理");
        }
        String note = adminNote == null ? "" : adminNote.trim();
        if (note.length() > 255) note = note.substring(0, 255);
        String status = approve ? "approved" : "rejected";
        String now = LocalDateTime.now().format(FMT);
        db().update(
                "UPDATE sys_account_cancel SET status=?, admin_note=?, reviewed_at=? WHERE id=?",
                status, note, now, id);
        String username = String.valueOf(cur.get("username"));
        if (approve) {
            UserStore.adminUpdate(username, null, null, false, null, false);
            AuthSessionStore.kickAll(username);
        }
        cur.put("status", status);
        cur.put("adminNote", note);
        cur.put("reviewedAt", now);
        return cur;
    }
}
