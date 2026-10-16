package com.thesis.service;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 岗位菜单勾选（sys_post_menu）。
 * 某岗位没有任何行时，调用方继续用原岗位菜单包。
 */
public final class RoleMenuStore {

    private static Boolean tableReady;

    private RoleMenuStore() {}

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    public static synchronized void ensureTable() {
        if (Boolean.TRUE.equals(tableReady)) return;
        try {
            db().execute(
                    "CREATE TABLE IF NOT EXISTS sys_post_menu ("
                            + "staff_post VARCHAR(64) NOT NULL,"
                            + "menu_key VARCHAR(64) NOT NULL,"
                            + "PRIMARY KEY (staff_post, menu_key)"
                            + ")");
            tableReady = true;
        } catch (Exception e) {
            tableReady = false;
        }
    }

    public static Map<String, Object> loginMenuPayload(String staffPost) {
        Map<String, Object> m = new LinkedHashMap<>();
        List<String> keys = keysOf(staffPost);
        m.put("menuUsePacks", keys == null);
        m.put("menuKeys", keys == null ? List.of() : keys);
        return m;
    }

    public static boolean hasOverride(String staffPost) {
        ensureTable();
        if (!Boolean.TRUE.equals(tableReady)) return false;
        String p = staffPost == null ? "" : staffPost.trim();
        if (p.isBlank()) return false;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM sys_post_menu WHERE staff_post=?", Integer.class, p);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    /** 无覆盖时返回 null。 */
    public static List<String> keysOf(String staffPost) {
        if (!hasOverride(staffPost)) return null;
        return db().query(
                "SELECT menu_key FROM sys_post_menu WHERE staff_post=? ORDER BY menu_key",
                (rs, i) -> rs.getString("menu_key"),
                staffPost.trim());
    }

    public static List<String> replace(String staffPost, List<String> keys) {
        ensureTable();
        String p = staffPost == null ? "" : staffPost.trim();
        if (p.isBlank() || p.length() > 64) throw new IllegalArgumentException("岗位无效");
        Set<String> clean = new LinkedHashSet<>();
        if (keys != null) {
            for (String k : keys) {
                if (k == null) continue;
                String s = k.trim();
                if (s.isBlank() || s.length() > 64) continue;
                clean.add(s);
                if (clean.size() >= 80) break;
            }
        }
        db().update("DELETE FROM sys_post_menu WHERE staff_post=?", p);
        for (String k : clean) {
            db().update("INSERT INTO sys_post_menu (staff_post, menu_key) VALUES (?,?)", p, k);
        }
        List<String> saved = new ArrayList<>(clean);
        return saved;
    }
}
