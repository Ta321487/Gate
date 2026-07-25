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
}
