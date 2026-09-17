package com.thesis.service;

import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.thesis.config.MybatisSupport;
import com.thesis.mapper.ItemCommentMapper;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * 档案条下评论（item_comment）：挂在影音/曲目/文章下；≠ 门户留言 guestbook。
 */
public class ItemCommentStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final int BODY_MAX = 500;
    private static Boolean tableReady;

    private static ItemCommentMapper mapper() {
        return MybatisSupport.mapper(ItemCommentMapper.class);
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

    public static void resetReadyCache() {
        tableReady = null;
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
        Object id = raw.get("id");
        m.put("id", id instanceof Number n ? n.longValue() : id);
        Object itemId = col(raw, "itemId", "item_id");
        m.put("itemId", itemId instanceof Number n ? n.longValue() : itemId);
        m.put("username", col(raw, "username", "username"));
        m.put("nickname", col(raw, "nickname", "nickname"));
        m.put("body", col(raw, "body", "body"));
        m.put("createdAt", fmt(col(raw, "createdAt", "created_at")));
        return m;
    }

    public static Map<String, Object> get(long id) {
        if (!ready()) return null;
        return shape(mapper().selectById(id));
    }

    public static Map<String, Object> add(long itemId, String username, String nickname, String body) {
        if (!ready() || itemId <= 0) return null;
        String b = clip(body, BODY_MAX);
        if (b.isBlank()) return null;
        String nick = clip(nickname == null || nickname.isBlank() ? username : nickname, 64);
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("itemId", itemId);
        row.put("username", username == null ? "" : username);
        row.put("nickname", nick);
        row.put("body", b);
        mapper().insert(row);
        Object key = row.get("id");
        return get(key == null ? 0L : ((Number) key).longValue());
    }

    public static boolean delete(long id) {
        if (!ready()) return false;
        return mapper().deleteById(id) > 0;
    }

    public static Map<String, Object> pageByItem(long itemId, int page, int size) {
        Map<String, Object> out = emptyPage(page, size);
        if (!ready() || itemId <= 0) return out;
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        PageHelper.startPage(page, size);
        List<Map<String, Object>> raw = mapper().selectByItem(itemId);
        PageInfo<Map<String, Object>> pi = new PageInfo<>(raw);
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> r : raw) {
            list.add(shape(r));
        }
        out.put("list", list);
        out.put("total", (int) pi.getTotal());
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    public static Map<String, Object> pageAdmin(int page, int size, Long itemId) {
        Map<String, Object> out = emptyPage(page, size);
        if (!ready()) return out;
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        Long filter = (itemId != null && itemId > 0) ? itemId : null;
        PageHelper.startPage(page, size);
        List<Map<String, Object>> raw = mapper().selectAdmin(filter);
        PageInfo<Map<String, Object>> pi = new PageInfo<>(raw);
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> r : raw) {
            list.add(shape(r));
        }
        out.put("list", list);
        out.put("total", (int) pi.getTotal());
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    private static Map<String, Object> emptyPage(int page, int size) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", List.of());
        out.put("total", 0);
        out.put("page", page < 1 ? 1 : page);
        out.put("size", size < 1 ? 10 : size);
        return out;
    }
}
