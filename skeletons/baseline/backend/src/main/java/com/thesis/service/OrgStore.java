package com.thesis.service;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.util.*;

/** 浅组织树（sys_org）。 */
public final class OrgStore {

    private static Boolean tableReady;

    private OrgStore() {}

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    public static synchronized void ensureTable() {
        if (Boolean.TRUE.equals(tableReady)) return;
        try {
            db().execute(
                    "CREATE TABLE IF NOT EXISTS sys_org ("
                            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
                            + "parent_id BIGINT NULL,"
                            + "name VARCHAR(64) NOT NULL,"
                            + "sort_order INT NOT NULL DEFAULT 0,"
                            + "enabled TINYINT NOT NULL DEFAULT 1,"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "KEY idx_org_parent (parent_id, sort_order)"
                            + ")");
            tableReady = true;
            seedIfEmpty();
        } catch (Exception e) {
            tableReady = false;
        }
    }

    private static void seedIfEmpty() {
        try {
            Integer n = db().queryForObject("SELECT COUNT(*) FROM sys_org", Integer.class);
            if (n != null && n > 0) return;
            db().update("INSERT INTO sys_org (parent_id, name, sort_order, enabled) VALUES (NULL,?,?,1)", "本部", 0);
        } catch (Exception ignored) {
        }
    }

    private static Map<String, Object> row(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        long id = rs.getLong("id");
        m.put("id", id);
        long parent = rs.getLong("parent_id");
        m.put("parentId", rs.wasNull() ? null : parent);
        m.put("name", rs.getString("name"));
        m.put("sortOrder", rs.getInt("sort_order"));
        m.put("enabled", rs.getInt("enabled") > 0);
        return m;
    }

    public static List<Map<String, Object>> listAll() {
        ensureTable();
        if (!Boolean.TRUE.equals(tableReady)) return List.of();
        return db().query(
                "SELECT * FROM sys_org ORDER BY sort_order ASC, id ASC",
                (rs, i) -> row(rs));
    }

    public static List<Map<String, Object>> options() {
        List<Map<String, Object>> all = listAll();
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> m : all) {
            if (!Boolean.TRUE.equals(m.get("enabled"))) continue;
            Map<String, Object> o = new LinkedHashMap<>();
            o.put("id", m.get("id"));
            o.put("parentId", m.get("parentId"));
            o.put("name", m.get("name"));
            out.add(o);
        }
        return out;
    }

    public static Map<String, Object> create(String name, Long parentId, Integer sortOrder) {
        ensureTable();
        String n = requireName(name);
        assertParent(parentId);
        int sort = sortOrder == null ? 100 : sortOrder;
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO sys_org (parent_id, name, sort_order, enabled) VALUES (?,?,?,1)",
                    Statement.RETURN_GENERATED_KEYS);
            if (parentId == null) ps.setObject(1, null);
            else ps.setLong(1, parentId);
            ps.setString(2, n);
            ps.setInt(3, sort);
            return ps;
        }, kh);
        Number key = kh.getKey();
        return get(key == null ? 0L : key.longValue());
    }

    public static Map<String, Object> update(long id, String name, Long parentId, Integer sortOrder, Boolean on) {
        Map<String, Object> cur = get(id);
        if (cur.isEmpty()) throw new IllegalArgumentException("组织不存在");
        if (parentId != null && parentId == id) throw new IllegalArgumentException("不能把自己设为上级");
        if (parentId != null && subtreeIds(id).contains(parentId)) {
            throw new IllegalArgumentException("不能挂到自己的下级");
        }
        String n = name == null ? String.valueOf(cur.get("name")) : requireName(name);
        Long parent = parentId;
        if (parentId == null && !explicitClear(parentId)) {
            parent = cur.get("parentId") instanceof Number num ? num.longValue() : null;
        }
        assertParent(parent);
        int sort = sortOrder == null
                ? ((Number) cur.getOrDefault("sortOrder", 0)).intValue()
                : sortOrder;
        int en = on == null ? (Boolean.TRUE.equals(cur.get("enabled")) ? 1 : 0) : (on ? 1 : 0);
        db().update("UPDATE sys_org SET parent_id=?, name=?, sort_order=?, enabled=? WHERE id=?",
                parent, n, sort, en, id);
        return get(id);
    }

    public static void delete(long id) {
        ensureTable();
        Integer kids = db().queryForObject(
                "SELECT COUNT(*) FROM sys_org WHERE parent_id=?", Integer.class, id);
        if (kids != null && kids > 0) throw new IllegalArgumentException("请先删除下级组织");
        db().update("DELETE FROM sys_org WHERE id=?", id);
    }

    public static Map<String, Object> get(long id) {
        ensureTable();
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM sys_org WHERE id=?", (rs, i) -> row(rs), id);
        return rows.isEmpty() ? Map.of() : rows.get(0);
    }

    /** 含自身的子树 id。 */
    public static Set<Long> subtreeIds(long rootId) {
        List<Map<String, Object>> all = listAll();
        Map<Long, List<Long>> children = new HashMap<>();
        for (Map<String, Object> m : all) {
            Long id = ((Number) m.get("id")).longValue();
            Object p = m.get("parentId");
            if (p instanceof Number num) {
                children.computeIfAbsent(num.longValue(), k -> new ArrayList<>()).add(id);
            }
        }
        Set<Long> out = new LinkedHashSet<>();
        ArrayDeque<Long> q = new ArrayDeque<>();
        q.add(rootId);
        while (!q.isEmpty()) {
            Long cur = q.removeFirst();
            if (!out.add(cur)) continue;
            for (Long c : children.getOrDefault(cur, List.of())) q.add(c);
        }
        return out;
    }

    private static void assertParent(Long parentId) {
        if (parentId == null) return;
        if (get(parentId).isEmpty()) throw new IllegalArgumentException("上级组织不存在");
    }

    private static boolean explicitClear(Long parentId) {
        return parentId == null;
    }

    private static String requireName(String raw) {
        String s = raw == null ? "" : raw.trim();
        if (s.isBlank()) throw new IllegalArgumentException("名称不能为空");
        if (s.length() > 64) throw new IllegalArgumentException("名称过长");
        return s;
    }
}
