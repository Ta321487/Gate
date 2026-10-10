package com.thesis.service;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 专栏/分类订阅（C-04）：category_follow 表；≠推荐引擎。
 */
public final class CategoryFollowStore {

    private static final String TABLE = "category_follow";
    private static boolean enabled = false;

    private CategoryFollowStore() {}

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
                            + "username VARCHAR(64) NOT NULL,"
                            + "category_id BIGINT NOT NULL,"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "UNIQUE KEY uk_cf_user_cat (username, category_id),"
                            + "KEY idx_cf_cat (category_id)"
                            + ")");
        } catch (Exception ignored) {
        }
    }

    /** @return true=已订阅 */
    public static boolean toggle(String username, long categoryId) {
        if (!enabled || username == null || username.isBlank() || categoryId <= 0) return false;
        ensureTable();
        String u = username.trim();
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM " + TABLE + " WHERE username=? AND category_id=?",
                Integer.class, u, categoryId);
        if (n != null && n > 0) {
            db().update("DELETE FROM " + TABLE + " WHERE username=? AND category_id=?", u, categoryId);
            return false;
        }
        db().update(
                "INSERT INTO " + TABLE + " (username,category_id,created_at) VALUES (?,?,?)",
                u, categoryId, Timestamp.valueOf(LocalDateTime.now()));
        return true;
    }

    public static boolean isFollowing(String username, long categoryId) {
        if (!enabled || username == null || username.isBlank() || categoryId <= 0) return false;
        ensureTable();
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM " + TABLE + " WHERE username=? AND category_id=?",
                Integer.class, username.trim(), categoryId);
        return n != null && n > 0;
    }

    public static int followerCount(long categoryId) {
        if (!enabled || categoryId <= 0) return 0;
        ensureTable();
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM " + TABLE + " WHERE category_id=?",
                Integer.class, categoryId);
        return n == null ? 0 : n;
    }

    public static List<Map<String, Object>> listMine(String username) {
        List<Map<String, Object>> out = new ArrayList<>();
        if (!enabled || username == null || username.isBlank()) return out;
        ensureTable();
        db().query(
                "SELECT category_id, created_at FROM " + TABLE + " WHERE username=? ORDER BY id DESC",
                rs -> {
                    while (rs.next()) {
                        Map<String, Object> m = new LinkedHashMap<>();
                        long cid = rs.getLong("category_id");
                        m.put("categoryId", cid);
                        m.put("followerCount", followerCount(cid));
                        Timestamp ts = rs.getTimestamp("created_at");
                        if (ts != null) m.put("createdAt", ts.toLocalDateTime().toString().replace('T', ' '));
                        out.add(m);
                    }
                    return null;
                },
                username.trim());
        return out;
    }

    /** 新文公开时通知该专栏订阅者（跳过作者本人）。 */
    public static void notifyFollowers(long categoryId, String authorUsername, long itemId, String title) {
        if (!enabled || categoryId <= 0) return;
        ensureTable();
        String author = authorUsername == null ? "" : authorUsername.trim();
        String t = title == null || title.isBlank() ? "新文章" : title.trim();
        if (t.length() > 80) t = t.substring(0, 80);
        List<String> users = db().query(
                "SELECT username FROM " + TABLE + " WHERE category_id=?",
                (rs, i) -> rs.getString("username"),
                categoryId);
        if (users == null) return;
        for (String u : users) {
            if (u == null || u.isBlank() || u.equals(author)) continue;
            try {
                MessageStore.send(
                        u.trim(),
                        "订阅专栏有更新",
                        "你订阅的专栏发布了新文章：" + t,
                        "archive",
                        Long.valueOf(itemId));
            } catch (Exception ignored) {
            }
        }
    }
}
