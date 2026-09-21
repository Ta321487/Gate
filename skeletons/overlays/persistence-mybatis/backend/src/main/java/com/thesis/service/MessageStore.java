package com.thesis.service;

import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.thesis.config.MybatisSupport;
import com.thesis.mapper.MessageMapper;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 基线站内消息（sys_message）：审核结果等个人通知，非公告广播。
 */
public class MessageStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static Boolean tableReady;

    private static MessageMapper mapper() {
        return MybatisSupport.mapper(MessageMapper.class);
    }

    private static boolean ready() {
        if (tableReady != null) return tableReady;
        try {
            Integer n = mapper().countMessageTable();
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        String s = String.valueOf(o);
        return s.isBlank() ? null : s;
    }

    private static Map<String, Object> shape(Map<String, Object> raw) {
        if (raw == null) return null;
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", raw.get("id"));
        m.put("username", raw.get("username"));
        m.put("title", raw.get("title"));
        m.put("body", raw.get("body"));
        m.put("refType", raw.get("refType"));
        m.put("refId", raw.get("refId"));
        Object readAt = raw.get("readAt");
        m.put("readAt", fmt(readAt));
        m.put("createdAt", fmt(raw.get("createdAt")));
        m.put("read", readAt != null);
        return m;
    }

    public static void send(String username, String title, String body, String refType, Long refId) {
        if (!ready() || username == null || username.isBlank()) return;
        String t = title == null || title.isBlank() ? "系统通知" : title.trim();
        String b = body == null ? "" : body.trim();
        if (b.length() > 500) b = b.substring(0, 500);
        String rt = refType == null ? "" : refType.trim();
        mapper().insert(username.trim(), t, b, rt, refId);
    }

    /**
     * 通知所有管理端账号（role=admin，含总管与子管）。
     * @param excludeUsername 可空；不发给该账号（如初审人自己）
     */
    public static void notifyAdmins(String title, String body, String refType, Long refId, String excludeUsername) {
        if (!ready()) return;
        List<String> admins;
        try {
            admins = mapper().listAdminUsernames();
        } catch (Exception e) {
            try {
                admins = mapper().listAdminUsernamesFallback();
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
        PageHelper.startPage(page, size);
        List<Map<String, Object>> raw = mapper().selectByUsername(username);
        PageInfo<Map<String, Object>> pi = new PageInfo<>(raw);
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> r : raw) {
            list.add(shape(r));
        }
        out.put("list", list);
        out.put("total", pi.getTotal());
        out.put("page", page);
        out.put("size", size);
        out.put("unread", unreadCount(username));
        return out;
    }

    public static int unreadCount(String username) {
        if (!ready() || username == null || username.isBlank()) return 0;
        return mapper().countUnread(username);
    }

    public static boolean markRead(String username, long id) {
        if (!ready() || username == null || username.isBlank()) return false;
        if (mapper().countOwned(id, username) == 0) return false;
        mapper().markRead(Timestamp.valueOf(LocalDateTime.now()), id, username);
        return true;
    }

    public static int markAllRead(String username) {
        if (!ready() || username == null || username.isBlank()) return 0;
        return mapper().markAllRead(Timestamp.valueOf(LocalDateTime.now()), username);
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
            Integer n = MybatisSupport.db().queryForObject(
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
            MybatisSupport.db().execute(
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
            Integer n = MybatisSupport.db().queryForObject(
                    "SELECT COUNT(*) FROM sys_message_template WHERE code=?", Integer.class, code);
            if (n != null && n > 0) return;
            MybatisSupport.db().update(
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
                Map<String, Object> tpl = MybatisSupport.db().queryForObject(
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
        Integer total = MybatisSupport.db().queryForObject("SELECT COUNT(*) FROM sys_message_template", Integer.class);
        List<Map<String, Object>> rows = MybatisSupport.db().query(
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
            cur = MybatisSupport.db().queryForObject(
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
        MybatisSupport.db().update(
                "UPDATE sys_message_template SET title=?, body=?, enabled=?, updated_at=NOW() WHERE id=?",
                t, b, en, id);
        return MybatisSupport.db().queryForObject(
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
