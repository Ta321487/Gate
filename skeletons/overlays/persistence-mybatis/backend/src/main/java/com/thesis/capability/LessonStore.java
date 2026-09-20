package com.thesis.capability;

import com.thesis.config.MybatisSupport;
import com.thesis.mapper.LessonMapper;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 课时包与剩余节数。约课、取消仍走预约。数据访问走 LessonMapper。 */
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
        int remain = acc == null ? 0 : num(acc.get("remainSessions"));
        if (remain < 1) throw new IllegalStateException("剩余课时不足");
        if (expired(acc)) throw new IllegalStateException("课时已过期");
    }

    public static void spend(String username, long resvId) {
        if (!enabled || resvId <= 0) return;
        assertRemain(username);
        try {
            int n = mapper().decRemain(username);
            if (n == 0) throw new IllegalStateException("剩余课时不足");
            mapper().insertUse(username, resvId);
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置课时", e);
        }
    }

    public static void refund(long resvId) {
        if (!enabled || resvId <= 0) return;
        try {
            List<String> users = mapper().useUsers(resvId);
            if (users == null || users.isEmpty()) return;
            mapper().deleteUse(resvId);
            mapper().incRemain(users.get(0));
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置课时", e);
        }
    }

    public static List<Map<String, Object>> packs(boolean onlyEnabled) {
        requireOn();
        try {
            List<Map<String, Object>> rows = onlyEnabled ? mapper().packsOn() : mapper().packsAll();
            List<Map<String, Object>> out = new java.util.ArrayList<>();
            if (rows != null) {
                for (Map<String, Object> row : rows) out.add(packRow(row, !onlyEnabled));
            }
            return out;
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
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", id);
        row.put("name", name);
        row.put("sessions", sessions);
        row.put("price", price);
        row.put("days", days);
        row.put("enabled", on ? 1 : 0);
        try {
            if (id > 0) mapper().updatePack(row);
            else mapper().insertPack(row);
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
        Map<String, Object> pack;
        try {
            pack = mapper().packOn(packId);
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置课时", e);
        }
        if (pack == null || pack.isEmpty()) throw new IllegalArgumentException("请选择课时包");
        Map<String, Object> view = packRow(pack, false);
        int sessions = num(view.get("sessions"));
        int days = num(view.get("validDays"));
        LocalDate until = LocalDate.now().plusDays(Math.max(days, 1));
        try {
            Map<String, Object> acc = account(username);
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("username", username);
            row.put("sessions", sessions);
            if (acc == null) {
                row.put("expireAt", until.toString());
                mapper().insertAccount(row);
            } else {
                String cur = str(acc.get("expireAt"));
                LocalDate keep = until;
                if (!cur.isBlank()) {
                    LocalDate old = LocalDate.parse(cur.length() >= 10 ? cur.substring(0, 10) : cur);
                    if (old.isAfter(until)) keep = old;
                }
                row.put("expireAt", keep.toString());
                mapper().addSessions(row);
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
            List<Map<String, Object>> rows = mapper().uses();
            List<Map<String, Object>> out = new java.util.ArrayList<>();
            if (rows == null) return out;
            for (Map<String, Object> row : rows) {
                Map<String, Object> m = new LinkedHashMap<>();
                m.put("id", lng(first(row, "id")));
                m.put("username", str(first(row, "username")));
                m.put("reservationId", lng(first(row, "reservation_id", "reservationId")));
                m.put("createdAt", str(first(row, "created_at", "createdAt")));
                out.add(m);
            }
            return out;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置课时", e);
        }
    }

    private static Map<String, Object> account(String username) {
        try {
            Map<String, Object> row = mapper().account(username);
            if (row == null || row.isEmpty()) return null;
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id", lng(first(row, "id")));
            m.put("totalSessions", num(first(row, "total_sessions", "totalSessions")));
            m.put("remainSessions", num(first(row, "remain_sessions", "remainSessions")));
            String day = str(first(row, "expire_at", "expireAt"));
            m.put("expireAt", day.length() >= 10 ? day.substring(0, 10) : day);
            return m;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置课时", e);
        }
    }

    private static boolean expired(Map<String, Object> acc) {
        String day = str(acc.get("expireAt"));
        if (day.isBlank()) return false;
        return LocalDate.parse(day).isBefore(LocalDate.now());
    }

    private static Map<String, Object> packRow(Map<String, Object> row, boolean withEnabled) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", lng(first(row, "id")));
        m.put("name", str(first(row, "name")));
        m.put("sessions", num(first(row, "sessions")));
        m.put("priceYuan", money(first(row, "price_yuan", "priceYuan")));
        m.put("validDays", num(first(row, "valid_days", "validDays")));
        if (withEnabled) m.put("enabled", num(first(row, "enabled")) == 1);
        return m;
    }

    private static Object first(Map<String, Object> row, String... keys) {
        if (row == null) return null;
        for (String key : keys) {
            if (row.containsKey(key)) return row.get(key);
        }
        return null;
    }

    private static void requireOn() {
        if (!enabled) throw new IllegalStateException("课时未开启");
    }

    private static LessonMapper mapper() {
        return MybatisSupport.mapper(LessonMapper.class);
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

    private static int num(Object o) {
        if (o instanceof Number n) return n.intValue();
        try {
            return Integer.parseInt(str(o));
        } catch (Exception e) {
            return 0;
        }
    }

    private static int toInt(Object o) {
        return num(o);
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
