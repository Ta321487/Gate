package com.thesis.service;

import com.thesis.config.JpaDb;
import com.thesis.config.JpaSupport;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 就诊人多档案：本人/家属代约。仅 HOSPITAL 出包启用。 */
public class PatientProfileStore {

    private static boolean enabled;
    private static Boolean tableReady;

    private PatientProfileStore() {}

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
                            + "WHERE table_schema=DATABASE() AND table_name='patient_profile'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static void require() {
        if (!ready()) throw new IllegalStateException("就诊人功能暂不可用");
    }

    private static Map<String, Object> mapRow(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("patientName", rs.getString("patient_name"));
        m.put("relationLabel", rs.getString("relation_label"));
        m.put("idHint", rs.getString("id_hint"));
        return m;
    }

    public static List<Map<String, Object>> listMine(String username) {
        require();
        String u = username == null ? "" : username.trim();
        return db().query(
                "SELECT * FROM patient_profile WHERE username=? ORDER BY id",
                (rs, i) -> mapRow(rs),
                u);
    }

    public static long add(String username, String patientName, String relation, String idHint) {
        require();
        String u = username == null ? "" : username.trim();
        String name = patientName == null ? "" : patientName.trim();
        if (u.isBlank()) throw new IllegalArgumentException("请先登录");
        if (name.isBlank()) throw new IllegalArgumentException("请填写就诊人姓名");
        if (name.length() > 32) name = name.substring(0, 32);
        String rel = relation == null || relation.isBlank() ? "本人" : relation.trim();
        if (rel.length() > 16) rel = rel.substring(0, 16);
        String hint = idHint == null ? "" : idHint.trim();
        if (hint.length() > 32) hint = hint.substring(0, 32);
        db().update(
                "INSERT INTO patient_profile (username, patient_name, relation_label, id_hint) VALUES (?,?,?,?)",
                u,
                name,
                rel,
                hint);
        Long id = db().queryForObject("SELECT LAST_INSERT_ID()", Long.class);
        return id == null ? 0L : id;
    }

    public static void remove(long id, String username) {
        require();
        if (id <= 0) return;
        db().update(
                "DELETE FROM patient_profile WHERE id=? AND username=?",
                id,
                username == null ? "" : username.trim());
    }
}
