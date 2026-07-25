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
import java.util.Map;

/**
 * 门户留言板（sys_guestbook）：用户发表；管理端删除/简短回复。
 */
public class GuestbookStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final int BODY_MAX = 500;
    private static Boolean tableReady;

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

    private static Map<String, Object> shape(Map<String, Object> raw) {
        if (raw == null) return null;
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", raw.get("id"));
        m.put("username", raw.get("username"));
        m.put("nickname", raw.get("nickname"));
        m.put("body", raw.get("body"));
        m.put("reply", raw.get("reply"));
        m.put("replyUsername", raw.get("replyUsername"));
        m.put("repliedAt", fmt(raw.get("repliedAt")));
        m.put("createdAt", fmt(raw.get("createdAt")));
        return m;
    }

    public static Map<String, Object> get(long id) {
        if (!ready()) return null;
        return shape(mapper().selectById(id));
    }

    public static Map<String, Object> add(String username, String nickname, String body) {
        if (!ready()) return null;
        String b = clip(body, BODY_MAX);
        if (b.isBlank()) return null;
        String nick = clip(nickname == null || nickname.isBlank() ? username : nickname, 64);
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("username", username == null ? "" : username);
        row.put("nickname", nick);
        row.put("body", b);
        mapper().insert(row);
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
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", List.of());
        out.put("total", 0);
        out.put("page", page < 1 ? 1 : page);
        out.put("size", size < 1 ? 10 : size);
        if (!ready()) return out;
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        PageHelper.startPage(page, size);
        List<Map<String, Object>> raw = mapper().selectAllOrderByIdDesc();
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
