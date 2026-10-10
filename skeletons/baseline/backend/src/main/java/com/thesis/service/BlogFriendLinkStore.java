package com.thesis.service;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 博客友情链接栏（C-04）：blog_friend_link 浅表。 */
public final class BlogFriendLinkStore {

    private static final String TABLE = "blog_friend_link";
    private static boolean enabled = false;

    private BlogFriendLinkStore() {}

    public static void configure(boolean on) {
        enabled = on;
        if (on) ensureTable();
    }

    public static boolean enabled() {
        return enabled;
    }

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    private static void ensureTable() {
        try {
            db().execute(
                    "CREATE TABLE IF NOT EXISTS " + TABLE + " ("
                            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
                            + "title VARCHAR(128) NOT NULL,"
                            + "url VARCHAR(512) NOT NULL,"
                            + "sort_order INT NOT NULL DEFAULT 0,"
                            + "enabled TINYINT NOT NULL DEFAULT 1,"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "KEY idx_bfl_sort (enabled, sort_order, id)"
                            + ")");
        } catch (Exception ignored) {
        }
    }

    public static List<Map<String, Object>> listPublic() {
        return list(false);
    }

    public static List<Map<String, Object>> listAdmin() {
        return list(true);
    }

    private static List<Map<String, Object>> list(boolean all) {
        List<Map<String, Object>> out = new ArrayList<>();
        if (!enabled) return out;
        ensureTable();
        String sql = all
                ? "SELECT * FROM " + TABLE + " ORDER BY sort_order ASC, id ASC"
                : "SELECT * FROM " + TABLE + " WHERE enabled=1 ORDER BY sort_order ASC, id ASC";
        db().query(sql, rs -> {
            while (rs.next()) {
                out.add(row(rs));
            }
            return null;
        });
        return out;
    }

    public static Map<String, Object> save(Long id, String title, String url, int sortOrder, boolean on) {
        if (!enabled) throw new IllegalStateException("未开放友情链接");
        ensureTable();
        String t = title == null ? "" : title.trim();
        String u = url == null ? "" : url.trim();
        if (t.isBlank()) throw new IllegalArgumentException("名称不能为空");
        if (u.isBlank()) throw new IllegalArgumentException("链接不能为空");
        if (t.length() > 128) t = t.substring(0, 128);
        if (u.length() > 512) u = u.substring(0, 512);
        if (id != null && id > 0) {
            db().update(
                    "UPDATE " + TABLE + " SET title=?,url=?,sort_order=?,enabled=? WHERE id=?",
                    t, u, sortOrder, on ? 1 : 0, id);
            return get(id);
        }
        KeyHolder kh = new GeneratedKeyHolder();
        String ft = t;
        String fu = u;
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO " + TABLE + " (title,url,sort_order,enabled,created_at) VALUES (?,?,?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, ft);
            ps.setString(2, fu);
            ps.setInt(3, sortOrder);
            ps.setInt(4, on ? 1 : 0);
            ps.setTimestamp(5, Timestamp.valueOf(LocalDateTime.now()));
            return ps;
        }, kh);
        Number key = kh.getKey();
        return get(key == null ? 0L : key.longValue());
    }

    public static boolean delete(long id) {
        if (!enabled || id <= 0) return false;
        ensureTable();
        return db().update("DELETE FROM " + TABLE + " WHERE id=?", id) > 0;
    }

    public static Map<String, Object> get(long id) {
        if (id <= 0) return null;
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM " + TABLE + " WHERE id=?",
                (rs, i) -> row(rs),
                id);
        return list.isEmpty() ? null : list.get(0);
    }

    private static Map<String, Object> row(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("title", rs.getString("title"));
        m.put("url", rs.getString("url"));
        m.put("sortOrder", rs.getInt("sort_order"));
        m.put("enabled", rs.getInt("enabled") == 1);
        Timestamp ts = rs.getTimestamp("created_at");
        if (ts != null) m.put("createdAt", ts.toLocalDateTime().toString().replace('T', ' '));
        return m;
    }
}
