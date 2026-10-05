package com.thesis.service;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 报名黑名单：轻名单表，名单内禁止提交报名。≠风控引擎。
 */
public class ApplyBlacklistStore {

    private static boolean enabled;
    private static Boolean tableReady;
    private static String denyMessage = "当前账号暂不可报名，请联系管理员。";

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

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
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
        if (!ready()) throw new IllegalStateException("报名黑名单功能暂不可用");
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
        if (u.isBlank()) throw new IllegalArgumentException("请填写账号");
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
