package com.thesis.service;

import com.thesis.config.MybatisSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 车位包月次卡：浅计数。仅 PARKING 出包启用。 */
public class ParkingPassStore {

    private static boolean enabled;
    private static Boolean tableReady;

    private ParkingPassStore() {}

    public static void configure(boolean on) {
        enabled = on;
        tableReady = null;
    }

    public static boolean enabled() {
        return enabled;
    }

    private static JdbcTemplate db() {
        return MybatisSupport.db();
    }

    public static boolean ready() {
        if (!enabled) return false;
        if (tableReady != null) return tableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='parking_pass'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static void require() {
        if (!ready()) throw new IllegalStateException("停车次卡功能暂不可用");
    }

    private static Map<String, Object> mapRow(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("packName", rs.getString("pack_name"));
        m.put("remainCount", rs.getInt("remain_count"));
        return m;
    }

    public static List<Map<String, Object>> listMine(String username) {
        require();
        String u = username == null ? "" : username.trim();
        return db().query(
                "SELECT * FROM parking_pass WHERE username=? ORDER BY id",
                (rs, i) -> mapRow(rs),
                u);
    }

    public static List<Map<String, Object>> listAll(int limit) {
        require();
        int lim = Math.max(1, Math.min(200, limit));
        return db().query(
                "SELECT * FROM parking_pass ORDER BY id DESC LIMIT " + lim,
                (rs, i) -> mapRow(rs));
    }

    public static int totalRemain(String username) {
        if (!ready()) return 0;
        String u = username == null ? "" : username.trim();
        try {
            Integer n = db().queryForObject(
                    "SELECT COALESCE(SUM(remain_count),0) FROM parking_pass WHERE username=?",
                    Integer.class,
                    u);
            return n == null ? 0 : n;
        } catch (Exception e) {
            return 0;
        }
    }

    public static long grant(String username, String packName, int count) {
        require();
        String u = username == null ? "" : username.trim();
        if (u.isBlank()) throw new IllegalArgumentException("请填写用户名");
        if (count <= 0) throw new IllegalArgumentException("次数须大于 0");
        String pack = packName == null || packName.isBlank() ? "包月次卡" : packName.trim();
        if (pack.length() > 64) pack = pack.substring(0, 64);
        List<Map<String, Object>> existing = db().query(
                "SELECT id, remain_count FROM parking_pass WHERE username=? AND pack_name=? LIMIT 1",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("remain", rs.getInt("remain_count"));
                    return m;
                },
                u,
                pack);
        if (!existing.isEmpty()) {
            long id = ((Number) existing.get(0).get("id")).longValue();
            int cur = ((Number) existing.get(0).get("remain")).intValue();
            db().update("UPDATE parking_pass SET remain_count=? WHERE id=?", cur + count, id);
            return id;
        }
        db().update(
                "INSERT INTO parking_pass (username, pack_name, remain_count) VALUES (?,?,?)",
                u,
                pack,
                count);
        Long id = db().queryForObject("SELECT LAST_INSERT_ID()", Long.class);
        return id == null ? 0L : id;
    }

    public static boolean spendOne(String username) {
        if (!ready()) return false;
        String u = username == null ? "" : username.trim();
        List<Map<String, Object>> rows = db().query(
                "SELECT id, remain_count FROM parking_pass WHERE username=? AND remain_count>0 ORDER BY id LIMIT 1",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("remain", rs.getInt("remain_count"));
                    return m;
                },
                u);
        if (rows.isEmpty()) return false;
        long id = ((Number) rows.get(0).get("id")).longValue();
        int updated = db().update(
                "UPDATE parking_pass SET remain_count=remain_count-1 WHERE id=? AND remain_count>0", id);
        return updated > 0;
    }

    public static void refundOne(String username) {
        if (!ready()) return;
        String u = username == null ? "" : username.trim();
        List<Map<String, Object>> rows = db().query(
                "SELECT id FROM parking_pass WHERE username=? ORDER BY id LIMIT 1",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    return m;
                },
                u);
        if (rows.isEmpty()) {
            grant(u, "包月次卡", 1);
            return;
        }
        long id = ((Number) rows.get(0).get("id")).longValue();
        db().update("UPDATE parking_pass SET remain_count=remain_count+1 WHERE id=?", id);
    }
}