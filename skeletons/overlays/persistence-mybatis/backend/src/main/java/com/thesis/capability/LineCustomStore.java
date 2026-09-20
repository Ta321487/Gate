package com.thesis.capability;

import com.thesis.config.MybatisSupport;
import com.thesis.mapper.LineCustomMapper;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 规格选项。规则与 jdbc 相同，只换数据访问。 */
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
            List<Map<String, Object>> rows = db().enabled();
            if (rows == null) return List.of();
            for (Map<String, Object> row : rows) row.put("enabled", true);
            return rows;
        } catch (Exception e) {
            return List.of();
        }
    }

    public static List<Map<String, Object>> listAll() {
        requireOn();
        try {
            List<Map<String, Object>> rows = db().all();
            if (rows == null) return List.of();
            for (Map<String, Object> row : rows) {
                Object on = row.get("enabled");
                row.put("enabled", on instanceof Number n ? n.intValue() != 0 : Boolean.TRUE.equals(on));
            }
            return rows;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置规格选项", e);
        }
    }

    public static void assertKnown(String choice) {
        if (!enabled || choice == null || choice.isBlank()) return;
        Integer n;
        try {
            n = db().countLabel(choice.trim());
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
            if (id > 0) db().update(id, label, on, sortNo);
            else db().insert(label, on, sortNo);
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置规格选项", e);
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("ok", true);
        return out;
    }

    private static void requireOn() {
        if (!enabled) throw new IllegalStateException("定制未开启");
    }

    private static LineCustomMapper db() {
        return MybatisSupport.mapper(LineCustomMapper.class);
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
        return 0L;
    }

    private static boolean flag(Object o) {
        if (o instanceof Boolean b) return b;
        if (o instanceof Number n) return n.intValue() != 0;
        String s = str(o);
        return "1".equals(s) || "true".equalsIgnoreCase(s);
    }
}
