package com.thesis.service;

import com.thesis.config.JpaSupport;
import com.thesis.config.JpaDb;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 本地签章（C-18）：上传签章图 + 勾选同意留痕；非 CA。
 */
public class ESignStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static boolean enabled;
    private static Boolean tableReady;

    private ESignStore() {}

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
                            + "WHERE table_schema=DATABASE() AND table_name='e_sign_record'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static void require() {
        if (!ready()) throw new IllegalStateException("签章功能暂不可用");
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

    private static boolean asBool(Object o) {
        if (o instanceof Boolean b) return b;
        if (o instanceof Number n) return n.intValue() != 0;
        String s = str(o).toLowerCase(Locale.ROOT);
        return "1".equals(s) || "true".equals(s) || "yes".equals(s) || "on".equals(s);
    }

    private static Map<String, Object> pageOut(List<?> list, Integer total, int page, int size) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    private static Map<String, Object> mapRow(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("title", rs.getString("title"));
        Object tid = rs.getObject("ticket_id");
        m.put("ticketId", tid == null ? null : rs.getLong("ticket_id"));
        m.put("signImageUrl", rs.getString("sign_image_url"));
        m.put("agreed", rs.getInt("agreed") != 0);
        m.put("remark", rs.getString("remark"));
        m.put("signedAt", fmt(rs.getTimestamp("signed_at")));
        return m;
    }

    public static Map<String, Object> pageMine(String username, int page, int size) {
        require();
        String u = clip(username, 64);
        if (page < 1) page = 1;
        if (size < 1) size = 20;
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM e_sign_record WHERE username=?", Integer.class, u);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM e_sign_record WHERE username=? ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> mapRow(rs),
                u, size, (page - 1) * size);
        return pageOut(list, total, page, size);
    }

    public static Map<String, Object> pageAdmin(int page, int size, String username) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 20;
        String u = clip(username, 64);
        Integer total;
        List<Map<String, Object>> list;
        if (u.isBlank()) {
            total = db().queryForObject("SELECT COUNT(*) FROM e_sign_record", Integer.class);
            list = db().query(
                    "SELECT * FROM e_sign_record ORDER BY id DESC LIMIT ? OFFSET ?",
                    (rs, i) -> mapRow(rs),
                    size, (page - 1) * size);
        } else {
            total = db().queryForObject(
                    "SELECT COUNT(*) FROM e_sign_record WHERE username=?", Integer.class, u);
            list = db().query(
                    "SELECT * FROM e_sign_record WHERE username=? ORDER BY id DESC LIMIT ? OFFSET ?",
                    (rs, i) -> mapRow(rs),
                    u, size, (page - 1) * size);
        }
        return pageOut(list, total, page, size);
    }

    public static Map<String, Object> submit(
            String username, String title, String signImageUrl, boolean agreed, Long ticketId, String remark) {
        require();
        String u = clip(username, 64);
        if (u.isBlank()) throw new IllegalArgumentException("用户无效");
        String t = clip(title, 200);
        if (t.isBlank()) throw new IllegalArgumentException("请填写签署标题");
        String img = clip(signImageUrl, 255);
        if (img.isBlank()) throw new IllegalArgumentException("请上传签章图");
        if (!agreed) throw new IllegalArgumentException("请勾选同意签署");
        String note = clip(remark, 255);
        Long tid = ticketId != null && ticketId > 0 ? ticketId : null;

        db().update(
                "INSERT INTO e_sign_record (username, title, ticket_id, sign_image_url, agreed, remark) "
                        + "VALUES (?,?,?,?,1,?)",
                u, t, tid, img, note);
        Long id = db().queryForObject("SELECT LAST_INSERT_ID()", Long.class);
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM e_sign_record WHERE id=?", (rs, i) -> mapRow(rs), id == null ? 0L : id);
        return rows.isEmpty() ? Map.of() : rows.get(0);
    }

    public static Map<String, Object> submitFromBody(String username, Map<String, Object> body) {
        Map<String, Object> b = body == null ? Map.of() : body;
        Long ticketId = null;
        Object raw = b.get("ticketId");
        if (raw instanceof Number n) ticketId = n.longValue();
        else if (raw != null && !String.valueOf(raw).isBlank()) {
            ticketId = Long.parseLong(String.valueOf(raw).trim());
        }
        return submit(
                username,
                str(b.get("title")),
                str(b.get("signImageUrl")).isBlank() ? str(b.get("imageUrl")) : str(b.get("signImageUrl")),
                asBool(b.get("agreed")),
                ticketId,
                str(b.get("remark")));
    }
}
