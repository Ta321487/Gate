package com.thesis.service;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.sql.Timestamp;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 最近登录记录与异地对照。 */
public final class LoginLogStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static Boolean tableReady;

    private LoginLogStore() {}

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    private static boolean ready() {
        if (tableReady != null) return tableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='sys_login_log'",
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

    private static String nz(String s, int max) {
        if (s == null) return "";
        String t = s.trim();
        if (t.length() > max) t = t.substring(0, max);
        return t;
    }

    /** 粗粒度来源提示：本机 / 内网 / 公网前缀。 */
    public static String geoHint(String ip) {
        String p = ip == null ? "" : ip.trim();
        if (p.isBlank() || "127.0.0.1".equals(p) || "0:0:0:0:0:0:0:1".equals(p) || "::1".equals(p)) {
            return "本机";
        }
        if (p.startsWith("192.168.") || p.startsWith("10.") || p.startsWith("172.")) {
            return "内网";
        }
        int dot = p.indexOf('.');
        if (dot > 0) return "外网-" + p.substring(0, Math.min(p.length(), dot + 4));
        return "外网";
    }

    public static void record(String username, String ip, String userAgent, boolean success) {
        if (!ready() || username == null || username.isBlank()) return;
        String geo = geoHint(ip);
        db().update(
                "INSERT INTO sys_login_log (username,ip,user_agent,geo_hint,success) VALUES (?,?,?,?,?)",
                username.trim(),
                nz(ip, 64),
                nz(userAgent, 255),
                geo,
                success ? 1 : 0);
    }

    /** 最近一次成功登录的 geo_hint（不含本次即将写入的）。 */
    public static String lastSuccessGeo(String username) {
        if (!ready() || username == null || username.isBlank()) return "";
        try {
            List<String> rows = db().query(
                    "SELECT geo_hint FROM sys_login_log WHERE username=? AND success=1 "
                            + "ORDER BY id DESC LIMIT 1",
                    (rs, i) -> rs.getString("geo_hint"),
                    username.trim());
            return rows == null || rows.isEmpty() || rows.get(0) == null ? "" : rows.get(0).trim();
        } catch (Exception e) {
            return "";
        }
    }

    public static List<Map<String, Object>> listMine(String username, int limit) {
        if (!ready() || username == null || username.isBlank()) return List.of();
        int lim = Math.max(1, Math.min(limit, 50));
        return db().query(
                "SELECT id,username,ip,user_agent,geo_hint,success,created_at FROM sys_login_log "
                        + "WHERE username=? ORDER BY id DESC LIMIT " + lim,
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("username", rs.getString("username"));
                    m.put("ip", rs.getString("ip"));
                    m.put("userAgent", rs.getString("user_agent"));
                    m.put("geoHint", rs.getString("geo_hint"));
                    m.put("success", rs.getInt("success") == 1);
                    m.put("createdAt", fmt(rs.getTimestamp("created_at")));
                    return m;
                },
                username.trim());
    }
}
