package com.thesis.service;

import com.thesis.capability.ArchiveStore;
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

/** 影音分集（C-05）：media_episode 表；新分集可通知分类订阅者。 */
public final class MediaEpisodeStore {

    private static final String TABLE = "media_episode";
    private static boolean enabled = false;

    private MediaEpisodeStore() {}

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
                            + "item_id BIGINT NOT NULL,"
                            + "title VARCHAR(128) NOT NULL,"
                            + "sort_ord INT NOT NULL DEFAULT 0,"
                            + "media_url VARCHAR(512) NOT NULL DEFAULT '',"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "KEY idx_me_item (item_id, sort_ord, id)"
                            + ")");
        } catch (Exception ignored) {
        }
    }

    public static List<Map<String, Object>> listByItem(long itemId) {
        List<Map<String, Object>> out = new ArrayList<>();
        if (!enabled || itemId <= 0) return out;
        ensureTable();
        db().query(
                "SELECT id, item_id, title, sort_ord, media_url, created_at FROM " + TABLE
                        + " WHERE item_id=? ORDER BY sort_ord ASC, id ASC",
                rs -> {
                    while (rs.next()) {
                        out.add(mapRow(rs));
                    }
                    return null;
                },
                itemId);
        return out;
    }

    public static Map<String, Object> save(
            Long id, long itemId, String title, int sortOrd, String mediaUrl, boolean notify) {
        if (!enabled) throw new IllegalStateException("未开放分集");
        if (itemId <= 0) throw new IllegalArgumentException("片单无效");
        String t = title == null ? "" : title.trim();
        if (t.isBlank()) throw new IllegalArgumentException("分集标题不能为空");
        if (t.length() > 128) t = t.substring(0, 128);
        String url = mediaUrl == null ? "" : mediaUrl.trim();
        if (url.length() > 512) url = url.substring(0, 512);
        ensureTable();
        boolean isNew = id == null || id <= 0;
        long eid;
        if (!isNew) {
            db().update(
                    "UPDATE " + TABLE + " SET title=?, sort_ord=?, media_url=? WHERE id=? AND item_id=?",
                    t, sortOrd, url, id, itemId);
            eid = id;
        } else {
            KeyHolder kh = new GeneratedKeyHolder();
            String finalT = t;
            String finalUrl = url;
            db().update(con -> {
                PreparedStatement ps = con.prepareStatement(
                        "INSERT INTO " + TABLE + " (item_id,title,sort_ord,media_url,created_at) VALUES (?,?,?,?,?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setLong(1, itemId);
                ps.setString(2, finalT);
                ps.setInt(3, sortOrd);
                ps.setString(4, finalUrl);
                ps.setTimestamp(5, Timestamp.valueOf(LocalDateTime.now()));
                return ps;
            }, kh);
            Number key = kh.getKey();
            eid = key == null ? 0L : key.longValue();
            if (notify) notifyFollowersOfNewEpisode(itemId, t);
        }
        return get(eid);
    }

    public static boolean delete(long id) {
        if (!enabled || id <= 0) return false;
        ensureTable();
        return db().update("DELETE FROM " + TABLE + " WHERE id=?", id) > 0;
    }

    public static Map<String, Object> get(long id) {
        if (!enabled || id <= 0) return null;
        ensureTable();
        List<Map<String, Object>> rows = db().query(
                "SELECT id, item_id, title, sort_ord, media_url, created_at FROM " + TABLE + " WHERE id=?",
                (rs, i) -> mapRow(rs),
                id);
        return rows == null || rows.isEmpty() ? null : rows.get(0);
    }

    private static void notifyFollowersOfNewEpisode(long itemId, String episodeTitle) {
        try {
            Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
            if (item == null) return;
            long cat = 0L;
            Object c = item.get("categoryId");
            if (c instanceof Number n) cat = n.longValue();
            String owner = item.get("ownerUsername") == null ? "" : String.valueOf(item.get("ownerUsername"));
            if (owner.isBlank()) owner = item.get("author") == null ? "" : String.valueOf(item.get("author"));
            String mediaTitle = item.get("title") == null ? "片单" : String.valueOf(item.get("title"));
            String msg = mediaTitle + " 更新了分集：" + episodeTitle;
            CategoryFollowStore.notifyFollowers(cat, owner, itemId, msg);
        } catch (Exception ignored) {
        }
    }

    private static Map<String, Object> mapRow(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("itemId", rs.getLong("item_id"));
        m.put("title", rs.getString("title"));
        m.put("sortOrd", rs.getInt("sort_ord"));
        m.put("mediaUrl", rs.getString("media_url"));
        Timestamp ts = rs.getTimestamp("created_at");
        if (ts != null) m.put("createdAt", ts.toLocalDateTime().toString().replace('T', ' '));
        return m;
    }
}
