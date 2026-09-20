package com.thesis.capability;

import com.thesis.config.JpaDb;
import com.thesis.config.JpaSupport;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.Date;
import java.sql.Timestamp;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 寄养：日价乘天数。重叠日期仍用时段占用，满了拒绝。 */
public final class BoardingStore {

    private static boolean enabled;

    private BoardingStore() {}

    public static void configure(boolean on) {
        enabled = on;
    }

    public static boolean enabled() {
        return enabled;
    }

    public static BigDecimal stayYuan(BigDecimal unit, int days) {
        if (unit == null) unit = BigDecimal.ZERO;
        if (days < 1) throw new IllegalArgumentException("离店须晚于入住");
        return unit.multiply(BigDecimal.valueOf(days)).setScale(2, RoundingMode.HALF_UP);
    }

    public static int dayCount(String from, String to) {
        LocalDate a = parseDay(from);
        LocalDate b = parseDay(to);
        long days = ChronoUnit.DAYS.between(a, b);
        if (days < 1 || days > 60) throw new IllegalArgumentException("离店须晚于入住");
        return (int) days;
    }

    public static void assertStay(Map<String, Object> extras) {
        if (!enabled) return;
        if (str(extras == null ? null : extras.get("guestName")).isBlank()) {
            throw new IllegalArgumentException("请填写宠物名");
        }
        String from = str(extras == null ? null : extras.get("stayFrom"));
        String to = str(extras == null ? null : extras.get("stayTo"));
        dayCount(from, to);
        String ids = careIds(extras);
        if (ids.isBlank()) return;
        requireTable();
        for (String part : ids.split(",")) {
            long id = lng(part.trim());
            if (id <= 0 || !careEnabled(id)) throw new IllegalArgumentException("请选择有效的特殊要求");
        }
    }

    public static long holdFrom(Map<String, Object> extras, long slotItemId) {
        long itemId = lng(extras == null ? null : extras.get("itemId"));
        if (itemId <= 0) itemId = slotItemId;
        return hold(
                itemId,
                str(extras == null ? null : extras.get("stayFrom")),
                str(extras == null ? null : extras.get("stayTo")));
    }

