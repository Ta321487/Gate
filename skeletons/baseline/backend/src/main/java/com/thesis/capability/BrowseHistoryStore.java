package com.thesis.capability;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 能力 browse_history：最近浏览足迹（user_browse_history）。 */
public final class BrowseHistoryStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final String TABLE = "user_browse_history";
    private static boolean enabled = false;
    private static int limit = 20;

    private BrowseHistoryStore() {}

    public static void configure(boolean on, int maxKeep) {
        enabled = on;
        limit = maxKeep > 0 ? Math.min(maxKeep, 50) : 20;
        if (enabled) ensureTable();
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
                            + "viewed_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "UNIQUE KEY uk_browse_user_item (username, item_id),"
                            + "KEY idx_browse_user_time (username, viewed_at)"
                            + ")");
        } catch (Exception ignored) {
        }
    }

    public static void touch(String username, long itemId) {
        if (!enabled || username == null || username.isBlank() || itemId <= 0) return;
        if (ArchiveStore.getItemRaw(itemId) == null) return;
        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM " + TABLE + " WHERE username=? AND item_id=?",
                Integer.class, username, itemId);
        if (n != null && n > 0) {
            db().update(
                    "UPDATE " + TABLE + " SET viewed_at=? WHERE username=? AND item_id=?",
                    now, username, itemId);
        } else {
            db().update(
                    "INSERT INTO " + TABLE + " (username,item_id,viewed_at) VALUES (?,?,?)",
                    username, itemId, now);
        }
        trim(username);
    }

    private static void trim(String username) {
        try {
            List<Long> ids = db().query(
                    "SELECT id FROM " + TABLE + " WHERE username=? ORDER BY viewed_at DESC",
                    (rs, i) -> rs.getLong(1),
                    username);
            if (ids == null || ids.size() <= limit) return;
            for (int i = limit; i < ids.size(); i++) {
                db().update("DELETE FROM " + TABLE + " WHERE id=?", ids.get(i));
            }
        } catch (Exception ignored) {
        }
    }

    public static Map<String, Object> page(String username, int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM " + TABLE + " WHERE username=?", Integer.class, username);
        List<Map<String, Object>> rows = db().query(
                "SELECT item_id, viewed_at FROM " + TABLE
                        + " WHERE username=? ORDER BY viewed_at DESC LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    long itemId = rs.getLong("item_id");
                    m.put("itemId", itemId);
                    Timestamp ts = rs.getTimestamp("viewed_at");
                    m.put("viewedAt", ts == null ? null : ts.toLocalDateTime().format(FMT));
                    Map<String, Object> item = ArchiveStore.getItem(itemId);
                    if (item != null) {
                        m.putAll(item);
                        m.put("id", itemId);
                    } else {
                        m.put("id", itemId);
                        m.put("title", "已下架");
                    }
                    return m;
                },
                username, size, (page - 1) * size);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", rows == null ? List.of() : rows);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    public static boolean clear(String username) {
        require();
        return db().update("DELETE FROM " + TABLE + " WHERE username=?", username) >= 0;
    }

    private static void require() {
        if (!enabled) throw new IllegalStateException("浏览历史暂不可用");
    }
}
