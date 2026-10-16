package com.thesis.service;

import com.thesis.config.AppPolicy;
import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 在线会话登记；管理端可踢下线、多端互踢。 */
public final class AuthSessionStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static Boolean tableReady;

    private AuthSessionStore() {}

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    private static boolean ready() {
        if (tableReady != null) return tableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='sys_auth_session'",
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

    private static String nz(String s, int max) {
        if (s == null) return "";
        String t = s.trim();
        if (t.length() > max) t = t.substring(0, max);
        return t;
    }

    public static void register(String sessionId, String username, String ip, String userAgent) {
        if (!ready() || sessionId == null || sessionId.isBlank() || username == null || username.isBlank()) {
            return;
        }
        String sid = sessionId.trim();
        String un = username.trim();
        String now = LocalDateTime.now().format(FMT);
        db().update(
                "INSERT INTO sys_auth_session (session_id,username,ip,user_agent,created_at,last_seen_at,kicked) "
                        + "VALUES (?,?,?,?,?,?,0) "
                        + "ON DUPLICATE KEY UPDATE username=VALUES(username), ip=VALUES(ip), "
                        + "user_agent=VALUES(user_agent), last_seen_at=VALUES(last_seen_at), kicked=0",
                sid, un, nz(ip, 64), nz(userAgent, 255), now, now);
        trimToMax(un);
    }

    public static void touch(String sessionId) {
        if (!ready() || sessionId == null || sessionId.isBlank()) return;
        try {
            db().update(
                    "UPDATE sys_auth_session SET last_seen_at=? WHERE session_id=? AND kicked=0",
                    LocalDateTime.now().format(FMT),
                    sessionId.trim());
        } catch (Exception ignored) {
        }
    }

    public static boolean isAlive(String sessionId) {
        if (!ready() || sessionId == null || sessionId.isBlank()) return true;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM sys_auth_session WHERE session_id=? AND kicked=0",
                    Integer.class,
                    sessionId.trim());
            // 无登记行（旧会话）视为存活，避免升级后全员被踢
            if (n == null || n == 0) {
                Integer any = db().queryForObject(
                        "SELECT COUNT(*) FROM sys_auth_session WHERE session_id=?",
                        Integer.class,
                        sessionId.trim());
                return any == null || any == 0;
            }
            return true;
        } catch (Exception e) {
            return true;
        }
    }

    public static void kick(String sessionId) {
        if (!ready() || sessionId == null || sessionId.isBlank()) return;
        db().update("UPDATE sys_auth_session SET kicked=1 WHERE session_id=?", sessionId.trim());
    }

    public static void kickAll(String username) {
        if (!ready() || username == null || username.isBlank()) return;
        db().update("UPDATE sys_auth_session SET kicked=1 WHERE username=? AND kicked=0", username.trim());
    }

    public static void invalidate(String sessionId) {
        if (!ready() || sessionId == null || sessionId.isBlank()) return;
        db().update("DELETE FROM sys_auth_session WHERE session_id=?", sessionId.trim());
    }

    private static void trimToMax(String username) {
        int max = Math.max(1, AppPolicy.AUTH_MAX_SESSIONS);
        List<String> ids = db().query(
                "SELECT session_id FROM sys_auth_session WHERE username=? AND kicked=0 ORDER BY created_at ASC",
                (rs, i) -> rs.getString("session_id"),
                username);
        if (ids == null || ids.size() <= max) return;
        int drop = ids.size() - max;
        for (int i = 0; i < drop; i++) {
            kick(ids.get(i));
        }
    }

    public static List<Map<String, Object>> listOnline() {
        if (!ready()) return List.of();
        return db().query(
                "SELECT session_id,username,ip,user_agent,created_at,last_seen_at FROM sys_auth_session "
                        + "WHERE kicked=0 ORDER BY last_seen_at DESC LIMIT 500",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("sessionId", rs.getString("session_id"));
                    m.put("username", rs.getString("username"));
                    m.put("ip", rs.getString("ip"));
                    m.put("userAgent", rs.getString("user_agent"));
                    m.put("createdAt", fmt(rs.getTimestamp("created_at")));
                    m.put("lastSeenAt", fmt(rs.getTimestamp("last_seen_at")));
                    return m;
                });
    }

    public static List<Map<String, Object>> listByUser(String username) {
        if (!ready() || username == null || username.isBlank()) return List.of();
        return db().query(
                "SELECT session_id,username,ip,user_agent,created_at,last_seen_at FROM sys_auth_session "
                        + "WHERE username=? AND kicked=0 ORDER BY created_at DESC",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("sessionId", rs.getString("session_id"));
                    m.put("username", rs.getString("username"));
                    m.put("ip", rs.getString("ip"));
                    m.put("userAgent", rs.getString("user_agent"));
                    m.put("createdAt", fmt(rs.getTimestamp("created_at")));
                    m.put("lastSeenAt", fmt(rs.getTimestamp("last_seen_at")));
                    return m;
                },
                username.trim());
    }

    public static boolean belongsTo(String sessionId, String username) {
        if (!ready() || sessionId == null || username == null) return false;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM sys_auth_session WHERE session_id=? AND username=? AND kicked=0",
                    Integer.class,
                    sessionId.trim(),
                    username.trim());
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }
}
