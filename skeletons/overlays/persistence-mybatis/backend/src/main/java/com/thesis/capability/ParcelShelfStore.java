package com.thesis.capability;

import com.thesis.config.MybatisSupport;
import com.thesis.config.MbSql;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 能力 parcel_shelf：驿站货架/柜格编码维护。 */
public final class ParcelShelfStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final String TABLE = "parcel_shelf";
    private static boolean enabled = false;

    private ParcelShelfStore() {}

    public static void configure(boolean on) {
        enabled = on;
        if (enabled) ensureTable();
    }

    public static boolean enabled() {
        return enabled;
    }

    private static MbSql db() {
        return MybatisSupport.db();
    }

    public static void ensureTable() {
        try {
            db().execute(
                    "CREATE TABLE IF NOT EXISTS " + TABLE + " ("
                            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
                            + "code VARCHAR(32) NOT NULL UNIQUE,"
                            + "remark VARCHAR(255) DEFAULT '',"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
                            + ")");
        } catch (Exception ignored) {
        }
        seedIfEmpty();
    }

    private static void seedIfEmpty() {
        try {
            Integer n = db().queryForObject("SELECT COUNT(*) FROM " + TABLE, Integer.class);
            if (n != null && n > 0) return;
            String[][] seeds = {{"A-01", "A区1号"}, {"A-02", "A区2号"}, {"B-01", "B区1号"}};
            for (String[] s : seeds) {
                db().update(
                        "INSERT INTO " + TABLE + " (code, remark, created_at) VALUES (?,?,?)",
                        s[0], s[1], Timestamp.valueOf(LocalDateTime.now()));
            }
        } catch (Exception ignored) {
        }
    }

    public static List<Map<String, Object>> list() {
        require();
        try {
            List<Map<String, Object>> rows = db().query(
                    "SELECT * FROM " + TABLE + " ORDER BY code ASC, id ASC",
                    (rs, i) -> mapRow(rs));
            return rows == null ? List.of() : rows;
        } catch (Exception e) {
            return List.of();
        }
    }

    public static Map<String, Object> create(String code, String remark) {
        require();
        String c = requireCode(code);
        Integer exists = db().queryForObject(
                "SELECT COUNT(*) FROM " + TABLE + " WHERE code=?", Integer.class, c);
        if (exists != null && exists > 0) {
            throw new IllegalArgumentException("货架编码已存在");
        }
        String r = blankRemark(remark);
        db().update(
                "INSERT INTO " + TABLE + " (code, remark, created_at) VALUES (?,?,?)",
                c, r, Timestamp.valueOf(LocalDateTime.now()));
        Long id = db().queryForObject("SELECT id FROM " + TABLE + " WHERE code=?", Long.class, c);
        return get(id == null ? 0L : id);
    }

    public static Map<String, Object> update(long id, String code, String remark) {
        require();
        Map<String, Object> cur = get(id);
        if (cur.isEmpty()) throw new IllegalArgumentException("货架不存在");
        String c = code == null ? String.valueOf(cur.get("code")) : requireCode(code);
        Integer dup = db().queryForObject(
                "SELECT COUNT(*) FROM " + TABLE + " WHERE code=? AND id<>?", Integer.class, c, id);
        if (dup != null && dup > 0) {
            throw new IllegalArgumentException("货架编码已存在");
        }
        String r = remark == null ? String.valueOf(cur.getOrDefault("remark", "")) : blankRemark(remark);
        db().update("UPDATE " + TABLE + " SET code=?, remark=? WHERE id=?", c, r, id);
        return get(id);
    }

    public static void delete(long id) {
        require();
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

    private static void require() {
        if (!enabled) throw new IllegalStateException("货架管理暂不可用");
    }

    private static String requireCode(String code) {
        String c = code == null ? "" : code.trim();
        if (c.isBlank()) throw new IllegalArgumentException("请填写货架编码");
        if (c.length() > 32) c = c.substring(0, 32);
        return c;
    }

    private static String blankRemark(String remark) {
        String r = remark == null ? "" : remark.trim();
        if (r.length() > 255) r = r.substring(0, 255);
        return r;
    }

    private static Map<String, Object> mapRow(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("code", rs.getString("code"));
        m.put("remark", rs.getString("remark"));
        try {
            Timestamp ts = rs.getTimestamp("created_at");
            m.put("createdAt", ts == null ? "" : FMT.format(ts.toLocalDateTime()));
        } catch (SQLException ignored) {
            m.put("createdAt", "");
        }
        return m;
    }
}
