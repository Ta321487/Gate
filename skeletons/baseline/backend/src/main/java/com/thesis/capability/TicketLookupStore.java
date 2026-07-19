package com.thesis.capability;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.util.*;

/**
 * standalone 报修壳：楼栋/区域 + 房间/终端 + 类型 下拉数据源。
 * 表名由 DomainRuntimeBinder 按领域注入，空表名表示未启用。
 */
public final class TicketLookupStore {

    private static String SITE = "";
    private static String UNIT = "";
    private static String TYPE = "";
    private static String SITE_LABEL = "楼栋";
    private static String UNIT_LABEL = "房间";
    private static String TYPE_LABEL = "类型";

    private TicketLookupStore() {}

    public static void bind(
            String siteTable,
            String unitTable,
            String typeTable,
            String siteLabel,
            String unitLabel,
            String typeLabel) {
        SITE = blankToEmpty(siteTable);
        UNIT = blankToEmpty(unitTable);
        TYPE = blankToEmpty(typeTable);
        if (siteLabel != null && !siteLabel.isBlank()) SITE_LABEL = siteLabel.trim();
        if (unitLabel != null && !unitLabel.isBlank()) UNIT_LABEL = unitLabel.trim();
        if (typeLabel != null && !typeLabel.isBlank()) TYPE_LABEL = typeLabel.trim();
    }

    public static boolean enabled() {
        return !SITE.isEmpty() && !UNIT.isEmpty() && !TYPE.isEmpty();
    }

