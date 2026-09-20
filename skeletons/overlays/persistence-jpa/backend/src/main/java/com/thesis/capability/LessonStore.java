package com.thesis.capability;

import com.thesis.config.JpaDb;
import com.thesis.config.JpaSupport;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.Date;
import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 课时包与剩余节数。约课、取消仍走预约。 */
public final class LessonStore {

    private static boolean enabled;

    private LessonStore() {}

    public static void configure(boolean on) {
        enabled = on;
    }

    public static boolean enabled() {
        return enabled;
    }

    public static void assertRemain(String username) {
        if (!enabled) return;
        Map<String, Object> acc = account(username);
        int remain = acc == null ? 0 : ((Number) acc.get("remainSessions")).intValue();
        if (remain < 1) throw new IllegalStateException("剩余课时不足");
        if (expired(acc)) throw new IllegalStateException("课时已过期");
    }

    public static void spend(String username, long resvId) {
        if (!enabled || resvId <= 0) return;
        assertRemain(username);
        try {
            int n = db().update(
                    "UPDATE lesson_wallet SET remain_sessions=remain_sessions-1 "
                            + "WHERE username=? AND reservation_id IS NULL AND remain_sessions>0",
                    username);
            if (n == 0) throw new IllegalStateException("剩余课时不足");
            db().update(
                    "INSERT INTO lesson_wallet (username, reservation_id, total_sessions, remain_sessions) "
                            + "VALUES (?, ?, 0, 0)",
                    username, resvId);
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置课时", e);
        }
    }

    public static void refund(long resvId) {
        if (!enabled || resvId <= 0) return;
        try {
            List<String> users = db().query(
                    "SELECT username FROM lesson_wallet WHERE reservation_id=?",
                    (rs, i) -> rs.getString("username"),
                    resvId);
            if (users.isEmpty()) return;
            db().update("DELETE FROM lesson_wallet WHERE reservation_id=?", resvId);
            db().update(
                    "UPDATE lesson_wallet SET remain_sessions=remain_sessions+1 "
                            + "WHERE username=? AND reservation_id IS NULL",
                    users.get(0));
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置课时", e);
        }
    }

    public static List<Map<String, Object>> packs(boolean onlyEnabled) {
        requireOn();
        String sql = onlyEnabled
                ? "SELECT id, name, sessions, price_yuan, valid_days FROM lesson_pack WHERE enabled=1 ORDER BY id"
                : "SELECT id, name, sessions, price_yuan, valid_days, enabled FROM lesson_pack ORDER BY id";
        try {
            return db().query(sql, (rs, i) -> packRow(rs, !onlyEnabled));
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置课时", e);
        }
    }

    public static Map<String, Object> savePack(Map<String, Object> body) {
        requireOn();
        long id = lng(body == null ? null : body.get("id"));
        String name = str(body == null ? null : body.get("name"));
        if (name.isBlank()) throw new IllegalArgumentException("请填写包名");
        int sessions = toInt(body == null ? null : body.get("sessions"));
        if (sessions < 1) throw new IllegalArgumentException("请填写节数");
        BigDecimal price = money(body == null ? null : body.get("priceYuan"));
        int days = toInt(body == null ? null : body.get("validDays"));
        if (days < 1) throw new IllegalArgumentException("请填写有效天数");
        boolean on = body == null || body.get("enabled") == null || flag(body.get("enabled"));
        try {
            if (id > 0) {
                db().update(
                        "UPDATE lesson_pack SET name=?, sessions=?, price_yuan=?, valid_days=?, enabled=? WHERE id=?",
                        name, sessions, price, days, on ? 1 : 0, id);
            } else {
                db().update(
                        "INSERT INTO lesson_pack (name, sessions, price_yuan, valid_days, enabled) VALUES (?,?,?,?,?)",
                        name, sessions, price, days, on ? 1 : 0);
            }
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置课时", e);
        }
        return Map.of("ok", true);
    }

    public static Map<String, Object> mine(String username) {
        requireOn();
        Map<String, Object> acc = account(username);
        if (acc == null) {
            Map<String, Object> empty = new LinkedHashMap<>();
            empty.put("remainSessions", 0);
            empty.put("totalSessions", 0);
            empty.put("expireAt", "");
            return empty;
        }
        return acc;
    }

