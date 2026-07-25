package com.thesis.service;

import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.thesis.config.MybatisSupport;
import com.thesis.mapper.NoticeMapper;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 基线公告（MySQL sys_notice）。
 */
public class NoticeStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private static NoticeMapper mapper() {
        return MybatisSupport.mapper(NoticeMapper.class);
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
        m.put("title", raw.get("title"));
        m.put("content", raw.get("content"));
        m.put("publisherUsername", raw.get("publisherUsername"));
        m.put("publisherName", raw.get("publisherName"));
        m.put("createdAt", fmt(raw.get("createdAt")));
        m.put("updatedAt", fmt(raw.get("updatedAt")));
        return m;
    }

    public static Map<String, Object> add(String title, String content, String publisherUsername, String publisherName) {
        String name = publisherName == null || publisherName.isBlank()
                ? (publisherUsername == null ? "系统" : publisherUsername)
                : publisherName;
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("title", title == null ? "" : title);
        row.put("content", content == null ? "" : content);
        row.put("publisherUsername", publisherUsername == null ? "" : publisherUsername);
        row.put("publisherName", name);
        mapper().insert(row);
        Object key = row.get("id");
        return get(key == null ? 0L : ((Number) key).longValue());
    }

    /** 领域启动时追加种子；表内已有同标题则跳过。 */
    public static void seedDomain(String title, String content, String publisherUsername, String publisherName) {
        if (mapper().countByTitle(title) > 0) return;
        add(title, content, publisherUsername, publisherName);
    }

    public static Map<String, Object> get(long id) {
        return shape(mapper().selectById(id));
    }

    public static Map<String, Object> update(long id, String title, String content) {
        Map<String, Object> m = get(id);
        if (m == null) return null;
        String t = title != null ? title : String.valueOf(m.get("title"));
        String c = content != null ? content : String.valueOf(m.get("content"));
        mapper().update(id, t, c);
        return get(id);
    }

    public static boolean delete(long id) {
        return mapper().deleteById(id) > 0;
    }

    public static Map<String, Object> page(int page, int size) {
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        PageHelper.startPage(page, size);
        List<Map<String, Object>> raw = mapper().selectAllOrderByIdDesc();
        PageInfo<Map<String, Object>> pi = new PageInfo<>(raw);
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> r : raw) {
            list.add(shape(r));
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", pi.getTotal());
        out.put("page", page);
        out.put("size", size);
        return out;
    }
}
