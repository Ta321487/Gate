package com.thesis.service;

import com.thesis.config.JpaDb;
import com.thesis.config.JpaSupport;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 预约黑名单：轻名单表 + 申诉。≠风控引擎。
 */
public class ReserveBlacklistStore {

    private static boolean enabled;
    private static Boolean tableReady;
    private static String denyMessage = "当前账号暂不可预约，可提交申诉或联系管理员。";

    private ReserveBlacklistStore() {}

    public static void configure(boolean on, String denyMsg) {
        enabled = on;
        tableReady = null;
        if (denyMsg != null && !denyMsg.isBlank()) {
            denyMessage = denyMsg.trim();
        }
    }

    public static boolean enabled() {
        return enabled;
    }

    private static JpaDb db() {
        return JpaSupport.db();
    }

    public static boolean ready() {
        if (!enabled) return false;
        if (tableReady != null) return tableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='reserve_blacklist'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static void require() {
        if (!ready()) throw new IllegalStateException("预约黑名单功能暂不可用");
    }

    private static Map<String, Object> mapRow(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("reason", rs.getString("reason"));
        m.put("status", rs.getString("status"));
        return m;
    }

    private static Map<String, Object> mapAppeal(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("reason", rs.getString("reason"));
        m.put("status", rs.getString("status"));
        try {
            m.put("createdAt", rs.getTimestamp("created_at") == null
                    ? null
                    : rs.getTimestamp("created_at").toString());
        } catch (Exception e) {
            m.put("createdAt", null);
        }
        return m;
    }

    public static List<Map<String, Object>> listAll() {
        require();
        return db().query(
                "SELECT * FROM reserve_blacklist WHERE status='blocked' ORDER BY id DESC",
                (rs, i) -> mapRow(rs));
    }

    public static void assertNotBlocked(String username) {
        if (!enabled || !ready()) return;
        String u = username == null ? "" : username.trim();
        if (u.isBlank()) return;
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM reserve_blacklist WHERE username=? AND status='blocked'",
                Integer.class,
                u);
        if (n != null && n > 0) {
            throw new IllegalStateException(denyMessage);
        }
    }

    public static long add(String username, String reason) {
        require();
        String u = username == null ? "" : username.trim();
        if (u.isBlank()) throw new IllegalArgumentException("请填写账号");
        if (u.length() > 64) u = u.substring(0, 64);
        String r = reason == null ? "" : reason.trim();
        if (r.length() > 255) r = r.substring(0, 255);
        Integer exists = db().queryForObject(
                "SELECT COUNT(*) FROM reserve_blacklist WHERE username=?",
                Integer.class,
                u);
        if (exists != null && exists > 0) {
            db().update(
                    "UPDATE reserve_blacklist SET reason=?, status='blocked' WHERE username=?",
                    r,
                    u);
            Long id = db().queryForObject(
                    "SELECT id FROM reserve_blacklist WHERE username=?",
                    Long.class,
                    u);
            return id == null ? 0L : id;
        }
        db().update(
                "INSERT INTO reserve_blacklist (username, reason, status) VALUES (?,?,'blocked')",
                u,
                r);
        Long id = db().queryForObject("SELECT LAST_INSERT_ID()", Long.class);
        return id == null ? 0L : id;
    }

    public static void remove(long id) {
        require();
        if (id <= 0) return;
        db().update("UPDATE reserve_blacklist SET status='cleared' WHERE id=?", id);
    }

    public static long submitAppeal(String username, String reason) {
        require();
        String u = username == null ? "" : username.trim();
        if (u.isBlank()) throw new IllegalArgumentException("请先登录");
        String r = reason == null ? "" : reason.trim();
        if (r.isBlank()) throw new IllegalArgumentException("请填写申诉说明");
        if (r.length() > 255) r = r.substring(0, 255);
        db().update(
                "INSERT INTO reserve_blacklist_appeal (username, reason, status) VALUES (?,?,'pending')",
                u,
                r);
        Long id = db().queryForObject("SELECT LAST_INSERT_ID()", Long.class);
        return id == null ? 0L : id;
    }

    public static List<Map<String, Object>> listAppeals(String username) {
        require();
        if (username != null && !username.isBlank()) {
            return db().query(
                    "SELECT * FROM reserve_blacklist_appeal WHERE username=? ORDER BY id DESC",
                    (rs, i) -> mapAppeal(rs),
                    username.trim());
        }
        return db().query(
                "SELECT * FROM reserve_blacklist_appeal ORDER BY id DESC LIMIT 200",
                (rs, i) -> mapAppeal(rs));
    }

    public static void resolveAppeal(long appealId, boolean approve) {
        require();
        if (appealId <= 0) return;
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM reserve_blacklist_appeal WHERE id=?",
                (rs, i) -> mapAppeal(rs),
                appealId);
        if (rows.isEmpty()) throw new IllegalArgumentException("申诉不存在");
        Map<String, Object> a = rows.get(0);
        String st = String.valueOf(a.get("status"));
        if (!"pending".equals(st)) return;
        String next = approve ? "approved" : "rejected";
        db().update("UPDATE reserve_blacklist_appeal SET status=? WHERE id=?", next, appealId);
        if (approve) {
            String u = String.valueOf(a.get("username"));
            db().update(
                    "UPDATE reserve_blacklist SET status='cleared' WHERE username=? AND status='blocked'",
                    u);
        }
    }
}
