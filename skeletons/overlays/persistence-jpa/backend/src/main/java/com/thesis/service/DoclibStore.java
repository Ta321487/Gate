package com.thesis.service;

import com.thesis.config.JpaSupport;
import com.thesis.config.JpaDb;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 文库下载台账（C-12）：资料附件、演示权限、下载记录。
 */
public class DoclibStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final Set<String> ACCESS = Set.of("public", "login", "staff");
    private static boolean enabled;
    private static Boolean tableReady;

    private DoclibStore() {}

    public static void configure(boolean on) {
        enabled = on;
        tableReady = null;
    }

    public static boolean enabled() {
        return enabled;
    }

    private static JpaDb db() {
        return JpaSupport.db();
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

    private static Map<String, Object> pageOut(List<?> list, Integer total, int page, int size) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
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
        return m;
    }

    public static List<Map<String, Object>> listOpenItems(boolean admin) {
        require();
        String sql = "SELECT id, title, author, isbn, category_id, stock, status, cover_url, file_url, access_level, created_at "
                + "FROM doc_item WHERE status='available' ";
        if (!admin) {
            sql += "AND access_level IN ('public','login') ";
        }
        sql += "ORDER BY id DESC";
        return db().query(sql, (rs, i) -> mapItem(rs));
    }

    public static Map<String, Object> getItem(long id) {
        require();
        List<Map<String, Object>> rows = db().query(
                "SELECT id, title, author, isbn, category_id, stock, status, cover_url, file_url, access_level, created_at "
                        + "FROM doc_item WHERE id=?",
                (rs, i) -> mapItem(rs),
                id);
        return rows.isEmpty() ? null : rows.get(0);
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

    public static Map<String, Object> download(String username, long id, boolean admin) {
        require();
        Map<String, Object> item = getItem(id);
        if (item == null) throw new IllegalArgumentException("资料不存在");
        assertAccess(item, admin);
        String url = str(item.get("fileUrl"));
        if (url.isBlank()) throw new IllegalStateException("未配置附件地址");
        db().update("INSERT INTO download_log(item_id, username) VALUES(?,?)", id, username);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("itemId", id);
        out.put("title", item.get("title"));
        out.put("url", url);
        out.put("accessLevel", item.get("accessLevel"));
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
        return item;
    }
}