    public static Map<String, Object> buy(String username, long packId) {
        requireOn();
        Map<String, Object> pack = pack(packId);
        if (pack == null) throw new IllegalArgumentException("请选择课时包");
        int sessions = ((Number) pack.get("sessions")).intValue();
        int days = ((Number) pack.get("validDays")).intValue();
        LocalDate until = LocalDate.now().plusDays(Math.max(days, 1));
        try {
            Map<String, Object> acc = account(username);
            if (acc == null) {
                db().update(
                        "INSERT INTO lesson_wallet (username, total_sessions, remain_sessions, expire_at) "
                                + "VALUES (?,?,?,?)",
                        username, sessions, sessions, Date.valueOf(until));
            } else {
                String cur = str(acc.get("expireAt"));
                LocalDate keep = until;
                if (!cur.isBlank()) {
                    LocalDate old = LocalDate.parse(cur);
                    if (old.isAfter(until)) keep = old;
                }
                db().update(
                        "UPDATE lesson_wallet SET total_sessions=total_sessions+?, "
                                + "remain_sessions=remain_sessions+?, expire_at=? "
                                + "WHERE username=? AND reservation_id IS NULL",
                        sessions, sessions, Date.valueOf(keep), username);
            }
        } catch (IllegalArgumentException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置课时", e);
        }
        return mine(username);
    }

    public static List<Map<String, Object>> uses() {
        requireOn();
        try {
            return db().query(
                    "SELECT id, username, reservation_id, created_at FROM lesson_wallet "
                            + "WHERE reservation_id IS NOT NULL ORDER BY id DESC",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("id", rs.getLong("id"));
                        m.put("username", rs.getString("username"));
                        m.put("reservationId", rs.getLong("reservation_id"));
                        m.put("createdAt", String.valueOf(rs.getTimestamp("created_at")));
                        return m;
                    });
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置课时", e);
        }
    }

    private static Map<String, Object> account(String username) {
        try {
            List<Map<String, Object>> rows = db().query(
                    "SELECT id, total_sessions, remain_sessions, expire_at FROM lesson_wallet "
                            + "WHERE username=? AND reservation_id IS NULL ORDER BY id LIMIT 1",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("id", rs.getLong("id"));
                        m.put("totalSessions", rs.getInt("total_sessions"));
                        m.put("remainSessions", rs.getInt("remain_sessions"));
                        Date d = rs.getDate("expire_at");
                        m.put("expireAt", d == null ? "" : d.toLocalDate().toString());
                        return m;
                    },
                    username);
            return rows.isEmpty() ? null : rows.get(0);
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置课时", e);
        }
    }

    private static Map<String, Object> pack(long id) {
        if (id <= 0) return null;
        try {
            List<Map<String, Object>> rows = db().query(
                    "SELECT id, name, sessions, price_yuan, valid_days FROM lesson_pack "
                            + "WHERE id=? AND enabled=1",
                    (rs, i) -> packRow(rs, false),
                    id);
            return rows.isEmpty() ? null : rows.get(0);
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置课时", e);
        }
    }

    private static boolean expired(Map<String, Object> acc) {
        String day = str(acc.get("expireAt"));
        if (day.isBlank()) return false;
        return LocalDate.parse(day).isBefore(LocalDate.now());
    }

    private static Map<String, Object> packRow(java.sql.ResultSet rs, boolean withEnabled) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("name", rs.getString("name"));
        m.put("sessions", rs.getInt("sessions"));
        m.put("priceYuan", rs.getBigDecimal("price_yuan"));
        m.put("validDays", rs.getInt("valid_days"));
        if (withEnabled) m.put("enabled", rs.getInt("enabled") == 1);
        return m;
    }

    private static void requireOn() {
        if (!enabled) throw new IllegalStateException("课时未开启");
    }

    private static JpaDb db() {
        return JpaSupport.db();
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static long lng(Object o) {
        if (o instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(str(o));
        } catch (Exception e) {
            return 0L;
        }
    }

    private static int toInt(Object o) {
        if (o instanceof Number n) return n.intValue();
        try {
            return Integer.parseInt(str(o));
        } catch (Exception e) {
            return 0;
        }
    }

    private static boolean flag(Object o) {
        if (o instanceof Boolean b) return b;
        String text = str(o);
        return !"0".equals(text) && !"false".equalsIgnoreCase(text) && !text.isBlank();
    }

    private static BigDecimal money(Object o) {
        try {
            return new BigDecimal(str(o).isBlank() ? "0" : str(o)).setScale(2, RoundingMode.HALF_UP);
        } catch (Exception e) {
            return BigDecimal.ZERO.setScale(2, RoundingMode.HALF_UP);
        }
    }
}
