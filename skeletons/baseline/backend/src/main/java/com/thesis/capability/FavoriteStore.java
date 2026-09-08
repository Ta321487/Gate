package com.thesis.capability;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 能力 favorites：即时收藏夹（user_favorite）；E-03 同文件扩展点赞 / 举报。 */
public final class FavoriteStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final String TABLE = "user_favorite";
    private static final String LIKE_TABLE = "user_post_like";
    private static final String REPORT_TABLE = "content_report";
    private static boolean enabled = false;
    private static boolean likeEnabled = false;
    private static boolean reportEnabled = false;

    private FavoriteStore() {}

    public static void configure(boolean on) {
        enabled = on;
        if (enabled) ensureTable();
    }

    public static void configureLike(boolean on) {
        likeEnabled = on;
        if (likeEnabled) {
            ensureLikeTable();
            ensureLikeCountColumn();
        }
    }

    public static void configureReport(boolean on) {
        reportEnabled = on;
        if (reportEnabled) ensureReportTable();
    }

    public static boolean enabled() {
        return enabled;
    }

    public static boolean likeEnabled() {
        return likeEnabled;
    }

    public static boolean reportEnabled() {
        return reportEnabled;
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

    private static void ensureLikeTable() {
        try {
            db().execute(
                    "CREATE TABLE IF NOT EXISTS " + LIKE_TABLE + " ("
                            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
                            + "username VARCHAR(64) NOT NULL,"
                            + "item_id BIGINT NOT NULL,"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "UNIQUE KEY uk_like_user_item (username, item_id),"
                            + "KEY idx_like_item (item_id)"
                            + ")");
        } catch (Exception ignored) {
        }
    }

    private static void ensureLikeCountColumn() {
        String item = ArchiveStore.itemTable();
        if (item == null || item.isBlank()) return;
        try {
            db().execute("ALTER TABLE `" + item + "` ADD COLUMN `like_count` INT NOT NULL DEFAULT 0");
        } catch (Exception ignored) {
            // 列已存在
        }
    }

    private static void ensureReportTable() {
        try {
            db().execute(
                    "CREATE TABLE IF NOT EXISTS " + REPORT_TABLE + " ("
                            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
                            + "username VARCHAR(64) NOT NULL,"
                            + "target_type VARCHAR(32) NOT NULL DEFAULT 'archive',"
                            + "target_id BIGINT NOT NULL,"
                            + "reason VARCHAR(512) NOT NULL,"
                            + "status VARCHAR(32) NOT NULL DEFAULT 'pending',"
                            + "handler VARCHAR(64) DEFAULT '',"
                            + "handle_note VARCHAR(512) DEFAULT '',"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "handled_at DATETIME NULL,"
                            + "KEY idx_creport_status (status, id),"
                            + "KEY idx_creport_target (target_type, target_id)"
                            + ")");
        } catch (Exception ignored) {
        }
    }

    public static boolean toggle(String username, long itemId) {
        require();
        if (ArchiveStore.getItemRaw(itemId) == null) {
            throw new IllegalArgumentException("对象不存在");
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

    /** @return true=已赞，false=取消赞 */
    public static boolean toggleLike(String username, long itemId) {
        requireLike();
        if (ArchiveStore.getItemRaw(itemId) == null) {
            throw new IllegalArgumentException("对象不存在");
        }
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM " + LIKE_TABLE + " WHERE username=? AND item_id=?",
                Integer.class, username, itemId);
        if (n != null && n > 0) {
            db().update("DELETE FROM " + LIKE_TABLE + " WHERE username=? AND item_id=?", username, itemId);
            bumpLikeCount(itemId, -1);
            return false;
        }
        db().update(
                "INSERT INTO " + LIKE_TABLE + " (username,item_id,created_at) VALUES (?,?,?)",
                username, itemId, Timestamp.valueOf(LocalDateTime.now()));
        bumpLikeCount(itemId, 1);
        return true;
    }

    private static void bumpLikeCount(long itemId, int delta) {
        String item = ArchiveStore.itemTable();
        if (item == null || item.isBlank()) return;
        try {
            db().update(
                    "UPDATE `" + item + "` SET like_count = GREATEST(0, COALESCE(like_count,0) + ?) WHERE id=?",
                    delta, itemId);
        } catch (Exception ignored) {
            // 无 like_count 列时忽略计数
        }
    }

    public static boolean isLiked(String username, long itemId) {
        if (!likeEnabled || username == null || username.isBlank() || itemId <= 0) return false;
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM " + LIKE_TABLE + " WHERE username=? AND item_id=?",
                Integer.class, username, itemId);
        return n != null && n > 0;
    }

    public static List<Long> likedIdsOf(String username) {
        if (!likeEnabled || username == null || username.isBlank()) return List.of();
        List<Long> ids = db().query(
                "SELECT item_id FROM " + LIKE_TABLE + " WHERE username=?",
                (rs, i) -> rs.getLong(1),
                username);
        return ids == null ? List.of() : new ArrayList<>(ids);
    }

    public static Map<String, Object> submitReport(
            String username, String targetType, long targetId, String reason) {
        requireReport();
        String type = targetType == null || targetType.isBlank() ? "archive" : targetType.trim();
        if (!"archive".equals(type) && !"ticket".equals(type)) {
            throw new IllegalArgumentException("不支持的举报对象类型");
        }
        String note = reason == null ? "" : reason.trim();
        if (note.isBlank()) throw new IllegalStateException("请填写举报理由");
        if (note.length() > 512) note = note.substring(0, 512);
        if ("archive".equals(type) && ArchiveStore.getItemRaw(targetId) == null) {
            throw new IllegalArgumentException("对象不存在");
        }
        if ("ticket".equals(type) && TicketStore.get(targetId) == null) {
            throw new IllegalArgumentException("单据不存在");
        }
        Integer dup = db().queryForObject(
                "SELECT COUNT(*) FROM " + REPORT_TABLE
                        + " WHERE username=? AND target_type=? AND target_id=? AND status='pending'",
                Integer.class, username, type, targetId);
        if (dup != null && dup > 0) {
            throw new IllegalStateException("您已提交过该内容的举报，请等待处理");
        }
        String finalNote = note;
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO " + REPORT_TABLE
                            + " (username,target_type,target_id,reason,status,created_at) VALUES (?,?,?,?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, username);
            ps.setString(2, type);
            ps.setLong(3, targetId);
            ps.setString(4, finalNote);
            ps.setString(5, "pending");
            ps.setTimestamp(6, Timestamp.valueOf(LocalDateTime.now()));
            return ps;
        }, kh);
        Number key = kh.getKey();
        long id = key == null ? 0L : key.longValue();
        return getReport(id);
    }

    public static Map<String, Object> pageReports(String status, int page, int size) {
        requireReport();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        String st = status == null ? "" : status.trim();
        String where = st.isBlank() ? "" : " WHERE status=?";
        Integer total = st.isBlank()
                ? db().queryForObject("SELECT COUNT(*) FROM " + REPORT_TABLE, Integer.class)
                : db().queryForObject(
                        "SELECT COUNT(*) FROM " + REPORT_TABLE + where, Integer.class, st);
        List<Map<String, Object>> rows = st.isBlank()
                ? db().query(
                        "SELECT * FROM " + REPORT_TABLE + " ORDER BY id DESC LIMIT ? OFFSET ?",
                        (rs, i) -> mapReport(rs),
                        size, (page - 1) * size)
                : db().query(
                        "SELECT * FROM " + REPORT_TABLE + where + " ORDER BY id DESC LIMIT ? OFFSET ?",
                        (rs, i) -> mapReport(rs),
                        st, size, (page - 1) * size);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", rows == null ? List.of() : rows);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    /**
     * @param action ignore | takedown | takedown_mute（下架并禁言作者，需 post_mute）
     * @param muteDays 禁言天数；takedown_mute 默认 7；&lt;=0 时不禁言
     */
    public static Map<String, Object> resolveReport(
            long reportId, String action, String handler, String handleNote) {
        return resolveReport(reportId, action, handler, handleNote, 0);
    }

    public static Map<String, Object> resolveReport(
            long reportId, String action, String handler, String handleNote, int muteDays) {
        requireReport();
        Map<String, Object> m = getReport(reportId);
        if (m == null) throw new IllegalArgumentException("举报不存在");
        if (!"pending".equals(String.valueOf(m.get("status")))) {
            throw new IllegalStateException("该举报已处理");
        }
        String act = action == null ? "" : action.trim();
        boolean withMute = "takedown_mute".equals(act);
        if (!"ignore".equals(act) && !"takedown".equals(act) && !withMute) {
            throw new IllegalStateException("处理方式须为忽略、下架或下架并禁言");
        }
        String note = handleNote == null ? "" : handleNote.trim();
        if (note.length() > 512) note = note.substring(0, 512);
        String newStatus = "ignore".equals(act) ? "ignored" : "takedown";
        if ("takedown".equals(act) || withMute) {
            String type = String.valueOf(m.get("targetType"));
            long tid = toLong(m.get("targetId"));
            if ("archive".equals(type)) {
                boolean ok = ArchiveStore.deleteItem(tid);
                if (!ok) {
                    ArchiveStore.updateItem(tid, Map.of("status", "unavailable"));
                }
            } else if ("ticket".equals(type)) {
                TicketStore.hideForReport(tid, note.isBlank() ? "举报下架" : note);
            }
            if (withMute) {
                muteContentAuthor(type, tid, muteDays > 0 ? muteDays : 7, note);
            }
        }
        db().update(
                "UPDATE " + REPORT_TABLE
                        + " SET status=?, handler=?, handle_note=?, handled_at=NOW() WHERE id=?",
                newStatus,
                handler == null ? "" : handler,
                note,
                reportId);
        return getReport(reportId);
    }

    /** 对举报对象作者设禁言（E-12 联动）。 */
    private static void muteContentAuthor(String targetType, long targetId, int days, String note) {
        if (!com.thesis.service.UserStore.postMuteEnabled()) {
            throw new IllegalStateException("禁言功能暂不可用，请仅下架或先开启禁言能力");
        }
        String author = "";
        if ("archive".equals(targetType)) {
            Map<String, Object> item = ArchiveStore.getItemRaw(targetId);
            if (item != null) {
                Object ou = item.get("ownerUsername");
                if (ou == null || String.valueOf(ou).isBlank()) {
                    ou = item.get("author");
                }
                author = ou == null ? "" : String.valueOf(ou).trim();
            }
        } else if ("ticket".equals(targetType)) {
            Map<String, Object> t = TicketStore.get(targetId);
            if (t != null && t.get("username") != null) {
                author = String.valueOf(t.get("username")).trim();
            }
        }
        if (author.isBlank()) {
            throw new IllegalStateException("无法定位内容作者，未能禁言");
        }
        String tip = note == null || note.isBlank() ? "举报处置禁言" : note;
        Map<String, Object> muted = com.thesis.service.UserStore.setPostMuteDays(author, days);
        muted.put("_muteNote", tip);
    }

    private static Map<String, Object> getReport(long id) {
        try {
            return db().queryForObject(
                    "SELECT * FROM " + REPORT_TABLE + " WHERE id=?",
                    (rs, i) -> mapReport(rs),
                    id);
        } catch (Exception e) {
            return null;
        }
    }

    private static Map<String, Object> mapReport(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("targetType", rs.getString("target_type"));
        m.put("targetId", rs.getLong("target_id"));
        m.put("reason", rs.getString("reason"));
        m.put("status", rs.getString("status"));
        m.put("handler", rs.getString("handler"));
        m.put("handleNote", rs.getString("handle_note"));
        Timestamp c = rs.getTimestamp("created_at");
        m.put("createdAt", c == null ? null : c.toLocalDateTime().format(FMT));
        Timestamp h = rs.getTimestamp("handled_at");
        m.put("handledAt", h == null ? null : h.toLocalDateTime().format(FMT));
        return m;
    }

    private static long toLong(Object o) {
        if (o instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(String.valueOf(o));
        } catch (Exception e) {
            return 0L;
        }
    }

    private static void require() {
        if (!enabled) throw new IllegalStateException("收藏功能暂不可用");
    }

    private static void requireLike() {
        if (!likeEnabled) throw new IllegalStateException("点赞功能暂不可用");
    }

    private static void requireReport() {
        if (!reportEnabled) throw new IllegalStateException("举报功能暂不可用");
    }
}
