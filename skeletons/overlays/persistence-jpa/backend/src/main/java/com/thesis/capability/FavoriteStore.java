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
    private static boolean commentReportOn = false;
    private static boolean groupsEnabled = false;
    private static int reportHandleDays = 0;

    private FavoriteStore() {}

    public static void configure(boolean on) {
        enabled = on;
        if (enabled) ensureTable();
    }

    /** C-06：收藏夹分组命名 + 公开/私密（无列时写库硬失败）。 */
    public static void configureGroups(boolean on) {
        groupsEnabled = on;
        if (enabled && groupsEnabled) ensureGroupColumns();
    }

    public static boolean groupsEnabled() {
        return groupsEnabled;
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

    /** C-08：允许举报评论（target_type=comment）。 */
    public static void configureCommentReport(boolean on) {
        commentReportOn = on;
        if (commentReportOn && reportEnabled) ensureReportTable();
    }

    public static void configureReportHandleDays(int days) {
        reportHandleDays = Math.max(0, days);
        if (reportEnabled && reportHandleDays > 0) ensureReportDeadlineColumn();
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
                            + "group_name VARCHAR(64) NOT NULL DEFAULT '',"
                            + "is_public TINYINT NOT NULL DEFAULT 0,"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "UNIQUE KEY uk_fav_user_item (username, item_id),"
                            + "KEY idx_fav_user (username, id),"
                            + "KEY idx_fav_public (is_public, username, id)"
                            + ")");
        } catch (Exception ignored) {
        }
        if (groupsEnabled) ensureGroupColumns();
    }

    private static void ensureGroupColumns() {
        try {
            db().execute(
                    "ALTER TABLE " + TABLE + " ADD COLUMN group_name VARCHAR(64) NOT NULL DEFAULT ''");
        } catch (Exception ignored) {
        }
        try {
            db().execute(
                    "ALTER TABLE " + TABLE + " ADD COLUMN is_public TINYINT NOT NULL DEFAULT 0");
        } catch (Exception ignored) {
        }
    }

    private static boolean hasGroupColumns() {
        try {
            db().queryForObject(
                    "SELECT group_name FROM " + TABLE + " WHERE 1=0", String.class);
            return true;
        } catch (Exception e) {
            return false;
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
                            + "handle_deadline_at DATETIME NULL,"
                            + "KEY idx_creport_status (status, id),"
                            + "KEY idx_creport_target (target_type, target_id)"
                            + ")");
        } catch (Exception ignored) {
        }
        ensureReportDeadlineColumn();
    }

    private static void ensureReportDeadlineColumn() {
        try {
            db().execute("ALTER TABLE " + REPORT_TABLE + " ADD COLUMN handle_deadline_at DATETIME NULL");
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
        return page(username, page, size, null);
    }

    public static Map<String, Object> page(String username, int page, int size, String groupName) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        boolean groups = groupsEnabled && hasGroupColumns();
        String g = groupName == null ? "" : groupName.trim();
        String where = " WHERE username=?";
        List<Object> args = new ArrayList<>();
        args.add(username);
        if (groups && !g.isBlank()) {
            where += " AND group_name=?";
            args.add(g);
        }
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM " + TABLE + where, Integer.class, args.toArray());
        String cols = groups
                ? "item_id, created_at, group_name, is_public"
                : "item_id, created_at";
        args.add(size);
        args.add((page - 1) * size);
        List<Map<String, Object>> rows = db().query(
                "SELECT " + cols + " FROM " + TABLE + where + " ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    long itemId = rs.getLong("item_id");
                    m.put("itemId", itemId);
                    Timestamp ts = rs.getTimestamp("created_at");
                    m.put("createdAt", ts == null ? null : ts.toLocalDateTime().format(FMT));
                    if (groups) {
                        m.put("groupName", rs.getString("group_name"));
                        m.put("isPublic", rs.getInt("is_public") == 1);
                    }
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
                args.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", rows == null ? List.of() : rows);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    /** 更新收藏分组与公开性（须开 CONTENT_FAVORITE_GROUP）。 */
    public static Map<String, Object> updateMeta(
            String username, long itemId, String groupName, Boolean isPublic) {
        require();
        if (!groupsEnabled) throw new IllegalStateException("收藏分组功能暂不可用");
        if (!hasGroupColumns()) {
            throw new IllegalStateException("系统未配置收藏分组字段，无法保存");
        }
        if (itemId <= 0) throw new IllegalArgumentException("对象不存在");
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM " + TABLE + " WHERE username=? AND item_id=?",
                Integer.class, username, itemId);
        if (n == null || n <= 0) throw new IllegalStateException("尚未收藏该内容");
        String g = groupName == null ? "" : groupName.trim();
        if (g.length() > 64) g = g.substring(0, 64);
        if (isPublic != null) {
            db().update(
                    "UPDATE " + TABLE + " SET group_name=?, is_public=? WHERE username=? AND item_id=?",
                    g, isPublic ? 1 : 0, username, itemId);
        } else {
            db().update(
                    "UPDATE " + TABLE + " SET group_name=? WHERE username=? AND item_id=?",
                    g, username, itemId);
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("itemId", itemId);
        out.put("groupName", g);
        if (isPublic != null) out.put("isPublic", isPublic);
        return out;
    }

    /** 他人公开歌单/片单（只读列表）。 */
    public static Map<String, Object> pagePublic(String ownerUsername, int page, int size) {
        require();
        if (!groupsEnabled) throw new IllegalStateException("收藏分组功能暂不可用");
        if (!hasGroupColumns()) {
            throw new IllegalStateException("系统未配置收藏分组字段，无法查看公开歌单");
        }
        String owner = ownerUsername == null ? "" : ownerUsername.trim();
        if (owner.isBlank()) throw new IllegalArgumentException("请指定用户");
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM " + TABLE + " WHERE username=? AND is_public=1",
                Integer.class, owner);
        List<Map<String, Object>> rows = db().query(
                "SELECT item_id, created_at, group_name, is_public FROM " + TABLE
                        + " WHERE username=? AND is_public=1 ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    long itemId = rs.getLong("item_id");
                    m.put("itemId", itemId);
                    m.put("ownerUsername", owner);
                    m.put("groupName", rs.getString("group_name"));
                    m.put("isPublic", true);
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
                owner, size, (page - 1) * size);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", rows == null ? List.of() : rows);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        out.put("ownerUsername", owner);
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
        if (!likeEnabled) return;
        String item = ArchiveStore.itemTable();
        if (item == null || item.isBlank()) {
            throw new IllegalStateException("系统未配置对象表，无法更新点赞热度");
        }
        try {
            db().update(
                    "UPDATE `" + item + "` SET like_count = GREATEST(0, COALESCE(like_count,0) + ?) WHERE id=?",
                    delta, itemId);
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置点赞计数字段，无法更新热度", e);
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
        if ("comment".equals(type) || "item_comment".equals(type)) {
            if (!commentReportOn) throw new IllegalArgumentException("未开放评论举报");
            type = "comment";
        } else if (!"archive".equals(type) && !"ticket".equals(type)) {
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
        if ("comment".equals(type) && com.thesis.service.ItemCommentStore.get(targetId) == null) {
            throw new IllegalArgumentException("评论不存在");
        }
        Integer dup = db().queryForObject(
                "SELECT COUNT(*) FROM " + REPORT_TABLE
                        + " WHERE username=? AND target_type=? AND target_id=? AND status='pending'",
                Integer.class, username, type, targetId);
        if (dup != null && dup > 0) {
            throw new IllegalStateException("您已提交过该内容的举报，请等待处理");
        }
        String finalNote = note;
        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        Timestamp deadline = reportHandleDays > 0
                ? Timestamp.valueOf(LocalDateTime.now().plusDays(reportHandleDays))
                : null;
        KeyHolder kh = new GeneratedKeyHolder();
        final Timestamp deadlineFinal = deadline;
        db().update(con -> {
            if (deadlineFinal != null) {
                PreparedStatement ps = con.prepareStatement(
                        "INSERT INTO " + REPORT_TABLE
                                + " (username,target_type,target_id,reason,status,created_at,handle_deadline_at) "
                                + "VALUES (?,?,?,?,?,?,?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setString(1, username);
                ps.setString(2, type);
                ps.setLong(3, targetId);
                ps.setString(4, finalNote);
                ps.setString(5, "pending");
                ps.setTimestamp(6, now);
                ps.setTimestamp(7, deadlineFinal);
                return ps;
            }
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO " + REPORT_TABLE
                            + " (username,target_type,target_id,reason,status,created_at) VALUES (?,?,?,?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, username);
            ps.setString(2, type);
            ps.setLong(3, targetId);
            ps.setString(4, finalNote);
            ps.setString(5, "pending");
            ps.setTimestamp(6, now);
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
        Map<String, Object> done = getReport(reportId);
        try {
            String reporter = done == null ? "" : String.valueOf(done.get("username"));
            if (reporter != null && !reporter.isBlank() && !"null".equals(reporter)) {
                String tip = note.isBlank()
                        ? ("ignore".equals(act) ? "已忽略该举报。" : "已按举报处理相关内容。")
                        : note;
                com.thesis.service.MessageStore.send(
                        reporter,
                        "举报处理结果",
                        tip,
                        "content_report",
                        Long.valueOf(reportId));
            }
        } catch (Exception ignored) {
        }
        return done;
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
        try {
            Timestamp dl = rs.getTimestamp("handle_deadline_at");
            m.put("handleDeadlineAt", dl == null ? null : dl.toLocalDateTime().format(FMT));
            boolean pending = "pending".equals(String.valueOf(m.get("status")));
            m.put("overdue", pending && dl != null && dl.toLocalDateTime().isBefore(LocalDateTime.now()));
        } catch (Exception ignored) {
            m.put("handleDeadlineAt", null);
            m.put("overdue", false);
        }
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
