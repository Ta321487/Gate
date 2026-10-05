package com.thesis.service;

import com.thesis.config.JpaDb;
import com.thesis.config.JpaSupport;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * ???????????????????????????
 */
public class ApplyBlacklistStore {

    private static boolean enabled;
    private static Boolean tableReady;
    private static String denyMessage = "?????????????????";

    private ApplyBlacklistStore() {}

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
                            + "WHERE table_schema=DATABASE() AND table_name='apply_blacklist'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static void require() {
        if (!ready()) throw new IllegalStateException("???????????");
    }

    private static Map<String, Object> mapRow(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("reason", rs.getString("reason"));
        m.put("status", rs.getString("status"));
        return m;
    }

    public static List<Map<String, Object>> listAll() {
        require();
        return db().query(
                "SELECT * FROM apply_blacklist WHERE status='blocked' ORDER BY id DESC",
                (rs, i) -> mapRow(rs));
    }

    public static void assertNotBlocked(String username) {
        if (!enabled || !ready()) return;
        String u = username == null ? "" : username.trim();
        if (u.isBlank()) return;
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM apply_blacklist WHERE username=? AND status='blocked'",
                Integer.class,
                u);
        if (n != null && n > 0) {
            throw new IllegalStateException(denyMessage);
        }
    }

    public static long add(String username, String reason) {
        require();
        String u = username == null ? "" : username.trim();
        if (u.isBlank()) throw new IllegalArgumentException("?????");
        if (u.length() > 64) u = u.substring(0, 64);
        String r = reason == null ? "" : reason.trim();
        if (r.length() > 255) r = r.substring(0, 255);
        Integer exists = db().queryForObject(
                "SELECT COUNT(*) FROM apply_blacklist WHERE username=?",
                Integer.class,
                u);
        if (exists != null && exists > 0) {
            db().update(
                    "UPDATE apply_blacklist SET reason=?, status='blocked' WHERE username=?",
                    r,
                    u);
            Long id = db().queryForObject(
                    "SELECT id FROM apply_blacklist WHERE username=?",
                    Long.class,
                    u);
            return id == null ? 0L : id;
        }
        db().update(
                "INSERT INTO apply_blacklist (username, reason, status) VALUES (?,?,'blocked')",
                u,
                r);
        Long id = db().queryForObject("SELECT LAST_INSERT_ID()", Long.class);
        return id == null ? 0L : id;
    }

    public static void remove(long id) {
        require();
        if (id <= 0) return;
        db().update("UPDATE apply_blacklist SET status='cleared' WHERE id=?", id);
    }
}
