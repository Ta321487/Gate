package com.thesis.service;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 基线公告（MySQL sys_notice）。
 */
public class NoticeStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        String s = String.valueOf(o);
        return s.isBlank() ? null : s;
    }

    private static Map<String, Object> row(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("title", rs.getString("title"));
        m.put("content", rs.getString("content"));
        m.put("publisherUsername", rs.getString("publisher_username"));
        m.put("publisherName", rs.getString("publisher_name"));
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        m.put("updatedAt", fmt(rs.getTimestamp("updated_at")));
        return m;
    }

    public static Map<String, Object> add(String title, String content, String publisherUsername, String publisherName) {
        String name = publisherName == null || publisherName.isBlank()
                ? (publisherUsername == null ? "系统" : publisherUsername)
                : publisherName;
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO sys_notice (title,content,publisher_username,publisher_name) VALUES (?,?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, title == null ? "" : title);
            ps.setString(2, content == null ? "" : content);
            ps.setString(3, publisherUsername == null ? "" : publisherUsername);
            ps.setString(4, name);
            return ps;
        }, kh);
        Number key = kh.getKey();
        return get(key == null ? 0L : key.longValue());
    }

    /** 领域启动时追加种子；表内已有同标题则跳过。 */
    public static void seedDomain(String title, String content, String publisherUsername, String publisherName) {
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM sys_notice WHERE title=?", Integer.class, title);
        if (n != null && n > 0) return;
        add(title, content, publisherUsername, publisherName);
    }

    public static Map<String, Object> get(long id) {
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM sys_notice WHERE id=?", (rs, i) -> row(rs), id);
        return list.isEmpty() ? null : list.get(0);
    }

    public static Map<String, Object> update(long id, String title, String content) {
        Map<String, Object> m = get(id);
        if (m == null) return null;
        String t = title != null ? title : String.valueOf(m.get("title"));
        String c = content != null ? content : String.valueOf(m.get("content"));
        db().update(
                "UPDATE sys_notice SET title=?, content=?, updated_at=NOW() WHERE id=?",
                t, c, id);
        return get(id);
    }

    public static boolean delete(long id) {
        return db().update("DELETE FROM sys_notice WHERE id=?", id) > 0;
    }

    public static Map<String, Object> page(int page, int size) {
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        Integer total = db().queryForObject("SELECT COUNT(*) FROM sys_notice", Integer.class);
        int t = total == null ? 0 : total;
        int offset = (page - 1) * size;
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM sys_notice ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> row(rs), size, offset);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", t);
        out.put("page", page);
        out.put("size", size);
        return out;
    }
}
