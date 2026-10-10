package com.thesis.service;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 文库下载台账：资料附件、演示权限、下载记录；C-07 加厚章节/版本/限额/审核/标签/纠错侵权。
 */
public class DoclibStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final Set<String> ACCESS = Set.of("public", "login", "staff");
    private static final Set<String> FEEDBACK_KINDS = Set.of("correction", "infringement");
    private static boolean enabled;
    private static boolean chapterOn;
    private static boolean feedbackOn;
    private static boolean tagCloudOn;
    private static boolean downloadGateOn;
    private static boolean pointsDownloadOn;
    private static int dailyDownloadLimit;
    private static Boolean tableReady;

    private DoclibStore() {}

    public static void configure(boolean on) {
        enabled = on;
        tableReady = null;
    }

    public static void configureThicken(
            boolean chapter, boolean feedback, boolean tagCloud, boolean downloadGate, int dailyLimit) {
        chapterOn = chapter;
        feedbackOn = feedback;
        tagCloudOn = tagCloud;
        downloadGateOn = downloadGate;
        dailyDownloadLimit = Math.max(0, dailyLimit);
        if (chapter) ensureChapterTables();
        if (feedback) ensureFeedbackTable();
        if (tagCloud) ensureTagTables();
        if (downloadGate) ensureAuditTable();
    }

    /** C-08：挂 points 时下载前扣积分。 */
    public static void configurePointsDownload(boolean on) {
        pointsDownloadOn = on;
    }

    public static boolean enabled() {
        return enabled;
    }

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    public static boolean ready() {
        if (!enabled) return false;
        if (tableReady != null) return tableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='download_log'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static void require() {
        if (!ready()) throw new IllegalStateException("文库功能暂不可用");
    }

    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        String s = String.valueOf(o);
        return s.isBlank() ? null : s;
    }

    private static String clip(String s, int max) {
        if (s == null) return "";
        String t = s.trim();
        return t.length() <= max ? t : t.substring(0, max);
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static Long toLong(Object o) {
        if (o == null || String.valueOf(o).isBlank()) return null;
        return Long.parseLong(String.valueOf(o));
    }

    private static int toInt(Object o, int def) {
        if (o == null || String.valueOf(o).isBlank()) return def;
        try {
            return Integer.parseInt(String.valueOf(o));
        } catch (NumberFormatException e) {
            return def;
        }
    }

    private static boolean toBool(Object o) {
        if (o == null) return false;
        if (o instanceof Boolean b) return b;
        String s = String.valueOf(o).trim();
        return "1".equals(s) || "true".equalsIgnoreCase(s) || "yes".equalsIgnoreCase(s);
    }

    private static Map<String, Object> pageOut(List<?> list, Integer total, int page, int size) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    private static boolean hasCol(String table, String col) {
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.columns "
                            + "WHERE table_schema=DATABASE() AND table_name=? AND column_name=?",
                    Integer.class, table, col);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    private static void ensureChapterTables() {
        try {
            db().execute(
                    "CREATE TABLE IF NOT EXISTS doc_chapter ("
                            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
                            + "item_id BIGINT NOT NULL,"
                            + "title VARCHAR(128) NOT NULL,"
                            + "anchor VARCHAR(64) NOT NULL DEFAULT '',"
                            + "sort_ord INT NOT NULL DEFAULT 0,"
                            + "KEY idx_dc_item (item_id, sort_ord, id))");
            db().execute(
                    "CREATE TABLE IF NOT EXISTS doc_version ("
                            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
                            + "item_id BIGINT NOT NULL,"
                            + "version_no VARCHAR(32) NOT NULL,"
                            + "note VARCHAR(512) NOT NULL DEFAULT '',"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "KEY idx_dv_item (item_id, id))");
        } catch (Exception ignored) {
        }
    }

    private static void ensureFeedbackTable() {
        try {
            db().execute(
                    "CREATE TABLE IF NOT EXISTS doc_feedback ("
                            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
                            + "item_id BIGINT NOT NULL,"
                            + "username VARCHAR(64) NOT NULL,"
                            + "kind VARCHAR(16) NOT NULL,"
                            + "body VARCHAR(1000) NOT NULL,"
                            + "status VARCHAR(16) NOT NULL DEFAULT 'pending',"
                            + "handle_note VARCHAR(512) NOT NULL DEFAULT '',"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "handled_at DATETIME NULL,"
                            + "KEY idx_df_item (item_id, id),"
                            + "KEY idx_df_status (status, id))");
        } catch (Exception ignored) {
        }
    }

    private static void ensureAuditTable() {
        try {
            db().execute(
                    "CREATE TABLE IF NOT EXISTS doc_download_request ("
                            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
                            + "item_id BIGINT NOT NULL,"
                            + "username VARCHAR(64) NOT NULL,"
                            + "status VARCHAR(16) NOT NULL DEFAULT 'pending',"
                            + "handle_note VARCHAR(512) NOT NULL DEFAULT '',"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "handled_at DATETIME NULL,"
                            + "KEY idx_ddr_user (username, status, id),"
                            + "KEY idx_ddr_item (item_id, id))");
        } catch (Exception ignored) {
        }
    }

    private static void ensureTagTables() {
        try {
            db().execute(
                    "CREATE TABLE IF NOT EXISTS doc_tag ("
                            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
                            + "name VARCHAR(64) NOT NULL,"
                            + "use_count INT NOT NULL DEFAULT 0,"
                            + "UNIQUE KEY uk_dt_name (name))");
            db().execute(
                    "CREATE TABLE IF NOT EXISTS doc_item_tag ("
                            + "item_id BIGINT NOT NULL,"
                            + "tag_id BIGINT NOT NULL,"
                            + "PRIMARY KEY (item_id, tag_id),"
                            + "KEY idx_dit_tag (tag_id))");
        } catch (Exception ignored) {
        }
    }

    private static Map<String, Object> mapItem(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("title", rs.getString("title"));
        m.put("author", rs.getString("author"));
        m.put("isbn", rs.getString("isbn"));
        m.put("categoryId", rs.getObject("category_id"));
        m.put("stock", rs.getInt("stock"));
        m.put("status", rs.getString("status"));
        m.put("coverUrl", rs.getString("cover_url"));
        m.put("fileUrl", rs.getString("file_url"));
        m.put("accessLevel", rs.getString("access_level"));
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        try {
            m.put("previewUrl", rs.getString("preview_url"));
        } catch (Exception ignored) {
            m.put("previewUrl", "");
        }
        try {
            m.put("downloadRoles", rs.getString("download_roles"));
        } catch (Exception ignored) {
            m.put("downloadRoles", "");
        }
        try {
            m.put("trialReadNote", rs.getString("trial_read_note"));
        } catch (Exception ignored) {
            m.put("trialReadNote", "");
        }
        try {
            m.put("watermarkOn", rs.getInt("watermark_on") == 1);
        } catch (Exception ignored) {
            m.put("watermarkOn", false);
        }
        try {
            m.put("needsDownloadAudit", rs.getInt("needs_download_audit") == 1);
        } catch (Exception ignored) {
            m.put("needsDownloadAudit", false);
        }
        try {
            m.put("dailyDownloadLimit", rs.getInt("daily_download_limit"));
        } catch (Exception ignored) {
            m.put("dailyDownloadLimit", 0);
        }
        try {
            m.put("downloadCostPoints", rs.getInt("download_cost_points"));
        } catch (Exception ignored) {
            m.put("downloadCostPoints", 0);
        }
        try {
            m.put("downloadCount", rs.getInt("download_count"));
        } catch (Exception ignored) {
        }
        return m;
    }

    private static String itemSelectCols() {
        StringBuilder sb = new StringBuilder(
                "id, title, author, isbn, category_id, stock, status, cover_url, file_url, access_level, created_at");
        if (hasCol("doc_item", "preview_url")) sb.append(", preview_url");
        if (hasCol("doc_item", "download_roles")) sb.append(", download_roles");
        if (hasCol("doc_item", "trial_read_note")) sb.append(", trial_read_note");
        if (hasCol("doc_item", "watermark_on")) sb.append(", watermark_on");
        if (hasCol("doc_item", "needs_download_audit")) sb.append(", needs_download_audit");
        if (hasCol("doc_item", "daily_download_limit")) sb.append(", daily_download_limit");
        if (hasCol("doc_item", "download_cost_points")) sb.append(", download_cost_points");
        if (hasCol("doc_item", "download_count")) sb.append(", download_count");
        return sb.toString();
    }

    public static List<Map<String, Object>> listOpenItems(boolean admin) {
        require();
        String cols = itemSelectCols();
        String sql = "SELECT " + cols + " FROM doc_item WHERE status='available' ";
        if (!admin) {
            sql += "AND access_level IN ('public','login') ";
        }
        sql += "ORDER BY id DESC";
        return db().query(sql, (rs, i) -> mapItem(rs));
    }

    public static Map<String, Object> getItem(long id) {
        require();
        String cols = itemSelectCols();
        List<Map<String, Object>> rows = db().query(
                "SELECT " + cols + " FROM doc_item WHERE id=?",
                (rs, i) -> mapItem(rs),
                id);
        if (rows.isEmpty()) return null;
        Map<String, Object> item = rows.get(0);
        if (chapterOn) {
            item.put("chapters", listChapters(id));
            item.put("versions", listVersions(id));
        }
        if (tagCloudOn) {
            item.put("tags", listItemTags(id));
        }
        return item;
    }

    private static void assertAccess(Map<String, Object> item, boolean admin) {
        String level = str(item.get("accessLevel")).toLowerCase(Locale.ROOT);
        if (level.isBlank()) level = "login";
        if ("staff".equals(level) && !admin) {
            throw new IllegalStateException("该资料仅管理人员可下载");
        }
        if (!"available".equals(str(item.get("status")))) {
            throw new IllegalStateException("资料未开放");
        }
    }

    private static void assertDownloadRoles(Map<String, Object> item, boolean admin, String role) {
        if (!downloadGateOn || admin) return;
        String roles = str(item.get("downloadRoles"));
        if (roles.isBlank()) return;
        String r = role == null ? "" : role.trim().toLowerCase(Locale.ROOT);
        for (String part : roles.split("[,，;；\\s]+")) {
            if (part.isBlank()) continue;
            if (part.trim().equalsIgnoreCase(r) || "admin".equalsIgnoreCase(part.trim()) && admin) {
                return;
            }
        }
        throw new IllegalStateException("当前身份不能下载这份资料");
    }

    private static void assertQuota(String username, Map<String, Object> item, boolean admin) {
        if (!downloadGateOn || admin) return;
        int itemLimit = toInt(item.get("dailyDownloadLimit"), 0);
        int limit = itemLimit > 0 ? itemLimit : dailyDownloadLimit;
        if (limit <= 0) return;
        String day = LocalDate.now().toString();
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM download_log WHERE username=? AND DATE(downloaded_at)=?",
                Integer.class, username, day);
        if (n != null && n >= limit) {
            throw new IllegalStateException("今日下载次数已达上限，请明天再试");
        }
    }

    private static void assertOrRequestAudit(String username, long id, Map<String, Object> item, boolean admin) {
        if (!downloadGateOn || admin) return;
        if (!toBool(item.get("needsDownloadAudit"))) return;
        ensureAuditTable();
        Integer approved = db().queryForObject(
                "SELECT COUNT(*) FROM doc_download_request WHERE item_id=? AND username=? AND status='approved'",
                Integer.class, id, username);
        if (approved != null && approved > 0) return;
        Integer pending = db().queryForObject(
                "SELECT COUNT(*) FROM doc_download_request WHERE item_id=? AND username=? AND status='pending'",
                Integer.class, id, username);
        if (pending == null || pending == 0) {
            db().update(
                    "INSERT INTO doc_download_request(item_id, username, status) VALUES(?,?,'pending')",
                    id, username);
        }
        throw new IllegalStateException("下载申请已提交，请等待审核");
    }

    public static Map<String, Object> download(String username, long id, boolean admin) {
        return download(username, id, admin, admin ? "admin" : "user");
    }

    public static Map<String, Object> download(String username, long id, boolean admin, String role) {
        require();
        Map<String, Object> item = getItem(id);
        if (item == null) throw new IllegalArgumentException("资料不存在");
        assertAccess(item, admin);
        assertDownloadRoles(item, admin, role);
        assertQuota(username, item, admin);
        assertOrRequestAudit(username, id, item, admin);
        int cost = toInt(item.get("downloadCostPoints"), 0);
        if (pointsDownloadOn && cost > 0 && !admin) {
            com.thesis.capability.LoyaltyStore.spendPoints(
                    username, cost, "文库下载扣积分 −" + cost, "doclib", id);
        }
        String url = str(item.get("fileUrl"));
        if (url.isBlank()) throw new IllegalStateException("未配置附件地址");
        db().update("INSERT INTO download_log(item_id, username) VALUES(?,?)", id, username);
        try {
            db().update(
                    "UPDATE doc_item SET download_count=IFNULL(download_count,0)+1 WHERE id=?",
                    id);
        } catch (Exception ignored) {
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("itemId", id);
        out.put("title", item.get("title"));
        out.put("url", url);
        out.put("accessLevel", item.get("accessLevel"));
        out.put("previewUrl", item.get("previewUrl"));
        out.put("watermarkOn", item.get("watermarkOn"));
        out.put("trialReadNote", item.get("trialReadNote"));
        return out;
    }

    public static Map<String, Object> pageMine(String username, int page, int size) {
        require();
        int p = Math.max(1, page);
        int s = Math.min(100, Math.max(1, size));
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM download_log WHERE username=?", Integer.class, username);
        List<Map<String, Object>> list = db().query(
                "SELECT l.id, l.item_id, l.downloaded_at, d.title "
                        + "FROM download_log l JOIN doc_item d ON d.id=l.item_id "
                        + "WHERE l.username=? ORDER BY l.id DESC LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("itemId", rs.getLong("item_id"));
                    m.put("title", rs.getString("title"));
                    m.put("downloadedAt", fmt(rs.getTimestamp("downloaded_at")));
                    return m;
                },
                username, s, (p - 1) * s);
        return pageOut(list, total, p, s);
    }

    public static Map<String, Object> pageLogsAdmin(int page, int size, Long itemId) {
        require();
        int p = Math.max(1, page);
        int s = Math.min(100, Math.max(1, size));
        if (itemId != null) {
            Integer total = db().queryForObject(
                    "SELECT COUNT(*) FROM download_log WHERE item_id=?", Integer.class, itemId);
            List<Map<String, Object>> list = db().query(
                    "SELECT l.id, l.item_id, l.username, l.downloaded_at, d.title "
                            + "FROM download_log l JOIN doc_item d ON d.id=l.item_id "
                            + "WHERE l.item_id=? ORDER BY l.id DESC LIMIT ? OFFSET ?",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("id", rs.getLong("id"));
                        m.put("itemId", rs.getLong("item_id"));
                        m.put("username", rs.getString("username"));
                        m.put("title", rs.getString("title"));
                        m.put("downloadedAt", fmt(rs.getTimestamp("downloaded_at")));
                        return m;
                    },
                    itemId, s, (p - 1) * s);
            return pageOut(list, total, p, s);
        }
        Integer total = db().queryForObject("SELECT COUNT(*) FROM download_log", Integer.class);
        List<Map<String, Object>> list = db().query(
                "SELECT l.id, l.item_id, l.username, l.downloaded_at, d.title "
                        + "FROM download_log l JOIN doc_item d ON d.id=l.item_id "
                        + "ORDER BY l.id DESC LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("itemId", rs.getLong("item_id"));
                    m.put("username", rs.getString("username"));
                    m.put("title", rs.getString("title"));
                    m.put("downloadedAt", fmt(rs.getTimestamp("downloaded_at")));
                    return m;
                },
                s, (p - 1) * s);
        return pageOut(list, total, p, s);
    }

    public static Map<String, Object> updateMeta(long id, Map<String, Object> body) {
        require();
        Map<String, Object> item = getItem(id);
        if (item == null) throw new IllegalArgumentException("资料不存在");
        String fileUrl = clip(str(body.get("fileUrl")), 255);
        String access = clip(str(body.get("accessLevel")), 16).toLowerCase(Locale.ROOT);
        if (access.isBlank()) access = "login";
        if (!ACCESS.contains(access)) throw new IllegalArgumentException("权限须为 public/login/staff");
        db().update("UPDATE doc_item SET file_url=?, access_level=? WHERE id=?", fileUrl, access, id);
        item.put("fileUrl", fileUrl);
        item.put("accessLevel", access);
        if (downloadGateOn || hasCol("doc_item", "preview_url")) {
            if (body.containsKey("previewUrl") && hasCol("doc_item", "preview_url")) {
                String preview = clip(str(body.get("previewUrl")), 512);
                db().update("UPDATE doc_item SET preview_url=? WHERE id=?", preview, id);
                item.put("previewUrl", preview);
            }
            if (body.containsKey("downloadRoles") && hasCol("doc_item", "download_roles")) {
                String roles = clip(str(body.get("downloadRoles")), 255);
                db().update("UPDATE doc_item SET download_roles=? WHERE id=?", roles, id);
                item.put("downloadRoles", roles);
            }
            if (body.containsKey("trialReadNote") && hasCol("doc_item", "trial_read_note")) {
                String note = clip(str(body.get("trialReadNote")), 2000);
                db().update("UPDATE doc_item SET trial_read_note=? WHERE id=?", note, id);
                item.put("trialReadNote", note);
            }
            if (body.containsKey("watermarkOn") && hasCol("doc_item", "watermark_on")) {
                int w = toBool(body.get("watermarkOn")) ? 1 : 0;
                db().update("UPDATE doc_item SET watermark_on=? WHERE id=?", w, id);
                item.put("watermarkOn", w == 1);
            }
            if (body.containsKey("needsDownloadAudit") && hasCol("doc_item", "needs_download_audit")) {
                int a = toBool(body.get("needsDownloadAudit")) ? 1 : 0;
                db().update("UPDATE doc_item SET needs_download_audit=? WHERE id=?", a, id);
                item.put("needsDownloadAudit", a == 1);
            }
            if (body.containsKey("dailyDownloadLimit") && hasCol("doc_item", "daily_download_limit")) {
                int lim = Math.max(0, toInt(body.get("dailyDownloadLimit"), 0));
                db().update("UPDATE doc_item SET daily_download_limit=? WHERE id=?", lim, id);
                item.put("dailyDownloadLimit", lim);
            }
            if (body.containsKey("downloadCostPoints") && hasCol("doc_item", "download_cost_points")) {
                int cost = Math.max(0, toInt(body.get("downloadCostPoints"), 0));
                db().update("UPDATE doc_item SET download_cost_points=? WHERE id=?", cost, id);
                item.put("downloadCostPoints", cost);
            }
        }
        if (tagCloudOn && body.containsKey("tags")) {
            Object raw = body.get("tags");
            List<String> tags = new ArrayList<>();
            if (raw instanceof List<?> list) {
                for (Object o : list) tags.add(str(o));
            } else if (raw != null) {
                for (String p : str(raw).split("[,，;；]+")) {
                    if (!p.isBlank()) tags.add(p.trim());
                }
            }
            setItemTags(id, tags);
            item.put("tags", listItemTags(id));
        }
        return item;
    }

    // ---- 章节 / 版本 ----

    public static List<Map<String, Object>> listChapters(long itemId) {
        if (!chapterOn || itemId <= 0) return List.of();
        ensureChapterTables();
        return db().query(
                "SELECT id, item_id, title, anchor, sort_ord FROM doc_chapter "
                        + "WHERE item_id=? ORDER BY sort_ord ASC, id ASC",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("itemId", rs.getLong("item_id"));
                    m.put("title", rs.getString("title"));
                    m.put("anchor", rs.getString("anchor"));
                    m.put("sortOrd", rs.getInt("sort_ord"));
                    return m;
                },
                itemId);
    }

    public static Map<String, Object> saveChapter(Long id, long itemId, String title, String anchor, int sortOrd) {
        if (!chapterOn) throw new IllegalStateException("未开放章节目录");
        if (itemId <= 0) throw new IllegalArgumentException("资料无效");
        String t = clip(title, 128);
        if (t.isBlank()) throw new IllegalArgumentException("章节标题不能为空");
        String a = clip(anchor, 64);
        ensureChapterTables();
        if (id != null && id > 0) {
            db().update(
                    "UPDATE doc_chapter SET title=?, anchor=?, sort_ord=? WHERE id=? AND item_id=?",
                    t, a, sortOrd, id, itemId);
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id", id);
            m.put("itemId", itemId);
            m.put("title", t);
            m.put("anchor", a);
            m.put("sortOrd", sortOrd);
            return m;
        }
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO doc_chapter(item_id,title,anchor,sort_ord) VALUES(?,?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, itemId);
            ps.setString(2, t);
            ps.setString(3, a);
            ps.setInt(4, sortOrd);
            return ps;
        }, kh);
        Number key = kh.getKey();
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", key == null ? 0L : key.longValue());
        m.put("itemId", itemId);
        m.put("title", t);
        m.put("anchor", a);
        m.put("sortOrd", sortOrd);
        return m;
    }

    public static void deleteChapter(long id, long itemId) {
        if (!chapterOn) throw new IllegalStateException("未开放章节目录");
        ensureChapterTables();
        db().update("DELETE FROM doc_chapter WHERE id=? AND item_id=?", id, itemId);
    }

    public static List<Map<String, Object>> listVersions(long itemId) {
        if (!chapterOn || itemId <= 0) return List.of();
        ensureChapterTables();
        return db().query(
                "SELECT id, item_id, version_no, note, created_at FROM doc_version "
                        + "WHERE item_id=? ORDER BY id DESC",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("itemId", rs.getLong("item_id"));
                    m.put("versionNo", rs.getString("version_no"));
                    m.put("note", rs.getString("note"));
                    m.put("createdAt", fmt(rs.getTimestamp("created_at")));
                    return m;
                },
                itemId);
    }

    public static Map<String, Object> addVersion(long itemId, String versionNo, String note) {
        if (!chapterOn) throw new IllegalStateException("未开放版本记录");
        if (itemId <= 0) throw new IllegalArgumentException("资料无效");
        String v = clip(versionNo, 32);
        if (v.isBlank()) throw new IllegalArgumentException("版本号不能为空");
        String n = clip(note, 512);
        ensureChapterTables();
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO doc_version(item_id,version_no,note) VALUES(?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, itemId);
            ps.setString(2, v);
            ps.setString(3, n);
            return ps;
        }, kh);
        Number key = kh.getKey();
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", key == null ? 0L : key.longValue());
        m.put("itemId", itemId);
        m.put("versionNo", v);
        m.put("note", n);
        m.put("createdAt", LocalDateTime.now().format(FMT));
        return m;
    }

    // ---- 标签云 ----

    public static List<Map<String, Object>> tagCloud(int limit) {
        if (!tagCloudOn) return List.of();
        ensureTagTables();
        int n = Math.min(100, Math.max(1, limit));
        return db().query(
                "SELECT id, name, use_count FROM doc_tag WHERE use_count>0 ORDER BY use_count DESC, id ASC LIMIT ?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("name", rs.getString("name"));
                    m.put("useCount", rs.getInt("use_count"));
                    return m;
                },
                n);
    }

    public static List<Map<String, Object>> listItemTags(long itemId) {
        if (!tagCloudOn || itemId <= 0) return List.of();
        ensureTagTables();
        return db().query(
                "SELECT t.id, t.name, t.use_count FROM doc_tag t "
                        + "JOIN doc_item_tag it ON it.tag_id=t.id WHERE it.item_id=? ORDER BY t.name",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("name", rs.getString("name"));
                    m.put("useCount", rs.getInt("use_count"));
                    return m;
                },
                itemId);
    }

    public static void setItemTags(long itemId, List<String> tags) {
        if (!tagCloudOn) throw new IllegalStateException("未开放标签云");
        if (itemId <= 0) throw new IllegalArgumentException("资料无效");
        ensureTagTables();
        List<Map<String, Object>> old = listItemTags(itemId);
        for (Map<String, Object> t : old) {
            db().update(
                    "UPDATE doc_tag SET use_count=GREATEST(0, use_count-1) WHERE id=?",
                    t.get("id"));
        }
        db().update("DELETE FROM doc_item_tag WHERE item_id=?", itemId);
        Set<String> seen = new LinkedHashSet<>();
        for (String raw : tags == null ? List.<String>of() : tags) {
            String name = clip(raw, 64);
            if (name.isBlank() || !seen.add(name.toLowerCase(Locale.ROOT))) continue;
            Long tagId = null;
            List<Long> ids = db().query(
                    "SELECT id FROM doc_tag WHERE name=?",
                    (rs, i) -> rs.getLong("id"),
                    name);
            if (ids.isEmpty()) {
                KeyHolder kh = new GeneratedKeyHolder();
                db().update(con -> {
                    PreparedStatement ps = con.prepareStatement(
                            "INSERT INTO doc_tag(name, use_count) VALUES(?,0)",
                            Statement.RETURN_GENERATED_KEYS);
                    ps.setString(1, name);
                    return ps;
                }, kh);
                Number key = kh.getKey();
                tagId = key == null ? null : key.longValue();
            } else {
                tagId = ids.get(0);
            }
            if (tagId == null) continue;
            db().update("INSERT IGNORE INTO doc_item_tag(item_id, tag_id) VALUES(?,?)", itemId, tagId);
            db().update("UPDATE doc_tag SET use_count=use_count+1 WHERE id=?", tagId);
        }
    }

    // ---- 纠错 / 侵权 ----

    public static Map<String, Object> submitFeedback(String username, long itemId, String kind, String body) {
        if (!feedbackOn) throw new IllegalStateException("未开放纠错与投诉");
        if (itemId <= 0) throw new IllegalArgumentException("资料无效");
        String k = clip(kind, 16).toLowerCase(Locale.ROOT);
        if (!FEEDBACK_KINDS.contains(k)) throw new IllegalArgumentException("类型须为 correction 或 infringement");
        String b = clip(body, 1000);
        if (b.isBlank()) throw new IllegalArgumentException("内容不能为空");
        ensureFeedbackTable();
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO doc_feedback(item_id,username,kind,body,status) VALUES(?,?,?,?,'pending')",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, itemId);
            ps.setString(2, username);
            ps.setString(3, k);
            ps.setString(4, b);
            return ps;
        }, kh);
        Number key = kh.getKey();
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", key == null ? 0L : key.longValue());
        m.put("itemId", itemId);
        m.put("kind", k);
        m.put("status", "pending");
        return m;
    }

    public static Map<String, Object> pageFeedbackAdmin(int page, int size, String status) {
        if (!feedbackOn) throw new IllegalStateException("未开放纠错与投诉");
        ensureFeedbackTable();
        int p = Math.max(1, page);
        int s = Math.min(100, Math.max(1, size));
        String st = clip(status, 16);
        if (!st.isBlank()) {
            Integer total = db().queryForObject(
                    "SELECT COUNT(*) FROM doc_feedback WHERE status=?", Integer.class, st);
            List<Map<String, Object>> list = db().query(
                    "SELECT f.id, f.item_id, f.username, f.kind, f.body, f.status, f.handle_note, "
                            + "f.created_at, f.handled_at, d.title "
                            + "FROM doc_feedback f LEFT JOIN doc_item d ON d.id=f.item_id "
                            + "WHERE f.status=? ORDER BY f.id DESC LIMIT ? OFFSET ?",
                    (rs, i) -> mapFeedback(rs),
                    st, s, (p - 1) * s);
            return pageOut(list, total, p, s);
        }
        Integer total = db().queryForObject("SELECT COUNT(*) FROM doc_feedback", Integer.class);
        List<Map<String, Object>> list = db().query(
                "SELECT f.id, f.item_id, f.username, f.kind, f.body, f.status, f.handle_note, "
                        + "f.created_at, f.handled_at, d.title "
                        + "FROM doc_feedback f LEFT JOIN doc_item d ON d.id=f.item_id "
                        + "ORDER BY f.id DESC LIMIT ? OFFSET ?",
                (rs, i) -> mapFeedback(rs),
                s, (p - 1) * s);
        return pageOut(list, total, p, s);
    }

    private static Map<String, Object> mapFeedback(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("itemId", rs.getLong("item_id"));
        m.put("username", rs.getString("username"));
        m.put("kind", rs.getString("kind"));
        m.put("body", rs.getString("body"));
        m.put("status", rs.getString("status"));
        m.put("handleNote", rs.getString("handle_note"));
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        m.put("handledAt", fmt(rs.getTimestamp("handled_at")));
        m.put("title", rs.getString("title"));
        return m;
    }

    public static Map<String, Object> handleFeedback(long id, String status, String handleNote) {
        if (!feedbackOn) throw new IllegalStateException("未开放纠错与投诉");
        String st = clip(status, 16).toLowerCase(Locale.ROOT);
        if (!Set.of("handled", "rejected", "pending").contains(st)) {
            throw new IllegalArgumentException("状态无效");
        }
        ensureFeedbackTable();
        db().update(
                "UPDATE doc_feedback SET status=?, handle_note=?, handled_at=NOW() WHERE id=?",
                st, clip(handleNote, 512), id);
        List<Map<String, Object>> rows = db().query(
                "SELECT f.id, f.item_id, f.username, f.kind, f.body, f.status, f.handle_note, "
                        + "f.created_at, f.handled_at, d.title "
                        + "FROM doc_feedback f LEFT JOIN doc_item d ON d.id=f.item_id WHERE f.id=?",
                (rs, i) -> mapFeedback(rs),
                id);
        return rows.isEmpty() ? Map.of("id", id, "status", st) : rows.get(0);
    }

    // ---- 下载审核 ----

    public static Map<String, Object> pageDownloadRequests(int page, int size, String status) {
        if (!downloadGateOn) throw new IllegalStateException("未开放下载审核");
        ensureAuditTable();
        int p = Math.max(1, page);
        int s = Math.min(100, Math.max(1, size));
        String st = clip(status, 16);
        if (!st.isBlank()) {
            Integer total = db().queryForObject(
                    "SELECT COUNT(*) FROM doc_download_request WHERE status=?", Integer.class, st);
            List<Map<String, Object>> list = db().query(
                    "SELECT r.id, r.item_id, r.username, r.status, r.handle_note, r.created_at, r.handled_at, d.title "
                            + "FROM doc_download_request r LEFT JOIN doc_item d ON d.id=r.item_id "
                            + "WHERE r.status=? ORDER BY r.id DESC LIMIT ? OFFSET ?",
                    (rs, i) -> mapRequest(rs),
                    st, s, (p - 1) * s);
            return pageOut(list, total, p, s);
        }
        Integer total = db().queryForObject("SELECT COUNT(*) FROM doc_download_request", Integer.class);
        List<Map<String, Object>> list = db().query(
                "SELECT r.id, r.item_id, r.username, r.status, r.handle_note, r.created_at, r.handled_at, d.title "
                        + "FROM doc_download_request r LEFT JOIN doc_item d ON d.id=r.item_id "
                        + "ORDER BY r.id DESC LIMIT ? OFFSET ?",
                (rs, i) -> mapRequest(rs),
                s, (p - 1) * s);
        return pageOut(list, total, p, s);
    }

    private static Map<String, Object> mapRequest(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("itemId", rs.getLong("item_id"));
        m.put("username", rs.getString("username"));
        m.put("status", rs.getString("status"));
        m.put("handleNote", rs.getString("handle_note"));
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        m.put("handledAt", fmt(rs.getTimestamp("handled_at")));
        m.put("title", rs.getString("title"));
        return m;
    }

    public static Map<String, Object> handleDownloadRequest(long id, String status, String handleNote) {
        if (!downloadGateOn) throw new IllegalStateException("未开放下载审核");
        String st = clip(status, 16).toLowerCase(Locale.ROOT);
        if (!Set.of("approved", "rejected", "pending").contains(st)) {
            throw new IllegalArgumentException("状态无效");
        }
        ensureAuditTable();
        db().update(
                "UPDATE doc_download_request SET status=?, handle_note=?, handled_at=NOW() WHERE id=?",
                st, clip(handleNote, 512), id);
        List<Map<String, Object>> rows = db().query(
                "SELECT r.id, r.item_id, r.username, r.status, r.handle_note, r.created_at, r.handled_at, d.title "
                        + "FROM doc_download_request r LEFT JOIN doc_item d ON d.id=r.item_id WHERE r.id=?",
                (rs, i) -> mapRequest(rs),
                id);
        return rows.isEmpty() ? Map.of("id", id, "status", st) : rows.get(0);
    }
}
