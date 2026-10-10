package com.thesis.service;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 播放进度（C-05）：按用户+片单+分集一条；≠多端云同步。 */
public final class MediaPlayProgressStore {

    private static final String TABLE = "media_play_progress";
    private static boolean enabled = false;

    private MediaPlayProgressStore() {}

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
                            + "item_id BIGINT NOT NULL,"
                            + "episode_id BIGINT NOT NULL DEFAULT 0,"
                            + "position_sec INT NOT NULL DEFAULT 0,"
                            + "completed TINYINT NOT NULL DEFAULT 0,"
                            + "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,"
                            + "UNIQUE KEY uk_mpp_user_item_ep (username, item_id, episode_id),"
                            + "KEY idx_mpp_item (item_id)"
                            + ")");
        } catch (Exception ignored) {
        }
    }

    public static Map<String, Object> get(String username, long itemId, long episodeId) {
        Map<String, Object> empty = blank(itemId, episodeId);
        if (!enabled || username == null || username.isBlank() || itemId <= 0) return empty;
        ensureTable();
        long ep = episodeId < 0 ? 0 : episodeId;
        List<Map<String, Object>> rows = db().query(
                "SELECT position_sec, completed, updated_at FROM " + TABLE
                        + " WHERE username=? AND item_id=? AND episode_id=?",
                (rs, i) -> {
                    Map<String, Object> m = blank(itemId, ep);
                    m.put("positionSec", rs.getInt("position_sec"));
                    m.put("completed", rs.getInt("completed") == 1);
                    Timestamp ts = rs.getTimestamp("updated_at");
                    if (ts != null) m.put("updatedAt", ts.toLocalDateTime().toString().replace('T', ' '));
                    return m;
                },
                username.trim(), itemId, ep);
        return rows == null || rows.isEmpty() ? empty : rows.get(0);
    }

    public static Map<String, Object> save(
            String username, long itemId, long episodeId, int positionSec, boolean completed) {
        if (!enabled) throw new IllegalStateException("未开放播放进度");
        if (username == null || username.isBlank()) throw new IllegalArgumentException("未登录");
        if (itemId <= 0) throw new IllegalArgumentException("片单无效");
        ensureTable();
        String u = username.trim();
        long ep = episodeId < 0 ? 0 : episodeId;
        int pos = Math.max(0, positionSec);
        int done = completed ? 1 : 0;
        db().update(
                "INSERT INTO " + TABLE + " (username,item_id,episode_id,position_sec,completed,updated_at)"
                        + " VALUES (?,?,?,?,?,?) ON DUPLICATE KEY UPDATE"
                        + " position_sec=VALUES(position_sec), completed=VALUES(completed), updated_at=VALUES(updated_at)",
                u, itemId, ep, pos, done, Timestamp.valueOf(LocalDateTime.now()));
        return get(u, itemId, ep);
    }

    private static Map<String, Object> blank(long itemId, long episodeId) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("itemId", itemId);
        m.put("episodeId", episodeId);
        m.put("positionSec", 0);
        m.put("completed", false);
        return m;
    }
}