    public static Map<String, Object> meta() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("enabled", enabled());
        m.put("siteLabel", SITE_LABEL);
        m.put("unitLabel", UNIT_LABEL);
        m.put("typeLabel", TYPE_LABEL);
        return m;
    }

    public static List<Map<String, Object>> listSites() {
        if (SITE.isEmpty()) return List.of();
        return db().query(
                "SELECT id, name FROM " + SITE + " ORDER BY id",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("name", rs.getString("name"));
                    return m;
                });
    }

    public static List<Map<String, Object>> listUnits(Long siteId) {
        if (UNIT.isEmpty()) return List.of();
        if (siteId == null || siteId <= 0) {
            return db().query(
                    "SELECT id, building_id AS siteId, code FROM " + UNIT + " ORDER BY building_id, code",
                    (rs, i) -> unitRow(rs));
        }
        return db().query(
                "SELECT id, building_id AS siteId, code FROM " + UNIT + " WHERE building_id=? ORDER BY code",
                (rs, i) -> unitRow(rs),
                siteId);
    }

    public static List<Map<String, Object>> listTypes() {
        if (TYPE.isEmpty()) return List.of();
        return db().query(
                "SELECT id, name FROM " + TYPE + " ORDER BY sort_no, id",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("name", rs.getString("name"));
                    return m;
                });
    }

    /** 由房间拼地点文案，供列表展示。 */
    public static String formatLocation(long unitId) {
        if (UNIT.isEmpty() || SITE.isEmpty() || unitId <= 0) return "";
        List<Map<String, Object>> rows = db().query(
                "SELECT u.code AS code, s.name AS siteName FROM " + UNIT + " u "
                        + "JOIN " + SITE + " s ON s.id = u.building_id WHERE u.id=?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("code", rs.getString("code"));
                    m.put("siteName", rs.getString("siteName"));
                    return m;
                },
                unitId);
        if (rows.isEmpty()) return "";
        Map<String, Object> r = rows.get(0);
        return str(r.get("siteName")) + " " + str(r.get("code"));
    }

    public static String typeName(long typeId) {
        if (TYPE.isEmpty() || typeId <= 0) return "";
        try {
            return db().queryForObject("SELECT name FROM " + TYPE + " WHERE id=?", String.class, typeId);
        } catch (Exception e) {
            return "";
        }
    }

    public static boolean unitExists(long unitId) {
        if (UNIT.isEmpty() || unitId <= 0) return false;
        Integer n = db().queryForObject("SELECT COUNT(*) FROM " + UNIT + " WHERE id=?", Integer.class, unitId);
        return n != null && n > 0;
    }

    public static boolean typeExists(long typeId) {
        if (TYPE.isEmpty() || typeId <= 0) return false;
        Integer n = db().queryForObject("SELECT COUNT(*) FROM " + TYPE + " WHERE id=?", Integer.class, typeId);
        return n != null && n > 0;
    }

    public static Map<String, Object> createSite(String name, String remark) {
        requireSite();
        String n = requireText(name, SITE_LABEL + "名称");
        db().update(
                "INSERT INTO " + SITE + " (name, remark) VALUES (?, ?)",
                n,
                remark == null ? "" : remark.trim());
        Long id = db().queryForObject("SELECT MAX(id) FROM " + SITE + " WHERE name=?", Long.class, n);
        return siteById(id == null ? 0L : id);
    }

    public static Map<String, Object> updateSite(long id, String name, String remark) {
        requireSite();
        if (siteById(id) == null) throw new IllegalArgumentException(SITE_LABEL + "不存在");
        String n = requireText(name, SITE_LABEL + "名称");
        db().update(
                "UPDATE " + SITE + " SET name=?, remark=? WHERE id=?",
                n,
                remark == null ? "" : remark.trim(),
                id);
        return siteById(id);
    }

    public static void deleteSite(long id) {
        requireSite();
        if (siteById(id) == null) throw new IllegalArgumentException(SITE_LABEL + "不存在");
        Integer units = db().queryForObject(
                "SELECT COUNT(*) FROM " + UNIT + " WHERE building_id=?", Integer.class, id);
        if (units != null && units > 0) {
            throw new IllegalArgumentException("请先删除下属" + UNIT_LABEL);
        }
        db().update("DELETE FROM " + SITE + " WHERE id=?", id);
    }

    public static Map<String, Object> createUnit(long siteId, String code, Integer capacity) {
        requireUnit();
        if (siteById(siteId) == null) throw new IllegalArgumentException(SITE_LABEL + "不存在");
        String c = requireText(code, UNIT_LABEL + "编号");
        int cap = capacity == null || capacity <= 0 ? 4 : capacity;
        db().update(
                "INSERT INTO " + UNIT + " (building_id, code, capacity) VALUES (?, ?, ?)",
                siteId, c, cap);
        Long id = db().queryForObject(
                "SELECT id FROM " + UNIT + " WHERE building_id=? AND code=?", Long.class, siteId, c);
        return unitById(id == null ? 0L : id);
    }

    public static Map<String, Object> updateUnit(long id, Long siteId, String code, Integer capacity) {
        requireUnit();
        Map<String, Object> cur = unitById(id);
        if (cur == null) throw new IllegalArgumentException(UNIT_LABEL + "不存在");
        long sid = siteId != null && siteId > 0 ? siteId : toLong(cur.get("siteId"));
        if (siteById(sid) == null) throw new IllegalArgumentException(SITE_LABEL + "不存在");
        String c = requireText(code, UNIT_LABEL + "编号");
        int cap = capacity == null || capacity <= 0 ? 4 : capacity;
        db().update(
                "UPDATE " + UNIT + " SET building_id=?, code=?, capacity=? WHERE id=?",
                sid, c, cap, id);
        return unitById(id);
    }

    public static void deleteUnit(long id) {
        requireUnit();
        if (unitById(id) == null) throw new IllegalArgumentException(UNIT_LABEL + "不存在");
        db().update("DELETE FROM " + UNIT + " WHERE id=?", id);
    }

    public static Map<String, Object> createType(String name, Integer sortNo) {
        requireType();
        String n = requireText(name, TYPE_LABEL + "名称");
        int sort = sortNo == null ? 0 : sortNo;
        db().update("INSERT INTO " + TYPE + " (name, sort_no) VALUES (?, ?)", n, sort);
        Long id = db().queryForObject("SELECT id FROM " + TYPE + " WHERE name=?", Long.class, n);
        return typeById(id == null ? 0L : id);
    }

    public static Map<String, Object> updateType(long id, String name, Integer sortNo) {
        requireType();
        if (typeById(id) == null) throw new IllegalArgumentException(TYPE_LABEL + "不存在");
        String n = requireText(name, TYPE_LABEL + "名称");
        int sort = sortNo == null ? 0 : sortNo;
        db().update("UPDATE " + TYPE + " SET name=?, sort_no=? WHERE id=?", n, sort, id);
        return typeById(id);
    }

    public static void deleteType(long id) {
        requireType();
        if (typeById(id) == null) throw new IllegalArgumentException(TYPE_LABEL + "不存在");
        db().update("DELETE FROM " + TYPE + " WHERE id=?", id);
    }

    public static List<Map<String, Object>> listSitesAdmin() {
        if (SITE.isEmpty()) return List.of();
        return db().query(
                "SELECT id, name, remark FROM " + SITE + " ORDER BY id",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("name", rs.getString("name"));
                    m.put("remark", rs.getString("remark"));
                    return m;
                });
    }

    public static List<Map<String, Object>> listUnitsAdmin(Long siteId) {
        if (UNIT.isEmpty()) return List.of();
        String sql = "SELECT id, building_id AS siteId, code, capacity FROM " + UNIT;
        if (siteId != null && siteId > 0) {
            return db().query(
                    sql + " WHERE building_id=? ORDER BY building_id, code",
                    (rs, i) -> unitAdminRow(rs),
                    siteId);
        }
        return db().query(sql + " ORDER BY building_id, code", (rs, i) -> unitAdminRow(rs));
    }

    public static List<Map<String, Object>> listTypesAdmin() {
        if (TYPE.isEmpty()) return List.of();
        return db().query(
                "SELECT id, name, sort_no AS sortNo FROM " + TYPE + " ORDER BY sort_no, id",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("name", rs.getString("name"));
                    m.put("sortNo", rs.getInt("sortNo"));
                    return m;
                });
    }

    private static Map<String, Object> siteById(long id) {
        if (SITE.isEmpty() || id <= 0) return null;
        List<Map<String, Object>> rows = db().query(
                "SELECT id, name, remark FROM " + SITE + " WHERE id=?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("name", rs.getString("name"));
                    m.put("remark", rs.getString("remark"));
                    return m;
                },
                id);
        return rows.isEmpty() ? null : rows.get(0);
    }

    private static Map<String, Object> unitById(long id) {
        if (UNIT.isEmpty() || id <= 0) return null;
        List<Map<String, Object>> rows = db().query(
                "SELECT id, building_id AS siteId, code, capacity FROM " + UNIT + " WHERE id=?",
                (rs, i) -> unitAdminRow(rs),
                id);
        return rows.isEmpty() ? null : rows.get(0);
    }

    private static Map<String, Object> typeById(long id) {
        if (TYPE.isEmpty() || id <= 0) return null;
        List<Map<String, Object>> rows = db().query(
                "SELECT id, name, sort_no AS sortNo FROM " + TYPE + " WHERE id=?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("name", rs.getString("name"));
                    m.put("sortNo", rs.getInt("sortNo"));
                    return m;
                },
                id);
        return rows.isEmpty() ? null : rows.get(0);
    }

    private static Map<String, Object> unitAdminRow(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("siteId", rs.getLong("siteId"));
        m.put("code", rs.getString("code"));
        m.put("name", rs.getString("code"));
        m.put("capacity", rs.getInt("capacity"));
        return m;
    }

    private static Map<String, Object> unitRow(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("siteId", rs.getLong("siteId"));
        m.put("code", rs.getString("code"));
        m.put("name", rs.getString("code"));
        return m;
    }

    private static void requireSite() {
        if (SITE.isEmpty()) throw new IllegalStateException("未配置" + SITE_LABEL + "表");
    }

    private static void requireUnit() {
        if (UNIT.isEmpty()) throw new IllegalStateException("未配置" + UNIT_LABEL + "表");
        requireSite();
    }

    private static void requireType() {
        if (TYPE.isEmpty()) throw new IllegalStateException("未配置" + TYPE_LABEL + "表");
    }

    private static String requireText(String v, String label) {
        if (v == null || v.isBlank()) throw new IllegalArgumentException(label + "不能为空");
        return v.trim();
    }

    private static long toLong(Object o) {
        if (o == null) return 0L;
        if (o instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(String.valueOf(o));
        } catch (Exception e) {
            return 0L;
        }
    }

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    private static String blankToEmpty(String s) {
        return s == null || s.isBlank() ? "" : s.trim();
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o);
    }
}
