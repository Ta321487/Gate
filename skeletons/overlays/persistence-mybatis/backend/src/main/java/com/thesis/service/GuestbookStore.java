package com.thesis.service;

import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.thesis.config.MybatisSupport;
import com.thesis.mapper.GuestbookMapper;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * 门户留言板（sys_guestbook）：用户发表；管理端删除/简短回复。
 * 多店时 channel=user（买家↔平台）/ merchant（商家↔平台）。
 */
public class GuestbookStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final int BODY_MAX = 500;
    private static Boolean tableReady;
    private static Boolean hasChannel;

    private static GuestbookMapper mapper() {
        return MybatisSupport.mapper(GuestbookMapper.class);
    }

    public static boolean ready() {
        if (tableReady != null) return tableReady;
        try {
            Integer n = mapper().countTable();
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    public static boolean hasChannel() {
        if (hasChannel == null) {
            try {
                hasChannel = mapper().countColumn("channel") > 0;
            } catch (Exception e) {
                hasChannel = false;
            }
        }
        return hasChannel;
    }

    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        String s = String.valueOf(o);
        return s.isBlank() ? null : s;
    }

    private static String clip(String s, int max) {
        if (s == null) return "";
        String t = s.trim();
        return t.length() <= max ? t : t.substring(0, max);
    }

    private static String normChannel(String channel) {
        String c = channel == null ? "" : channel.trim().toLowerCase(Locale.ROOT);
        if ("merchant".equals(c) || "shop".equals(c) || "seller".equals(c)) return "merchant";
        return "user";
    }

    private static Object col(Map<String, Object> raw, String camel, String snake) {
        if (raw == null) return null;
        if (raw.containsKey(camel)) return raw.get(camel);
        if (raw.containsKey(snake)) return raw.get(snake);
        String lower = snake.toLowerCase(Locale.ROOT);
        for (Map.Entry<String, Object> e : raw.entrySet()) {
            if (e.getKey() != null && e.getKey().equalsIgnoreCase(lower)) return e.getValue();
        }
        return null;
    }

    private static Map<String, Object> shape(Map<String, Object> raw) {
        if (raw == null) return null;
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", raw.get("id"));
        m.put("username", col(raw, "username", "username"));
        m.put("nickname", col(raw, "nickname", "nickname"));
        m.put("body", col(raw, "body", "body"));
        m.put("reply", col(raw, "reply", "reply"));
        m.put("replyUsername", col(raw, "replyUsername", "reply_username"));
        m.put("repliedAt", fmt(col(raw, "repliedAt", "replied_at")));
        m.put("createdAt", fmt(col(raw, "createdAt", "created_at")));
        if (hasChannel()) {
            Object ch = col(raw, "channel", "channel");
            String s = ch == null ? "" : String.valueOf(ch).trim();
            m.put("channel", s.isBlank() ? "user" : s);
        } else {
            m.put("channel", "user");
        }
        return m;
    }

    public static Map<String, Object> get(long id) {
        if (!ready()) return null;
        return shape(mapper().selectById(id));
    }

    public static Map<String, Object> add(String username, String nickname, String body) {
        return add(username, nickname, body, "user");
    }

    public static Map<String, Object> add(String username, String nickname, String body, String channel) {
        if (!ready()) return null;
        String b = clip(body, BODY_MAX);
        if (b.isBlank()) return null;
        String nick = clip(nickname == null || nickname.isBlank() ? username : nickname, 64);
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("username", username == null ? "" : username);
        row.put("nickname", nick);
        row.put("body", b);
        String ch = normChannel(channel);
        if ("merchant".equals(ch) && !hasChannel()) {
            throw new IllegalStateException("系统未配置留言通道字段，无法保存");
        }
        if (hasChannel()) {
            row.put("channel", ch);
            mapper().insertWithChannel(row);
        } else {
            mapper().insert(row);
        }
        Object key = row.get("id");
        return get(key == null ? 0L : ((Number) key).longValue());
    }

    public static Map<String, Object> reply(long id, String reply, String replyUsername) {
        if (!ready()) return null;
        Map<String, Object> m = get(id);
        if (m == null) return null;
        String r = clip(reply, BODY_MAX);
        mapper().reply(id, r, replyUsername == null ? "" : replyUsername);
        return get(id);
    }

    public static boolean delete(long id) {
        if (!ready()) return false;
        return mapper().deleteById(id) > 0;
    }

    public static Map<String, Object> page(int page, int size) {
        return page(page, size, null, null);
    }

    /**
     * @param channel 多店：user / merchant；空=不过滤通道
     * @param onlyUsername 非空时仅本人留言（商家看自己的平台沟通）
     */
    public static Map<String, Object> page(int page, int size, String channel, String onlyUsername) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", List.of());
        out.put("total", 0);
        out.put("page", page < 1 ? 1 : page);
        out.put("size", size < 1 ? 10 : size);
        if (!ready()) return out;
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        String ch = null;
        if (hasChannel() && channel != null && !channel.isBlank()) {
            ch = normChannel(channel);
        }
        String only = (onlyUsername == null || onlyUsername.isBlank()) ? null : onlyUsername.trim();
        PageHelper.startPage(page, size);
        List<Map<String, Object>> raw = mapper().selectPage(ch, only);
        PageInfo<Map<String, Object>> pi = new PageInfo<>(raw);
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> r : raw) {
            list.add(shape(r));
        }
        out.put("list", list);
        out.put("total", pi.getTotal());
        out.put("page", page);
        out.put("size", size);
        return out;
    }
}