    public static long hold(long itemId, String from, String to) {
        if (itemId <= 0) throw new IllegalArgumentException("请选择寄养位");
        LocalDate a = parseDay(from);
        LocalDate b = parseDay(to);
        dayCount(from, to);
        List<Map<String, Object>> rows = db().query(
                "SELECT id, booked, capacity FROM resource_slot WHERE item_id=? AND start_at>=? AND start_at<? ORDER BY start_at",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("booked", rs.getInt("booked"));
                    m.put("capacity", rs.getInt("capacity"));
                    return m;
                },
                itemId,
                Timestamp.valueOf(a.atStartOfDay()),
                Timestamp.valueOf(b.atStartOfDay()));
        if (rows.isEmpty()) throw new IllegalStateException("这些日期没有可约位置");
        for (Map<String, Object> row : rows) {
            if (num(row.get("booked")) >= num(row.get("capacity"))) {
                throw new IllegalStateException("这些日期已满");
            }
        }
        List<Long> bumped = new ArrayList<>();
        long first = 0;
        try {
            for (Map<String, Object> row : rows) {
                long id = lng(row.get("id"));
                int n = db().update(
                        "UPDATE resource_slot SET booked=booked+1 WHERE id=? AND booked<capacity", id);
                if (n == 0) throw new IllegalStateException("这些日期已满");
                bumped.add(id);
                if (first == 0) first = id;
            }
        } catch (RuntimeException e) {
            for (Long id : bumped) {
                db().update("UPDATE resource_slot SET booked=GREATEST(booked-1,0) WHERE id=?", id);
            }
            throw e;
        }
        return first;
    }

    public static void releaseRange(long itemId, String from, String to) {
        if (itemId <= 0 || str(from).isBlank() || str(to).isBlank()) return;
        LocalDate a = parseDay(from);
        LocalDate b = parseDay(to);
        db().update(
                "UPDATE resource_slot SET booked=GREATEST(booked-1,0) WHERE item_id=? AND start_at>=? AND start_at<?",
                itemId,
                Timestamp.valueOf(a.atStartOfDay()),
                Timestamp.valueOf(b.atStartOfDay()));
    }

    public static boolean releaseStay(String resvTable, String slotTable, long resvId) {
        if (!enabled || resvId <= 0) return false;
        try {
            List<Map<String, Object>> rows = db().query(
                    "SELECT r.stay_from, r.stay_to, s.item_id FROM " + table(resvTable)
                            + " r JOIN " + table(slotTable) + " s ON s.id=r.slot_id WHERE r.id=?",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        Date from = rs.getDate("stay_from");
                        Date to = rs.getDate("stay_to");
                        m.put("from", from == null ? "" : from.toLocalDate().toString());
                        m.put("to", to == null ? "" : to.toLocalDate().toString());
                        m.put("itemId", rs.getLong("item_id"));
                        return m;
                    },
                    resvId);
            if (rows.isEmpty()) return false;
            String from = str(rows.get(0).get("from"));
            String to = str(rows.get(0).get("to"));
            if (from.isBlank() || to.isBlank()) return false;
            releaseRange(lng(rows.get(0).get("itemId")), from, to);
            return true;
        } catch (RuntimeException e) {
            return false;
        }
    }

    public static String careIds(Map<String, Object> extras) {
        if (extras == null) return "";
        Object raw = extras.get("careIds");
        if (raw instanceof List<?> list) {
            StringBuilder sb = new StringBuilder();
            for (Object one : list) {
                String part = str(one);
                if (part.isBlank()) continue;
                if (sb.length() > 0) sb.append(',');
                sb.append(part);
            }
            return sb.toString();
        }
        return str(raw);
    }

    public static List<Map<String, Object>> cares(boolean onlyEnabled) {
        requireOn();
        requireTable();
        String sql = onlyEnabled
                ? "SELECT id, option_name, enabled FROM stay_log WHERE reservation_id IS NULL AND enabled=1 ORDER BY id"
                : "SELECT id, option_name, enabled FROM stay_log WHERE reservation_id IS NULL ORDER BY id";
        return db().query(sql, (rs, i) -> careRow(rs));
    }

    public static Map<String, Object> saveCare(Map<String, Object> body) {
        requireOn();
        requireTable();
        String name = str(body == null ? null : body.get("name"));
        if (name.isBlank()) throw new IllegalArgumentException("请填写名称");
        int on = flag(body == null ? null : body.get("enabled")) ? 1 : 0;
        long id = lng(body == null ? null : body.get("id"));
        if (id > 0) {
            db().update(
                    "UPDATE stay_log SET option_name=?, enabled=? WHERE id=? AND reservation_id IS NULL",
                    name, on, id);
        } else {
            db().update("INSERT INTO stay_log (option_name, enabled) VALUES (?,?)", name, on);
        }
        return Map.of("ok", true);
    }

    public static List<Map<String, Object>> logs(String username) {
        requireOn();
        requireTable();
        if (username == null || username.isBlank()) {
            return db().query(
                    "SELECT id, reservation_id, day_key, note, photo_url FROM stay_log "
                            + "WHERE reservation_id IS NOT NULL ORDER BY day_key DESC, id DESC",
                    (rs, i) -> logRow(rs));
        }
        return db().query(
                "SELECT l.id, l.reservation_id, l.day_key, l.note, l.photo_url FROM stay_log l "
                        + "JOIN reservation r ON r.id=l.reservation_id WHERE r.username=? "
                        + "ORDER BY l.day_key DESC, l.id DESC",
                (rs, i) -> logRow(rs),
                username);
    }

    public static Map<String, Object> saveLog(Map<String, Object> body) {
        requireOn();
        requireTable();
        long resvId = lng(body == null ? null : body.get("reservationId"));
        if (resvId <= 0) throw new IllegalArgumentException("请选择寄养");
        LocalDate day = parseDay(str(body == null ? null : body.get("dayKey")));
        String note = str(body == null ? null : body.get("note"));
        String photo = str(body == null ? null : body.get("photoUrl"));
        db().update(
                "INSERT INTO stay_log (reservation_id, day_key, note, photo_url, enabled) VALUES (?,?,?,?,1)",
                resvId, Date.valueOf(day), note, photo);
        return Map.of("ok", true);
    }

    private static boolean careEnabled(long id) {
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM stay_log WHERE id=? AND reservation_id IS NULL AND enabled=1",
                Integer.class, id);
        return n != null && n > 0;
    }

    private static Map<String, Object> careRow(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("name", rs.getString("option_name"));
        m.put("enabled", rs.getInt("enabled") == 1);
        return m;
    }

    private static Map<String, Object> logRow(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("reservationId", rs.getLong("reservation_id"));
        Date day = rs.getDate("day_key");
        m.put("dayKey", day == null ? "" : day.toLocalDate().toString());
        m.put("note", rs.getString("note"));
        m.put("photoUrl", rs.getString("photo_url") == null ? "" : rs.getString("photo_url"));
        return m;
    }

    private static void requireOn() {
        if (!enabled) throw new IllegalStateException("寄养未开启");
    }

    private static void requireTable() {
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='stay_log'",
                Integer.class);
        if (n == null || n == 0) throw new IllegalStateException("系统未配置寄养");
    }

    private static JpaDb db() {
        return JpaSupport.db();
    }

    private static String table(String name) {
        if (name == null || !name.matches("[A-Za-z_][A-Za-z0-9_]*")) {
            throw new IllegalStateException("系统未配置寄养");
        }
        return name;
    }

    private static LocalDate parseDay(String raw) {
        String text = str(raw);
        if (text.length() >= 10) text = text.substring(0, 10);
        try {
            return LocalDate.parse(text);
        } catch (Exception e) {
            throw new IllegalArgumentException("请选择日期");
        }
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static int num(Object o) {
        if (o instanceof Number n) return n.intValue();
        try {
            return Integer.parseInt(str(o));
        } catch (Exception e) {
            return 0;
        }
    }

    private static long lng(Object o) {
        if (o instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(str(o));
        } catch (Exception e) {
            return 0L;
        }
    }

    private static boolean flag(Object o) {
        if (o instanceof Boolean b) return b;
        String text = str(o);
        return "1".equals(text) || "true".equalsIgnoreCase(text);
    }
}
