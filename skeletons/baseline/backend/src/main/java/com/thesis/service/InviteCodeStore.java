package com.thesis.service;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.sql.Timestamp;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** XA-02：注册邀请码浅表。 */
public final class InviteCodeStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static Boolean tableReady;

    private InviteCodeStore() {}

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    private static boolean ready() {
        if (tableReady != null) return tableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='sys_invite_code'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static String fmt(Timestamp ts) {
        return ts == null ? null : ts.toLocalDateTime().format(FMT);
    }

    public static void consumeOrThrow(String code) {
        if (!ready()) return;
        String c = code == null ? "" : code.trim();
        if (c.isBlank()) {
            throw new IllegalArgumentException("请填写邀请码");
        }
        List<Map<String, Object>> rows = db().query(
                "SELECT code,max_uses,used_count,enabled FROM sys_invite_code WHERE code=?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("code", rs.getString("code"));
                    m.put("maxUses", rs.getInt("max_uses"));
                    m.put("usedCount", rs.getInt("used_count"));
                    m.put("enabled", rs.getInt("enabled") == 1);
                    return m;
                },
                c);
        if (rows == null || rows.isEmpty()) {
            throw new IllegalArgumentException("邀请码无效");
        }
        Map<String, Object> row = rows.get(0);
        if (!Boolean.TRUE.equals(row.get("enabled"))) {
            throw new IllegalArgumentException("邀请码已停用");
        }
        int max = ((Number) row.get("maxUses")).intValue();
        int used = ((Number) row.get("usedCount")).intValue();
        if (max > 0 && used >= max) {
            throw new IllegalArgumentException("邀请码已用完");
        }
        int n = db().update(
                "UPDATE sys_invite_code SET used_count=used_count+1 WHERE code=? AND enabled=1 "
                        + "AND (max_uses=0 OR used_count<max_uses)",
                c);
        if (n <= 0) {
            throw new IllegalArgumentException("邀请码不可用");
        }
    }

    public static List<Map<String, Object>> listAll() {
        if (!ready()) return List.of();
        return db().query(
                "SELECT code,label,max_uses,used_count,enabled,created_at FROM sys_invite_code ORDER BY created_at DESC",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("code", rs.getString("code"));
                    m.put("label", rs.getString("label"));
                    m.put("maxUses", rs.getInt("max_uses"));
                    m.put("usedCount", rs.getInt("used_count"));
                    m.put("enabled", rs.getInt("enabled") == 1);
                    m.put("createdAt", fmt(rs.getTimestamp("created_at")));
                    return m;
                });
    }

    public static Map<String, Object> create(String code, String label, int maxUses) {
        if (!ready()) throw new IllegalStateException("邀请码表未就绪");
        String c = code == null ? "" : code.trim();
        if (c.isBlank() || c.length() > 64) {
            throw new IllegalArgumentException("邀请码须为 1–64 位");
        }
        String lb = label == null ? "" : label.trim();
        if (lb.length() > 128) lb = lb.substring(0, 128);
        int max = Math.max(0, maxUses);
        try {
            db().update(
                    "INSERT INTO sys_invite_code (code,label,max_uses,used_count,enabled) VALUES (?,?,?,0,1)",
                    c, lb, max);
        } catch (Exception e) {
            throw new IllegalStateException("邀请码已存在");
        }
        return Map.of("code", c, "label", lb, "maxUses", max, "usedCount", 0, "enabled", true);
    }

    public static void setEnabled(String code, boolean enabled) {
        if (!ready()) return;
        String c = code == null ? "" : code.trim();
        if (c.isBlank()) throw new IllegalArgumentException("邀请码不能为空");
        int n = db().update("UPDATE sys_invite_code SET enabled=? WHERE code=?", enabled ? 1 : 0, c);
        if (n <= 0) throw new IllegalArgumentException("邀请码不存在");
    }
}
