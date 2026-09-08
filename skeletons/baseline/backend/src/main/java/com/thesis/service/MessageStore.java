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

    private static boolean templateEnabled = false;
    private static Boolean templateTableReady;

    public static void configureTemplate(boolean on) {
        templateEnabled = on;
        templateTableReady = null;
        if (templateEnabled) ensureTemplateTable();
    }

    public static boolean templateEnabled() {
        return templateEnabled;
    }

    private static boolean templateReady() {
        if (!templateEnabled) return false;
        if (templateTableReady != null) return templateTableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='sys_message_template'",
                    Integer.class);
            templateTableReady = n != null && n > 0;
        } catch (Exception e) {
            templateTableReady = false;
        }
        return templateTableReady;
    }

    private static void ensureTemplateTable() {
        try {
            db().execute(
                    "CREATE TABLE IF NOT EXISTS sys_message_template ("
                            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
                            + "code VARCHAR(64) NOT NULL,"
                            + "title VARCHAR(128) NOT NULL,"
                            + "body VARCHAR(512) NOT NULL,"
                            + "enabled TINYINT NOT NULL DEFAULT 1,"
                            + "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,"
                            + "UNIQUE KEY uk_msg_tpl_code (code)"
                            + ")");
            seedTemplate("ticket_approved", "审核已通过", "「{{subject}}」已通过{{note_suffix}}");
            seedTemplate("ticket_rejected", "审核未通过", "「{{subject}}」已驳回{{note_suffix}}");
        } catch (Exception ignored) {
        }
        templateTableReady = null;
    }

    private static void seedTemplate(String code, String title, String body) {
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM sys_message_template WHERE code=?", Integer.class, code);
            if (n != null && n > 0) return;
            db().update(
                    "INSERT INTO sys_message_template (code,title,body,enabled) VALUES (?,?,?,1)",
                    code, title, body);
        } catch (Exception ignored) {
        }
    }

    private static String renderPlaceholders(String raw, Map<String, String> vars) {
        String out = raw == null ? "" : raw;
        if (vars != null) {
            for (Map.Entry<String, String> e : vars.entrySet()) {
                String key = e.getKey() == null ? "" : e.getKey();
                String val = e.getValue() == null ? "" : e.getValue();
                out = out.replace("{{" + key + "}}", val);
            }
        }
        // 未替换占位符清空，避免把 {{x}} 打进学生包
        out = out.replaceAll("\\{\\{[a-zA-Z0-9_]+\\}\\}", "");
        return out;
    }

    /**
     * 有启用模板则套模板发送；否则用 fallback 文案。未挂 message_template 时等同 send(fallback)。
     */
    public static void sendWithTemplate(
            String username,
            String templateCode,
            Map<String, String> vars,
            String fallbackTitle,
            String fallbackBody,
            String refType,
            Long refId) {
        if (templateReady() && templateCode != null && !templateCode.isBlank()) {
            try {
                Map<String, Object> tpl = db().queryForObject(
                        "SELECT title, body, enabled FROM sys_message_template WHERE code=?",
                        (rs, i) -> {
                            Map<String, Object> m = new LinkedHashMap<>();
                            m.put("title", rs.getString("title"));
                            m.put("body", rs.getString("body"));
                            m.put("enabled", rs.getInt("enabled"));
                            return m;
                        },
                        templateCode.trim());
                if (tpl != null && ((Number) tpl.get("enabled")).intValue() == 1) {
                    String title = renderPlaceholders(String.valueOf(tpl.get("title")), vars);
                    String body = renderPlaceholders(String.valueOf(tpl.get("body")), vars);
                    if (title.isBlank()) title = fallbackTitle;
                    if (body.isBlank()) body = fallbackBody;
                    send(username, title, body, refType, refId);
                    return;
                }
            } catch (Exception ignored) {
            }
        }
        send(username, fallbackTitle, fallbackBody, refType, refId);
    }

    public static Map<String, Object> pageTemplates(int page, int size) {
        if (!templateReady()) throw new IllegalStateException("消息模板功能暂不可用");
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        Integer total = db().queryForObject("SELECT COUNT(*) FROM sys_message_template", Integer.class);
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM sys_message_template ORDER BY id ASC LIMIT ? OFFSET ?",
                (rs, i) -> mapTemplate(rs),
                size, (page - 1) * size);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", rows == null ? List.of() : rows);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    public static Map<String, Object> updateTemplate(long id, String title, String body, Boolean enabled) {
        if (!templateReady()) throw new IllegalStateException("消息模板功能暂不可用");
        Map<String, Object> cur;
        try {
            cur = db().queryForObject(
                    "SELECT * FROM sys_message_template WHERE id=?",
                    (rs, i) -> mapTemplate(rs),
                    id);
        } catch (Exception e) {
            cur = null;
        }
        if (cur == null) throw new IllegalArgumentException("模板不存在");
        String t = title == null ? String.valueOf(cur.get("title")) : title.trim();
        String b = body == null ? String.valueOf(cur.get("body")) : body.trim();
        if (t.isBlank()) throw new IllegalStateException("标题不能为空");
        if (b.isBlank()) throw new IllegalStateException("正文不能为空");
        if (t.length() > 128) t = t.substring(0, 128);
        if (b.length() > 512) b = b.substring(0, 512);
        int en = enabled == null
                ? (Boolean.TRUE.equals(cur.get("enabled")) ? 1 : 0)
                : (enabled ? 1 : 0);
        db().update(
                "UPDATE sys_message_template SET title=?, body=?, enabled=?, updated_at=NOW() WHERE id=?",
                t, b, en, id);
        return db().queryForObject(
                "SELECT * FROM sys_message_template WHERE id=?",
                (rs, i) -> mapTemplate(rs),
                id);
    }

    private static Map<String, Object> mapTemplate(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("code", rs.getString("code"));
        m.put("title", rs.getString("title"));
        m.put("body", rs.getString("body"));
        m.put("enabled", rs.getInt("enabled") == 1);
        Timestamp u = null;
        try {
            u = rs.getTimestamp("updated_at");
        } catch (Exception ignored) {
        }
        m.put("updatedAt", fmt(u));
        return m;
    }


}
