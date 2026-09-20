package com.thesis.service;

import com.thesis.config.JpaSupport;
import com.thesis.config.JpaDb;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 材料清单：必传项缺文件则拒绝提交。复用申请附件壳，不另做上传引擎。
 */
public class MaterialCheckStore {

    private static boolean enabled;
    private static Boolean tableReady;

    private MaterialCheckStore() {}

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
                            + "WHERE table_schema=DATABASE() AND table_name='material_checklist'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static void require() {
        if (!ready()) throw new IllegalStateException("材料清单功能暂不可用");
    }

    private static Map<String, Object> mapItem(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("title", rs.getString("title"));
        m.put("required", rs.getInt("required") == 1);
        m.put("sortOrder", rs.getInt("sort_order"));
        m.put("status", rs.getString("status"));
        return m;
    }

    public static List<Map<String, Object>> listOpen() {
        require();
        return db().query(
                "SELECT * FROM material_checklist WHERE status='available' ORDER BY sort_order, id",
                (rs, i) -> mapItem(rs));
    }

    /**
     * materials: [{checklistId, fileUrl}]。必传项必须各有文件。
     */
    @SuppressWarnings("unchecked")
    public static void assertSubmitted(Object materialsRaw) {
        if (!enabled || !ready()) return;
        List<Map<String, Object>> required = db().query(
                "SELECT id, title FROM material_checklist WHERE required=1 AND status='available' ORDER BY sort_order, id",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("title", rs.getString("title"));
                    return m;
                });
        if (required.isEmpty()) return;
        Map<Long, String> got = new LinkedHashMap<>();
        if (materialsRaw instanceof List<?> list) {
            for (Object row : list) {
                if (!(row instanceof Map<?, ?> map)) continue;
                Object idObj = map.get("checklistId");
                if (idObj == null) idObj = map.get("id");
                long id = 0L;
                if (idObj instanceof Number n) id = n.longValue();
                else if (idObj != null && !String.valueOf(idObj).isBlank()) {
                    try {
                        id = Long.parseLong(String.valueOf(idObj).trim());
                    } catch (Exception ignored) {
                        id = 0L;
                    }
                }
                String url = map.get("fileUrl") == null ? "" : String.valueOf(map.get("fileUrl")).trim();
                if (id > 0 && !url.isBlank() && !"null".equalsIgnoreCase(url)) {
                    got.put(id, url);
                }
            }
        }
        for (Map<String, Object> item : required) {
            long id = ((Number) item.get("id")).longValue();
            if (!got.containsKey(id)) {
                String title = item.get("title") == null ? "材料" : String.valueOf(item.get("title"));
                throw new IllegalStateException("缺少必传材料：「" + title + "」");
            }
        }
    }

    public static long addItem(String title, boolean required) {
        require();
        String t = title == null ? "" : title.trim();
        if (t.isBlank()) throw new IllegalArgumentException("请填写材料名");
        if (t.length() > 120) t = t.substring(0, 120);
        Integer max = db().queryForObject(
                "SELECT COALESCE(MAX(sort_order), 0) FROM material_checklist", Integer.class);
        int sort = (max == null ? 0 : max) + 1;
        db().update(
                "INSERT INTO material_checklist (title, required, sort_order, status) VALUES (?,?,?,'available')",
                t, required ? 1 : 0, sort);
        Long id = db().queryForObject("SELECT LAST_INSERT_ID()", Long.class);
        return id == null ? 0L : id;
    }

    public static void saveTicketMaterials(long ticketId, Object materialsRaw) {
        if (!enabled || !ready() || ticketId <= 0 || !(materialsRaw instanceof List<?> list)) return;
        for (Object row : list) {
            if (!(row instanceof Map<?, ?> map)) continue;
            Object idObj = map.get("checklistId");
            if (idObj == null) idObj = map.get("id");
            long cid = idObj instanceof Number n ? n.longValue() : 0L;
            String url = map.get("fileUrl") == null ? "" : String.valueOf(map.get("fileUrl")).trim();
            if (cid <= 0 || url.isBlank()) continue;
            if (url.length() > 255) url = url.substring(0, 255);
            db().update(
                    "INSERT INTO ticket_material (ticket_id, checklist_id, file_url) VALUES (?,?,?)",
                    ticketId, cid, url);
        }
    }
}
