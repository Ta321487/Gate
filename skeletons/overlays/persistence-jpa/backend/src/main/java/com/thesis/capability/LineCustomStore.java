package com.thesis.capability;

import com.thesis.config.JpaDb;
import com.thesis.config.JpaSupport;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 规格选项名单。刻字仍是手填，这里只维护有限选项。 */
public final class LineCustomStore {

    private static boolean enabled;

    private LineCustomStore() {}

    public static void configure(boolean on) {
        enabled = on;
    }

    public static boolean enabled() {
        return enabled;
    }

    public static List<Map<String, Object>> listEnabled() {
        if (!enabled) return List.of();
        try {
            return db().query(
                    "SELECT id, label FROM line_spec_option WHERE enabled=1 ORDER BY sort_no, id",
                    (rs, i) -> row(rs.getLong("id"), rs.getString("label"), 1, 0));
        } catch (Exception e) {
            return List.of();
        }
    }

    public static List<Map<String, Object>> listAll() {
        requireOn();
        try {
            return db().query(
                    "SELECT id, label, enabled, sort_no FROM line_spec_option ORDER BY sort_no, id",
                    (rs, i) -> row(rs.getLong("id"), rs.getString("label"), rs.getInt("enabled"), rs.getInt("sort_no")));
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置规格选项", e);
        }
    }

    public static void assertKnown(String choice) {
        if (!enabled || choice == null || choice.isBlank()) return;
        Integer n;
        try {
            n = db().queryForObject(
                    "SELECT COUNT(*) FROM line_spec_option WHERE enabled=1 AND label=?",
                    Integer.class, choice.trim());
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置规格选项", e);
        }
        if (n == null || n <= 0) throw new IllegalArgumentException("请从规格列表里选择");
    }

    public static Map<String, Object> save(Map<String, Object> body) {
        requireOn();
        Map<String, Object> in = body == null ? Map.of() : body;
        long id = lng(in.get("id"));
        String label = str(in.get("label"));
        int sortNo = num(in.get("sortNo"));
        int on = in.containsKey("enabled") && !flag(in.get("enabled")) ? 0 : 1;
        if (label.isBlank()) throw new IllegalArgumentException("请填写选项名称");
        if (label.length() > 64) label = label.substring(0, 64);
        try {
            if (id > 0) {
                db().update(
                        "UPDATE line_spec_option SET label=?, enabled=?, sort_no=? WHERE id=?",
                        label, on, sortNo, id);
            } else {
                db().update(
                        "INSERT INTO line_spec_option (label, enabled, sort_no) VALUES (?,?,?)",
                        label, on, sortNo);
            }
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置规格选项", e);
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("ok", true);
        return out;
    }

    private static Map<String, Object> row(long id, String label, int on, int sortNo) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", id);
        m.put("label", label == null ? "" : label);
        m.put("enabled", on != 0);
        m.put("sortNo", sortNo);
        return m;
    }

    private static void requireOn() {
        if (!enabled) throw new IllegalStateException("定制未开启");
    }

    private static JpaDb db() {
        return JpaSupport.db();
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static int num(Object o) {
        if (o instanceof Number n) return n.intValue();
        if (o == null || String.valueOf(o).isBlank()) return 0;
        try {
            return Integer.parseInt(String.valueOf(o).trim());
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    private static long lng(Object o) {
        if (o instanceof Number n) return n.longValue();
        if (o == null || String.valueOf(o).isBlank()) return 0L;
        try {
            return Long.parseLong(String.valueOf(o).trim());
        } catch (NumberFormatException e) {
            return 0L;
        }
    }

    private static boolean flag(Object o) {
        if (o instanceof Boolean b) return b;
        if (o instanceof Number n) return n.intValue() != 0;
        String s = str(o);
        return "1".equals(s) || "true".equalsIgnoreCase(s);
    }
}
