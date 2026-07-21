package com.thesis.capability;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 能力 favorites：交易域收藏夹（user_favorite）。 */
public final class FavoriteStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final String TABLE = "user_favorite";
    private static boolean enabled = false;

    private FavoriteStore() {}

    public static void configure(boolean on) {
        enabled = on;
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
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "UNIQUE KEY uk_fav_user_item (username, item_id),"
                            + "KEY idx_fav_user (username, id)"
                            + ")");
        } catch (Exception ignored) {
        }
    }

    public static boolean toggle(String username, long itemId) {
        require();
        if (ArchiveStore.getItemRaw(itemId) == null) {
            throw new IllegalArgumentException("商品不存在");
        }
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM " + TABLE + " WHERE username=? AND item_id=?",
                Integer.class, username, itemId);
        if (n != null && n > 0) {
            db().update("DELETE FROM " + TABLE + " WHERE username=? AND item_id=?", username, itemId);
            return false;
        }
        db().update(
                "INSERT INTO " + TABLE + " (username,item_id,created_at) VALUES (?,?,?)",
                username, itemId, Timestamp.valueOf(LocalDateTime.now()));
        return true;
    }

    public static boolean isFav(String username, long itemId) {
        if (!enabled || username == null || username.isBlank() || itemId <= 0) return false;
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM " + TABLE + " WHERE username=? AND item_id=?",
                Integer.class, username, itemId);
        return n != null && n > 0;
    }

    public static Map<String, Object> page(String username, int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM " + TABLE + " WHERE username=?", Integer.class, username);
        List<Map<String, Object>> rows = db().query(
                "SELECT item_id, created_at FROM " + TABLE
                        + " WHERE username=? ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    long itemId = rs.getLong("item_id");
                    m.put("itemId", itemId);
                    Timestamp ts = rs.getTimestamp("created_at");
                    m.put("createdAt", ts == null ? null : ts.toLocalDateTime().format(FMT));
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

    public static List<Long> idsOf(String username) {
        if (!enabled || username == null || username.isBlank()) return List.of();
        List<Long> ids = db().query(
                "SELECT item_id FROM " + TABLE + " WHERE username=?",
                (rs, i) -> rs.getLong(1),
                username);
        return ids == null ? List.of() : new ArrayList<>(ids);
    }

    private static void require() {
        if (!enabled) throw new IllegalStateException("收藏功能暂不可用");
    }
}
