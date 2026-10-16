package com.thesis.service;

import com.thesis.config.GeneratedKeyHolder;
import com.thesis.config.JpaDb;
import com.thesis.config.JpaSupport;
import com.thesis.config.KeyHolder;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * Banner slots (sys_banner) via JpaDb.
 */
public class BannerStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static Boolean tableReady;

    private static JpaDb db() {
        return JpaSupport.db();
    }

    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        String s = String.valueOf(o);
        return s.isBlank() ? null : s;
    }

    public static synchronized void ensureTable() {
        if (Boolean.TRUE.equals(tableReady)) return;
        try {
            db().execute(
                    "CREATE TABLE IF NOT EXISTS sys_banner ("
                            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
                            + "slot VARCHAR(32) NOT NULL DEFAULT 'home',"
                            + "title VARCHAR(128) NOT NULL DEFAULT '',"
                            + "lead_text VARCHAR(255) NOT NULL DEFAULT '',"
                            + "image_url VARCHAR(512) NOT NULL DEFAULT '',"
                            + "link_url VARCHAR(512) NOT NULL DEFAULT '',"
                            + "sort_order INT NOT NULL DEFAULT 0,"
                            + "enabled TINYINT NOT NULL DEFAULT 1,"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "KEY idx_banner_slot (slot, enabled, sort_order)"
                            + ")");
            tableReady = true;
        } catch (Exception e) {
            tableReady = false;
        }
    }

    private static Map<String, Object> row(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("slot", rs.getString("slot"));
        m.put("title", rs.getString("title"));
        m.put("lead", rs.getString("lead_text"));
        m.put("imageUrl", rs.getString("image_url"));
        m.put("linkUrl", rs.getString("link_url"));
        m.put("sortOrder", rs.getInt("sort_order"));
        m.put("enabled", rs.getInt("enabled") > 0);
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        // č˝Žć­çťäťśčŽ¤ src
        m.put("src", rs.getString("image_url"));
        return m;
    }

    /** é¨ćˇĺŻç¨ć§˝ä˝ĺčĄ¨ă */
    public static List<Map<String, Object>> listEnabled(String slot) {
        ensureTable();
        if (!Boolean.TRUE.equals(tableReady)) return List.of();
        String s = slot == null || slot.isBlank() ? "home" : slot.trim();
        return db().query(
                "SELECT * FROM sys_banner WHERE slot=? AND enabled=1 ORDER BY sort_order ASC, id ASC",
                (rs, i) -> row(rs), s);
    }

    public static List<Map<String, Object>> listAll() {
        ensureTable();
        if (!Boolean.TRUE.equals(tableReady)) return List.of();
        return db().query(
                "SELECT * FROM sys_banner ORDER BY slot ASC, sort_order ASC, id ASC",
                (rs, i) -> row(rs));
    }

    public static Map<String, Object> get(long id) {
        ensureTable();
        if (!Boolean.TRUE.equals(tableReady)) return null;
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM sys_banner WHERE id=?", (rs, i) -> row(rs), id);
        return list.isEmpty() ? null : list.get(0);
    }

    public static Map<String, Object> add(Map<String, Object> body) {
        ensureTable();
        if (!Boolean.TRUE.equals(tableReady)) throw new IllegalStateException("ĺšżĺä˝čĄ¨ä¸ĺŻç¨");
        String slot = str(body, "slot", "home");
        String title = str(body, "title", "");
        String lead = str(body, "lead", str(body, "leadText", ""));
        String image = str(body, "imageUrl", str(body, "src", ""));
        String link = str(body, "linkUrl", "");
        int sort = intVal(body.get("sortOrder"), 0);
        int enabled = boolVal(body.get("enabled"), true) ? 1 : 0;
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO sys_banner (slot,title,lead_text,image_url,link_url,sort_order,enabled) "
                            + "VALUES (?,?,?,?,?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, slot);
            ps.setString(2, title);
            ps.setString(3, lead);
            ps.setString(4, image);
            ps.setString(5, link);
            ps.setInt(6, sort);
            ps.setInt(7, enabled);
            return ps;
        }, kh);
        Number key = kh.getKey();
        return get(key == null ? 0L : key.longValue());
    }

    public static Map<String, Object> update(long id, Map<String, Object> body) {
        Map<String, Object> cur = get(id);
        if (cur == null) return null;
        String slot = body.containsKey("slot") ? str(body, "slot", "home") : String.valueOf(cur.get("slot"));
        String title = body.containsKey("title") ? str(body, "title", "") : String.valueOf(cur.get("title"));
        String lead = body.containsKey("lead") || body.containsKey("leadText")
                ? str(body, "lead", str(body, "leadText", ""))
                : String.valueOf(cur.get("lead"));
        String image = body.containsKey("imageUrl") || body.containsKey("src")
                ? str(body, "imageUrl", str(body, "src", ""))
                : String.valueOf(cur.get("imageUrl"));
        String link = body.containsKey("linkUrl") ? str(body, "linkUrl", "") : String.valueOf(cur.get("linkUrl"));
        int sort = body.containsKey("sortOrder") ? intVal(body.get("sortOrder"), 0) : intVal(cur.get("sortOrder"), 0);
        int enabled = body.containsKey("enabled")
                ? (boolVal(body.get("enabled"), true) ? 1 : 0)
                : (Boolean.TRUE.equals(cur.get("enabled")) ? 1 : 0);
        db().update(
                "UPDATE sys_banner SET slot=?, title=?, lead_text=?, image_url=?, link_url=?, sort_order=?, enabled=? WHERE id=?",
                slot, title, lead, image, link, sort, enabled, id);
        return get(id);
    }

    public static boolean delete(long id) {
        ensureTable();
        if (!Boolean.TRUE.equals(tableReady)) return false;
        return db().update("DELETE FROM sys_banner WHERE id=?", id) > 0;
    }

    private static String str(Map<String, Object> body, String key, String def) {
        if (body == null || !body.containsKey(key) || body.get(key) == null) return def;
        String s = String.valueOf(body.get(key)).trim();
        return s.isEmpty() ? def : s;
    }

    private static int intVal(Object o, int def) {
        if (o == null) return def;
        if (o instanceof Number n) return n.intValue();
        try {
            return Integer.parseInt(String.valueOf(o).trim());
        } catch (Exception e) {
            return def;
        }
    }

    private static boolean boolVal(Object o, boolean def) {
        if (o == null) return def;
        if (o instanceof Boolean b) return b;
        String s = String.valueOf(o).trim();
        if ("1".equals(s) || "true".equalsIgnoreCase(s)) return true;
        if ("0".equals(s) || "false".equalsIgnoreCase(s)) return false;
        return def;
    }
}
