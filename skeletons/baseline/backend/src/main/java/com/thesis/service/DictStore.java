package com.thesis.service;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/** 通识数据字典（sys_dict）：类型 + 项；启停/排序。 */
public final class DictStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static Boolean tableReady;

    private DictStore() {}

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
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
                    "CREATE TABLE IF NOT EXISTS sys_dict ("
                            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
                            + "dict_type VARCHAR(64) NOT NULL,"
                            + "item_code VARCHAR(64) NOT NULL,"
                            + "item_label VARCHAR(128) NOT NULL,"
                            + "sort_order INT NOT NULL DEFAULT 0,"
                            + "enabled TINYINT NOT NULL DEFAULT 1,"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "UNIQUE KEY uk_dict_type_code (dict_type, item_code),"
                            + "KEY idx_dict_type_sort (dict_type, enabled, sort_order)"
                            + ")");
            tableReady = true;
            seedIfEmpty();
        } catch (Exception e) {
            tableReady = false;
        }
    }

    private static void seedIfEmpty() {
        try {
            Integer n = db().queryForObject("SELECT COUNT(*) FROM sys_dict", Integer.class);
            if (n != null && n > 0) return;
            db().update(
                    "INSERT INTO sys_dict (dict_type, item_code, item_label, sort_order, enabled) VALUES (?,?,?,?,1)",
                    "common_status", "enabled", "启用", 10);
            db().update(
                    "INSERT INTO sys_dict (dict_type, item_code, item_label, sort_order, enabled) VALUES (?,?,?,?,1)",
                    "common_status", "disabled", "停用", 20);
        } catch (Exception ignored) {
        }
    }

    private static Map<String, Object> row(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("dictType", rs.getString("dict_type"));
        m.put("itemCode", rs.getString("item_code"));
        m.put("itemLabel", rs.getString("item_label"));
        m.put("sortOrder", rs.getInt("sort_order"));
        m.put("enabled", rs.getInt("enabled") > 0);
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        return m;
    }

    public static List<String> listTypes() {
        ensureTable();
        if (!Boolean.TRUE.equals(tableReady)) return List.of();
        return db().query(
                "SELECT DISTINCT dict_type FROM sys_dict ORDER BY dict_type ASC",
                (rs, i) -> rs.getString("dict_type"));
    }

    /** 启用项（下拉）；未指定类型则空。 */
    public static List<Map<String, Object>> options(String dictType) {
        ensureTable();
        if (!Boolean.TRUE.equals(tableReady)) return List.of();
        String t = dictType == null ? "" : dictType.trim();
        if (t.isBlank()) return List.of();
        return db().query(
                "SELECT * FROM sys_dict WHERE dict_type=? AND enabled=1 ORDER BY sort_order ASC, id ASC",
                (rs, i) -> row(rs), t);
    }

    public static Map<String, Object> page(String dictType, String keyword, int page, int size) {
        ensureTable();
        if (!Boolean.TRUE.equals(tableReady)) {
            throw new IllegalStateException("数据字典暂不可用");
        }
        if (page < 1) page = 1;
        if (size < 1) size = 20;
        StringBuilder where = new StringBuilder(" WHERE 1=1");
        List<Object> args = new ArrayList<>();
        String t = dictType == null ? "" : dictType.trim();
        if (!t.isBlank()) {
            where.append(" AND dict_type=?");
            args.add(t);
        }
        String kw = keyword == null ? "" : keyword.trim();
        if (!kw.isBlank()) {
            where.append(" AND (item_code LIKE ? OR item_label LIKE ?)");
            args.add("%" + kw + "%");
            args.add("%" + kw + "%");
        }
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM sys_dict" + where, Integer.class, args.toArray());
        args.add(size);
        args.add((page - 1) * size);
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM sys_dict" + where + " ORDER BY dict_type ASC, sort_order ASC, id ASC LIMIT ? OFFSET ?",
                (rs, i) -> row(rs),
                args.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", rows == null ? List.of() : rows);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    public static Map<String, Object> get(long id) {
        ensureTable();
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM sys_dict WHERE id=?", (rs, i) -> row(rs), id);
        return rows.isEmpty() ? Map.of() : rows.get(0);
    }

    public static Map<String, Object> create(
            String dictType, String itemCode, String itemLabel, Integer sortOrder, Boolean on) {
        ensureTable();
        String t = requireToken(dictType, "字典类型");
        String code = requireToken(itemCode, "编码");
        String label = requireLabel(itemLabel);
        Integer exists = db().queryForObject(
                "SELECT COUNT(*) FROM sys_dict WHERE dict_type=? AND item_code=?",
                Integer.class, t, code);
        if (exists != null && exists > 0) {
            throw new IllegalArgumentException("同类型下编码已存在");
        }
        int sort = sortOrder == null ? 100 : sortOrder;
        int en = on == null || on ? 1 : 0;
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO sys_dict (dict_type, item_code, item_label, sort_order, enabled, created_at) "
                            + "VALUES (?,?,?,?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, t);
            ps.setString(2, code);
            ps.setString(3, label);
            ps.setInt(4, sort);
            ps.setInt(5, en);
            ps.setTimestamp(6, Timestamp.valueOf(LocalDateTime.now()));
            return ps;
        }, kh);
        Number key = kh.getKey();
        return get(key == null ? 0L : key.longValue());
    }

    public static Map<String, Object> update(
            long id, String dictType, String itemCode, String itemLabel, Integer sortOrder, Boolean on) {
        ensureTable();
        Map<String, Object> cur = get(id);
        if (cur.isEmpty()) throw new IllegalArgumentException("记录不存在");
        String t = dictType == null ? String.valueOf(cur.get("dictType")) : requireToken(dictType, "字典类型");
        String code = itemCode == null ? String.valueOf(cur.get("itemCode")) : requireToken(itemCode, "编码");
        String label = itemLabel == null ? String.valueOf(cur.get("itemLabel")) : requireLabel(itemLabel);
        Integer dup = db().queryForObject(
                "SELECT COUNT(*) FROM sys_dict WHERE dict_type=? AND item_code=? AND id<>?",
                Integer.class, t, code, id);
        if (dup != null && dup > 0) {
            throw new IllegalArgumentException("同类型下编码已存在");
        }
        int sort = sortOrder == null
                ? ((Number) cur.getOrDefault("sortOrder", 0)).intValue()
                : sortOrder;
        int en = on == null
                ? (Boolean.TRUE.equals(cur.get("enabled")) ? 1 : 0)
                : (on ? 1 : 0);
        db().update(
                "UPDATE sys_dict SET dict_type=?, item_code=?, item_label=?, sort_order=?, enabled=? WHERE id=?",
                t, code, label, sort, en, id);
        return get(id);
    }

    /** 调整排序权重（浅；≠ 跨表拖拽引擎）。 */
    public static Map<String, Object> bumpSort(long id, int delta) {
        ensureTable();
        Map<String, Object> cur = get(id);
        if (cur.isEmpty()) throw new IllegalArgumentException("记录不存在");
        int sort = ((Number) cur.getOrDefault("sortOrder", 0)).intValue() + delta;
        db().update("UPDATE sys_dict SET sort_order=? WHERE id=?", sort, id);
        return get(id);
    }

    public static void delete(long id) {
        ensureTable();
        db().update("DELETE FROM sys_dict WHERE id=?", id);
    }

    private static String requireToken(String raw, String label) {
        String s = raw == null ? "" : raw.trim();
        if (s.isBlank()) throw new IllegalArgumentException(label + "不能为空");
        if (s.length() > 64) throw new IllegalArgumentException(label + "过长");
        return s;
    }

    private static String requireLabel(String raw) {
        String s = raw == null ? "" : raw.trim();
        if (s.isBlank()) throw new IllegalArgumentException("显示名不能为空");
        if (s.length() > 128) throw new IllegalArgumentException("显示名过长");
        return s;
    }
}
