package com.thesis.capability;

import com.thesis.config.MybatisSupport;
import com.thesis.mapper.TicketLookupMapper;

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

    private static TicketLookupMapper mapper() {
        return MybatisSupport.mapper(TicketLookupMapper.class);
    }

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
        return shapeSites(mapper().selectSites(SITE), false);
    }

    public static List<Map<String, Object>> listUnits(Long siteId) {
        if (UNIT.isEmpty()) return List.of();
        return shapeUnits(mapper().selectUnits(UNIT, siteId), false);
    }

    public static List<Map<String, Object>> listTypes() {
        if (TYPE.isEmpty()) return List.of();
        List<Map<String, Object>> raw = mapper().selectTypes(TYPE);
        List<Map<String, Object>> out = new ArrayList<>();
        if (raw != null) {
            for (Map<String, Object> r : raw) {
                Map<String, Object> m = new LinkedHashMap<>();
                m.put("id", r.get("id"));
                m.put("name", r.get("name"));
                out.add(m);
            }
        }
        return out;
    }

    /** 由房间拼地点文案，供列表展示。 */
    public static String formatLocation(long unitId) {
        if (UNIT.isEmpty() || SITE.isEmpty() || unitId <= 0) return "";
        Map<String, Object> r = mapper().selectLocation(UNIT, SITE, unitId);
        if (r == null) return "";
        return str(r.get("siteName")) + " " + str(r.get("code"));
    }

    public static String typeName(long typeId) {
        if (TYPE.isEmpty() || typeId <= 0) return "";
        try {
            String n = mapper().typeName(TYPE, typeId);
            return n == null ? "" : n;
        } catch (Exception e) {
            return "";
        }
    }

    public static boolean unitExists(long unitId) {
        if (UNIT.isEmpty() || unitId <= 0) return false;
        return mapper().countUnit(UNIT, unitId) > 0;
    }

    public static boolean typeExists(long typeId) {
        if (TYPE.isEmpty() || typeId <= 0) return false;
        return mapper().countType(TYPE, typeId) > 0;
    }

    public static Map<String, Object> createSite(String name, String remark) {
        requireSite();
        String n = requireText(name, SITE_LABEL + "名称");
        mapper().insertSite(SITE, n, remark == null ? "" : remark.trim());
        Long id = mapper().maxSiteIdByName(SITE, n);
        return siteById(id == null ? 0L : id);
    }

    public static Map<String, Object> updateSite(long id, String name, String remark) {
        requireSite();
        if (siteById(id) == null) throw new IllegalArgumentException(SITE_LABEL + "不存在");
        String n = requireText(name, SITE_LABEL + "名称");
        mapper().updateSite(SITE, id, n, remark == null ? "" : remark.trim());
        return siteById(id);
    }

    public static void deleteSite(long id) {
        requireSite();
        if (siteById(id) == null) throw new IllegalArgumentException(SITE_LABEL + "不存在");
        if (mapper().countUnitsBySite(UNIT, id) > 0) {
            throw new IllegalArgumentException("请先删除下属" + UNIT_LABEL);
        }
        mapper().deleteSite(SITE, id);
    }

    public static Map<String, Object> createUnit(long siteId, String code, Integer capacity) {
        requireUnit();
        if (siteById(siteId) == null) throw new IllegalArgumentException(SITE_LABEL + "不存在");
        String c = requireText(code, UNIT_LABEL + "编号");
        int cap = capacity == null || capacity <= 0 ? 4 : capacity;
        mapper().insertUnit(UNIT, siteId, c, cap);
        Long id = mapper().unitIdBySiteCode(UNIT, siteId, c);
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
        mapper().updateUnit(UNIT, id, sid, c, cap);
        return unitById(id);
    }

    public static void deleteUnit(long id) {
        requireUnit();
        if (unitById(id) == null) throw new IllegalArgumentException(UNIT_LABEL + "不存在");
        mapper().deleteUnit(UNIT, id);
    }

    public static Map<String, Object> createType(String name, Integer sortNo) {
        requireType();
        String n = requireText(name, TYPE_LABEL + "名称");
        int sort = sortNo == null ? 0 : sortNo;
        mapper().insertType(TYPE, n, sort);
        Long id = mapper().typeIdByName(TYPE, n);
        return typeById(id == null ? 0L : id);
    }

    public static Map<String, Object> updateType(long id, String name, Integer sortNo) {
        requireType();
        if (typeById(id) == null) throw new IllegalArgumentException(TYPE_LABEL + "不存在");
        String n = requireText(name, TYPE_LABEL + "名称");
        int sort = sortNo == null ? 0 : sortNo;
        mapper().updateType(TYPE, id, n, sort);
        return typeById(id);
    }

    public static void deleteType(long id) {
        requireType();
        if (typeById(id) == null) throw new IllegalArgumentException(TYPE_LABEL + "不存在");
        mapper().deleteType(TYPE, id);
    }

    public static List<Map<String, Object>> listSitesAdmin() {
        if (SITE.isEmpty()) return List.of();
        return shapeSites(mapper().selectSitesAdmin(SITE), true);
    }

    public static List<Map<String, Object>> listUnitsAdmin(Long siteId) {
        if (UNIT.isEmpty()) return List.of();
        return shapeUnits(mapper().selectUnitsAdmin(UNIT, siteId), true);
    }

    public static List<Map<String, Object>> listTypesAdmin() {
        if (TYPE.isEmpty()) return List.of();
        List<Map<String, Object>> raw = mapper().selectTypesAdmin(TYPE);
        List<Map<String, Object>> out = new ArrayList<>();
        if (raw != null) {
            for (Map<String, Object> r : raw) {
                Map<String, Object> m = new LinkedHashMap<>();
                m.put("id", r.get("id"));
                m.put("name", r.get("name"));
                m.put("sortNo", r.get("sortNo") != null ? r.get("sortNo") : r.get("sort_no"));
                out.add(m);
            }
        }
        return out;
    }

    private static List<Map<String, Object>> shapeSites(List<Map<String, Object>> raw, boolean admin) {
        List<Map<String, Object>> out = new ArrayList<>();
        if (raw == null) return out;
        for (Map<String, Object> r : raw) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id", r.get("id"));
            m.put("name", r.get("name"));
            if (admin) m.put("remark", r.get("remark"));
            out.add(m);
        }
        return out;
    }

    private static List<Map<String, Object>> shapeUnits(List<Map<String, Object>> raw, boolean admin) {
        List<Map<String, Object>> out = new ArrayList<>();
        if (raw == null) return out;
        for (Map<String, Object> r : raw) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id", r.get("id"));
            Object sid = r.get("siteId") != null ? r.get("siteId") : r.get("building_id");
            m.put("siteId", sid);
            m.put("code", r.get("code"));
            m.put("name", r.get("code"));
            if (admin) m.put("capacity", r.get("capacity"));
            out.add(m);
        }
        return out;
    }

    private static Map<String, Object> siteById(long id) {
        if (SITE.isEmpty() || id <= 0) return null;
        Map<String, Object> r = mapper().selectSiteById(SITE, id);
        if (r == null) return null;
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", r.get("id"));
        m.put("name", r.get("name"));
        m.put("remark", r.get("remark"));
        return m;
    }

    private static Map<String, Object> unitById(long id) {
        if (UNIT.isEmpty() || id <= 0) return null;
        Map<String, Object> r = mapper().selectUnitById(UNIT, id);
        if (r == null) return null;
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", r.get("id"));
        Object sid = r.get("siteId") != null ? r.get("siteId") : r.get("building_id");
        m.put("siteId", sid);
        m.put("code", r.get("code"));
        m.put("name", r.get("code"));
        m.put("capacity", r.get("capacity"));
        return m;
    }

    private static Map<String, Object> typeById(long id) {
        if (TYPE.isEmpty() || id <= 0) return null;
        Map<String, Object> r = mapper().selectTypeById(TYPE, id);
        if (r == null) return null;
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", r.get("id"));
        m.put("name", r.get("name"));
        m.put("sortNo", r.get("sortNo") != null ? r.get("sortNo") : r.get("sort_no"));
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

    private static String blankToEmpty(String s) {
        return s == null || s.isBlank() ? "" : s.trim();
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o);
    }
}
