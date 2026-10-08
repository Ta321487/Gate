package com.thesis.capability;

import com.thesis.config.JdbcSupport;
import com.thesis.service.MessageStore;
import org.springframework.jdbc.core.JdbcTemplate;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** T-09：缺货到货订阅（stock_notify）+ 补货站内信。 */
public final class StockNotifyStore {

    private static final String TABLE = "stock_notify";
    private static boolean tableReady;

    private StockNotifyStore() {}

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    private static boolean ready() {
        if (tableReady) return true;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name=?",
                    Integer.class,
                    TABLE);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    public static Map<String, Object> subscribe(String username, long itemId) {
        if (!ready()) throw new IllegalStateException("系统未配置到货通知");
        String u = username == null ? "" : username.trim();
        if (u.isBlank()) throw new IllegalArgumentException("请先登录");
        if (itemId <= 0) throw new IllegalArgumentException("商品无效");
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) throw new IllegalArgumentException("商品不存在");
        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        db().update(
                "INSERT INTO " + TABLE + " (item_id, username, created_at, notified_at) VALUES (?,?,?,NULL) "
                        + "ON DUPLICATE KEY UPDATE notified_at=NULL, created_at=?",
                itemId, u, now, now);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("itemId", itemId);
        out.put("subscribed", true);
        return out;
    }

    public static boolean isSubscribed(String username, long itemId) {
        if (!ready() || itemId <= 0) return false;
        String u = username == null ? "" : username.trim();
        if (u.isBlank()) return false;
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM " + TABLE + " WHERE item_id=? AND username=? AND notified_at IS NULL",
                Integer.class, itemId, u);
        return n != null && n > 0;
    }

    /** 补货后通知未通知的订阅者。 */
    public static int notifyRestock(long itemId) {
        if (!ready() || itemId <= 0) return 0;
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) return 0;
        int stock = item.get("stock") instanceof Number n ? n.intValue() : 0;
        if (stock <= 0) return 0;
        String title = String.valueOf(item.getOrDefault("title", "")).trim();
        if (title.isBlank()) title = "商品#" + itemId;
        List<String> users = db().query(
                "SELECT username FROM " + TABLE + " WHERE item_id=? AND notified_at IS NULL",
                (rs, i) -> rs.getString(1),
                itemId);
        if (users == null || users.isEmpty()) return 0;
        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        int sent = 0;
        for (String u : users) {
            if (u == null || u.isBlank()) continue;
            try {
                MessageStore.send(
                        u,
                        "到货提醒",
                        "「" + title + "」已有货，可前往选购。",
                        "archive",
                        itemId);
                db().update(
                        "UPDATE " + TABLE + " SET notified_at=? WHERE item_id=? AND username=? AND notified_at IS NULL",
                        now, itemId, u);
                sent++;
            } catch (Exception ignored) {
            }
        }
        return sent;
    }

    public static List<Map<String, Object>> listMine(String username) {
        if (!ready()) return List.of();
        String u = username == null ? "" : username.trim();
        if (u.isBlank()) return List.of();
        List<Map<String, Object>> rows = db().query(
                "SELECT item_id, created_at, notified_at FROM " + TABLE
                        + " WHERE username=? ORDER BY id DESC LIMIT 50",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("itemId", rs.getLong("item_id"));
                    m.put("createdAt", rs.getTimestamp("created_at") == null
                            ? null : rs.getTimestamp("created_at").toLocalDateTime().toString());
                    m.put("notifiedAt", rs.getTimestamp("notified_at") == null
                            ? null : rs.getTimestamp("notified_at").toLocalDateTime().toString());
                    m.put("pending", rs.getTimestamp("notified_at") == null);
                    return m;
                },
                u);
        return rows == null ? new ArrayList<>() : rows;
    }
}
