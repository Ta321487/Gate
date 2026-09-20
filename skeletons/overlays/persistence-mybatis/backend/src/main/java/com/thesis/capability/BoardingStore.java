package com.thesis.capability;

import com.thesis.config.MybatisSupport;
import com.thesis.mapper.BoardingMapper;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.Timestamp;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 寄养。规则与 jdbc 相同，只换数据访问。 */
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
        dayCount(
                str(extras == null ? null : extras.get("stayFrom")),
                str(extras == null ? null : extras.get("stayTo")));
        String ids = careIds(extras);
        if (ids.isBlank()) return;
        requireTable();
        for (String part : ids.split(",")) {
            long id = lng(part.trim());
            Integer n = db().careOn(id);
            if (id <= 0 || n == null || n == 0) throw new IllegalArgumentException("请选择有效的特殊要求");
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
        List<Map<String, Object>> rows = db().span(
                itemId, Timestamp.valueOf(a.atStartOfDay()), Timestamp.valueOf(b.atStartOfDay()));
        if (rows == null || rows.isEmpty()) throw new IllegalStateException("这些日期没有可约位置");
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
                if (db().bump(id) == 0) throw new IllegalStateException("这些日期已满");
                bumped.add(id);
                if (first == 0) first = id;
            }
        } catch (RuntimeException e) {
            for (Long id : bumped) db().unbump(id);
            throw e;
        }
        return first;
    }

    public static void releaseRange(long itemId, String from, String to) {
        if (itemId <= 0 || str(from).isBlank() || str(to).isBlank()) return;
        LocalDate a = parseDay(from);
        LocalDate b = parseDay(to);
        db().releaseRange(itemId, Timestamp.valueOf(a.atStartOfDay()), Timestamp.valueOf(b.atStartOfDay()));
    }

    public static boolean releaseStay(String resvTable, String slotTable, long resvId) {
        if (!enabled || resvId <= 0) return false;
        try {
            List<Map<String, Object>> rows = db().stayRow(resvTable, slotTable, resvId);
            if (rows == null || rows.isEmpty()) return false;
            String from = str(rows.get(0).get("stayFrom"));
            String to = str(rows.get(0).get("stayTo"));
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
        List<Map<String, Object>> rows = onlyEnabled ? db().enabledCares() : db().allCares();
        List<Map<String, Object>> out = new ArrayList<>();
        if (rows == null) return out;
        for (Map<String, Object> row : rows) {
            Map<String, Object> m = new LinkedHashMap<>(row);
            m.put("enabled", num(row.get("enabled")) == 1 || Boolean.TRUE.equals(row.get("enabled")));
            out.add(m);
        }
        return out;
    }

    public static Map<String, Object> saveCare(Map<String, Object> body) {
        requireOn();
        requireTable();
        String name = str(body == null ? null : body.get("name"));
        if (name.isBlank()) throw new IllegalArgumentException("请填写名称");
        int on = flag(body == null ? null : body.get("enabled")) ? 1 : 0;
        long id = lng(body == null ? null : body.get("id"));
        if (id > 0) db().updateCare(id, name, on);
        else db().insertCare(name, on);
        return Map.of("ok", true);
    }

    public static List<Map<String, Object>> logs(String username) {
        requireOn();
        requireTable();
        List<Map<String, Object>> rows = username == null || username.isBlank()
                ? db().logs()
                : db().mine(username);
        List<Map<String, Object>> out = new ArrayList<>();
        if (rows == null) return out;
        for (Map<String, Object> row : rows) {
            Map<String, Object> m = new LinkedHashMap<>(row);
            Object photo = row.get("photoUrl");
            m.put("photoUrl", photo == null ? "" : String.valueOf(photo));
            out.add(m);
        }
        return out;
    }

    public static Map<String, Object> saveLog(Map<String, Object> body) {
        requireOn();
        requireTable();
        long resvId = lng(body == null ? null : body.get("reservationId"));
        if (resvId <= 0) throw new IllegalArgumentException("请选择寄养");
        LocalDate day = parseDay(str(body == null ? null : body.get("dayKey")));
        db().insertLog(resvId, day.toString(), str(body == null ? null : body.get("note")), str(body.get("photoUrl")));
        return Map.of("ok", true);
    }

    private static void requireOn() {
        if (!enabled) throw new IllegalStateException("寄养未开启");
    }

    private static void requireTable() {
        Integer n = db().tableCount();
        if (n == null || n == 0) throw new IllegalStateException("系统未配置寄养");
    }

    private static BoardingMapper db() {
        return MybatisSupport.mapper(BoardingMapper.class);
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
