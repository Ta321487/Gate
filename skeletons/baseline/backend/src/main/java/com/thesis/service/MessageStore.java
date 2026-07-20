package com.thesis.service;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 基线站内消息（sys_message）：审核结果等个人通知，非公告广播。
 */
public class MessageStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static Boolean tableReady;

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    private static boolean ready() {
        if (tableReady != null) return tableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='sys_message'",
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

    private static Map<String, Object> row(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("title", rs.getString("title"));
        m.put("body", rs.getString("body"));
        m.put("refType", rs.getString("ref_type"));
        long refId = rs.getLong("ref_id");
        m.put("refId", rs.wasNull() ? null : refId);
        m.put("readAt", fmt(rs.getTimestamp("read_at")));
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        m.put("read", rs.getTimestamp("read_at") != null);
        return m;
    }

    public static void send(String username, String title, String body, String refType, Long refId) {
        if (!ready() || username == null || username.isBlank()) return;
        String t = title == null || title.isBlank() ? "系统通知" : title.trim();
        String b = body == null ? "" : body.trim();
        if (b.length() > 500) b = b.substring(0, 500);
        String rt = refType == null ? "" : refType.trim();
        db().update(
                "INSERT INTO sys_message (username,title,body,ref_type,ref_id) VALUES (?,?,?,?,?)",
                username.trim(), t, b, rt, refId);
    }

    /**
     * 通知所有管理端账号（role=admin，含总管与子管）。
     * @param excludeUsername 可空；不发给该账号（如初审人自己）
     */
    public static void notifyAdmins(String title, String body, String refType, Long refId, String excludeUsername) {
        if (!ready()) return;
        List<String> admins;
        try {
            admins = db().query(
                    "SELECT username FROM sys_user WHERE role='admin' AND (enabled IS NULL OR enabled=1)",
                    (rs, i) -> rs.getString("username"));
        } catch (Exception e) {
            try {
                admins = db().query(
                        "SELECT username FROM sys_user WHERE role='admin'",
                        (rs, i) -> rs.getString("username"));
            } catch (Exception e2) {
                return;
            }
        }
        String skip = excludeUsername == null ? "" : excludeUsername.trim();
        for (String u : admins) {
            if (u == null || u.isBlank()) continue;
            if (!skip.isEmpty() && skip.equals(u.trim())) continue;
            try {
                send(u, title, body, refType, refId);
            } catch (Exception ignored) {
            }
        }
    }

    public static void notifyAdmins(String title, String body, String refType, Long refId) {
        notifyAdmins(title, body, refType, refId, null);
    }

    public static Map<String, Object> page(String username, int page, int size) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", List.of());
        out.put("total", 0);
        out.put("page", page);
        out.put("size", size);
        out.put("unread", 0);
        if (!ready() || username == null || username.isBlank()) return out;
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM sys_message WHERE username=?", Integer.class, username);
        int t = total == null ? 0 : total;
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM sys_message WHERE username=? ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> row(rs), username, size, (page - 1) * size);
        out.put("list", list);
        out.put("total", t);
        out.put("page", page);
        out.put("size", size);
        out.put("unread", unreadCount(username));
        return out;
    }

    public static int unreadCount(String username) {
        if (!ready() || username == null || username.isBlank()) return 0;
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM sys_message WHERE username=? AND read_at IS NULL",
                Integer.class, username);
        return n == null ? 0 : n;
    }

    public static boolean markRead(String username, long id) {
        if (!ready() || username == null || username.isBlank()) return false;
        Integer exists = db().queryForObject(
                "SELECT COUNT(*) FROM sys_message WHERE id=? AND username=?",
                Integer.class, id, username);
        if (exists == null || exists == 0) return false;
        db().update(
                "UPDATE sys_message SET read_at=? WHERE id=? AND username=? AND read_at IS NULL",
                Timestamp.valueOf(LocalDateTime.now()), id, username);
        return true;
    }

    public static int markAllRead(String username) {
        if (!ready() || username == null || username.isBlank()) return 0;
        return db().update(
                "UPDATE sys_message SET read_at=? WHERE username=? AND read_at IS NULL",
                Timestamp.valueOf(LocalDateTime.now()), username);
    }
}
