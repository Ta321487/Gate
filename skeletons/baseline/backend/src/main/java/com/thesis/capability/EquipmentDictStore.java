package com.thesis.capability;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 能力 room_equipment：会议室配套设备字典；按课题需要启用。 */
public final class EquipmentDictStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final String TABLE = "sys_equipment_dict";
    private static boolean enabled = false;

    private EquipmentDictStore() {}

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
                            + "name VARCHAR(64) NOT NULL,"
                            + "sort_order INT NOT NULL DEFAULT 0,"
                            + "enabled TINYINT NOT NULL DEFAULT 1,"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "UNIQUE KEY uk_equip_name (name)"
                            + ")");
        } catch (Exception ignored) {
        }
        seedIfEmpty();
    }

    private static void seedIfEmpty() {
        try {
            Integer n = db().queryForObject("SELECT COUNT(*) FROM " + TABLE, Integer.class);
            if (n != null && n > 0) return;
            String[] names = {"投影仪", "音响", "白板", "视频会议终端", "投屏线"};
            int order = 10;
            for (String name : names) {
                db().update(
                        "INSERT INTO " + TABLE + " (name, sort_order, enabled) VALUES (?,?,1)",
                        name, order);
                order += 10;
            }
        } catch (Exception ignored) {
        }
    }

    /** 启用中的设备名（档案多选 / 展示用）。 */
    public static List<String> optionNames() {
        if (!enabled) return List.of();
        try {
            return db().query(
                    "SELECT name FROM " + TABLE + " WHERE enabled=1 ORDER BY sort_order ASC, id ASC",
                    (rs, i) -> rs.getString("name"));
        } catch (Exception e) {
            return List.of();
        }
    }

    public static Map<String, Object> page(String keyword, int page, int size) {
        if (!enabled) throw new IllegalStateException("设备字典暂不可用");
        if (page < 1) page = 1;
        if (size < 1) size = 20;
        StringBuilder where = new StringBuilder(" WHERE 1=1");
        List<Object> args = new ArrayList<>();
        String kw = keyword == null ? "" : keyword.trim();
        if (!kw.isBlank()) {
            where.append(" AND name LIKE ?");
            args.add("%" + kw + "%");
        }
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM " + TABLE + where, Integer.class, args.toArray());
        args.add(size);
        args.add((page - 1) * size);
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM " + TABLE + where + " ORDER BY sort_order ASC, id ASC LIMIT ? OFFSET ?",
                (rs, i) -> mapRow(rs),
                args.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", rows == null ? List.of() : rows);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    public static Map<String, Object> create(String name, Integer sortOrder, Boolean on) {
        if (!enabled) throw new IllegalStateException("设备字典暂不可用");
        String n = requireName(name);
        Integer exists = db().queryForObject(
                "SELECT COUNT(*) FROM " + TABLE + " WHERE name=?", Integer.class, n);
        if (exists != null && exists > 0) {
            throw new IllegalArgumentException("设备名称已存在");
        }
        int sort = sortOrder == null ? 100 : sortOrder;
        int en = on == null || on ? 1 : 0;
        db().update(
                "INSERT INTO " + TABLE + " (name, sort_order, enabled, created_at) VALUES (?,?,?,?)",
                n, sort, en, Timestamp.valueOf(LocalDateTime.now()));
        Long id = db().queryForObject("SELECT id FROM " + TABLE + " WHERE name=?", Long.class, n);
        return get(id == null ? 0L : id);
    }

    public static Map<String, Object> update(long id, String name, Integer sortOrder, Boolean on) {
        if (!enabled) throw new IllegalStateException("设备字典暂不可用");
        Map<String, Object> cur = get(id);
        if (cur.isEmpty()) throw new IllegalArgumentException("记录不存在");
        String n = name == null ? String.valueOf(cur.get("name")) : requireName(name);
        Integer dup = db().queryForObject(
                "SELECT COUNT(*) FROM " + TABLE + " WHERE name=? AND id<>?", Integer.class, n, id);
        if (dup != null && dup > 0) {
            throw new IllegalArgumentException("设备名称已存在");
        }
        int sort = sortOrder == null
                ? ((Number) cur.getOrDefault("sortOrder", 0)).intValue()
                : sortOrder;
        int en = on == null
                ? (Boolean.TRUE.equals(cur.get("enabled")) ? 1 : 0)
                : (on ? 1 : 0);
        db().update(
                "UPDATE " + TABLE + " SET name=?, sort_order=?, enabled=? WHERE id=?",
                n, sort, en, id);
        return get(id);
    }

    public static void delete(long id) {
        if (!enabled) throw new IllegalStateException("设备字典暂不可用");
        db().update("DELETE FROM " + TABLE + " WHERE id=?", id);
    }

    public static Map<String, Object> get(long id) {
        if (!enabled || id <= 0) return Map.of();
        try {
            List<Map<String, Object>> rows = db().query(
                    "SELECT * FROM " + TABLE + " WHERE id=?",
                    (rs, i) -> mapRow(rs),
                    id);
            return rows == null || rows.isEmpty() ? Map.of() : rows.get(0);
        } catch (Exception e) {
            return Map.of();
        }
    }

    private static String requireName(String name) {
        String n = name == null ? "" : name.trim();
        if (n.isBlank()) throw new IllegalArgumentException("设备名称不能为空");
        if (n.length() > 64) n = n.substring(0, 64);
        return n;
    }

    private static Map<String, Object> mapRow(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("name", rs.getString("name"));
        m.put("sortOrder", rs.getInt("sort_order"));
        m.put("enabled", rs.getInt("enabled") == 1);
        Timestamp ts = rs.getTimestamp("created_at");
        m.put("createdAt", ts == null ? "" : FMT.format(ts.toLocalDateTime()));
        return m;
    }
}
