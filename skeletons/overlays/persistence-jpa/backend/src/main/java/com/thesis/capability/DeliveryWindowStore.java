package com.thesis.capability;

import com.thesis.config.GeneratedKeyHolder;
import com.thesis.config.JpaDb;
import com.thesis.config.JpaSupport;
import com.thesis.config.KeyHolder;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.time.LocalDate;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 配送时段与节日加价。规则只在这里；下单仍走 OrderStore.placeOrder。
 */
public final class DeliveryWindowStore {

    private static final DateTimeFormatter DAY = DateTimeFormatter.ISO_LOCAL_DATE;
    private static boolean enabled;

    private DeliveryWindowStore() {}

    public static void configure(boolean on) {
        enabled = on;
    }

    public static boolean enabled() {
        return enabled;
    }

    private static JpaDb db() {
        return JpaSupport.db();
    }

    public static List<Map<String, Object>> listSlots() {
        requireOn();
        return db().query(
                "SELECT id, label, start_hm, end_hm, capacity, fulfill_mode, cutoff_hm, enabled, sort_no "
                        + "FROM delivery_slot ORDER BY sort_no, id",
                (rs, i) -> mapSlot(rs.getLong("id"), rs.getString("label"), rs.getString("start_hm"),
                        rs.getString("end_hm"), rs.getInt("capacity"), rs.getString("fulfill_mode"),
                        rs.getString("cutoff_hm"), rs.getInt("enabled"), rs.getInt("sort_no")));
    }

    public static Map<String, Object> saveSlot(Map<String, Object> body) {
        requireOn();
        Map<String, Object> row = normalizeSlot(body == null ? Map.of() : body);
        long id = longVal(body == null ? null : body.get("id"));
        if (id > 0) {
            db().update(
                    "UPDATE delivery_slot SET label=?, start_hm=?, end_hm=?, capacity=?, fulfill_mode=?, "
                            + "cutoff_hm=?, enabled=?, sort_no=? WHERE id=?",
                    row.get("label"), row.get("startHm"), row.get("endHm"), row.get("capacity"),
                    row.get("fulfillMode"), row.get("cutoffHm"), row.get("enabled"), row.get("sortNo"), id);
            row.put("id", id);
            return row;
        }
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO delivery_slot (label, start_hm, end_hm, capacity, fulfill_mode, cutoff_hm, enabled, sort_no) "
                            + "VALUES (?,?,?,?,?,?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, String.valueOf(row.get("label")));
            ps.setString(2, String.valueOf(row.get("startHm")));
            ps.setString(3, String.valueOf(row.get("endHm")));
            ps.setInt(4, (Integer) row.get("capacity"));
            ps.setString(5, String.valueOf(row.get("fulfillMode")));
            ps.setString(6, String.valueOf(row.get("cutoffHm")));
            ps.setInt(7, (Integer) row.get("enabled"));
            ps.setInt(8, (Integer) row.get("sortNo"));
            return ps;
        }, kh);
        row.put("id", kh.getKey() == null ? 0L : kh.getKey().longValue());
        return row;
    }

    public static List<Map<String, Object>> listSpans() {
        requireOn();
        return db().query(
                "SELECT id, name, date_from, date_to, rate, enabled FROM price_span ORDER BY date_from, id",
                (rs, i) -> mapSpan(rs.getLong("id"), rs.getString("name"), rs.getString("date_from"),
                        rs.getString("date_to"), rs.getDouble("rate"), rs.getInt("enabled")));
    }

    public static Map<String, Object> saveSpan(Map<String, Object> body) {
        requireOn();
        Map<String, Object> row = normalizeSpan(body == null ? Map.of() : body);
        long id = longVal(body == null ? null : body.get("id"));
        if (id > 0) {
            db().update(
                    "UPDATE price_span SET name=?, date_from=?, date_to=?, rate=?, enabled=? WHERE id=?",
                    row.get("name"), row.get("dateFrom"), row.get("dateTo"), row.get("rate"), row.get("enabled"), id);
            row.put("id", id);
            return row;
        }
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO price_span (name, date_from, date_to, rate, enabled) VALUES (?,?,?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, String.valueOf(row.get("name")));
            ps.setString(2, String.valueOf(row.get("dateFrom")));
            ps.setString(3, String.valueOf(row.get("dateTo")));
            ps.setDouble(4, (Double) row.get("rate"));
            ps.setInt(5, (Integer) row.get("enabled"));
            return ps;
        }, kh);
        row.put("id", kh.getKey() == null ? 0L : kh.getKey().longValue());
        return row;
    }

    public static Map<String, Object> options(String day) {
        requireOn();
        LocalDate date = parseDay(day);
        Map<String, Object> price = priceOn(date);
        List<Map<String, Object>> slots = new ArrayList<>();
        if (date != null && !date.isBefore(LocalDate.now())) {
            for (Map<String, Object> slot : listSlots()) {
                if (!isOpen(slot, date)) continue;
                int cap = (Integer) slot.get("capacity");
                int booked = countBooked(((Number) slot.get("id")).longValue(), date);
                Map<String, Object> one = new LinkedHashMap<>(slot);
                one.put("booked", booked);
                one.put("remain", Math.max(0, cap - booked));
                one.put("full", booked >= cap);
                slots.add(one);
            }
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("day", date == null ? "" : date.toString());
        out.put("priceRate", price.get("rate"));
        out.put("priceName", price.get("name"));
        out.put("slots", slots);
        return out;
    }

    public static Map<String, Object> quote(long slotId, String day) {
        requireOn();
        if (slotId <= 0 || day == null || day.isBlank()) {
            throw new IllegalArgumentException("请选择配送日期和时段");
        }
        LocalDate date = parseDay(day);
        if (date == null) throw new IllegalArgumentException("配送日期不正确");
        Map<String, Object> slot = null;
        for (Map<String, Object> row : listSlots()) {
            if (((Number) row.get("id")).longValue() == slotId) {
                slot = row;
                break;
            }
        }
        if (slot == null || (Integer) slot.get("enabled") != 1) {
            throw new IllegalArgumentException("时段不存在或已停用");
        }
        String mode = String.valueOf(slot.get("fulfillMode"));
        LocalDate today = LocalDate.now();
        if ("same_day".equals(mode)) {
            if (!date.equals(today)) throw new IllegalArgumentException("当日达只能选今天");
            if (pastCutoff(String.valueOf(slot.get("cutoffHm")))) {
                throw new IllegalArgumentException("已过截单时间");
            }
        } else if ("next_day".equals(mode)) {
            if (!date.equals(today.plusDays(1))) throw new IllegalArgumentException("次日达只能选明天");
        } else if (!date.isAfter(today)) {
            throw new IllegalArgumentException("预订请选明天及以后");
        }
        int cap = (Integer) slot.get("capacity");
        int booked = countBooked(slotId, date);
        if (booked >= cap) throw new IllegalStateException("该时段已满");
        Map<String, Object> price = priceOn(date);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("slotId", slotId);
        out.put("slotLabel", slot.get("label"));
        out.put("fulfillMode", mode);
        out.put("deliveryOn", date.toString());
        out.put("priceRate", price.get("rate"));
        out.put("priceName", price.get("name"));
        return out;
    }

    private static boolean isOpen(Map<String, Object> slot, LocalDate date) {
        if ((Integer) slot.get("enabled") != 1) return false;
        String mode = String.valueOf(slot.get("fulfillMode"));
        LocalDate today = LocalDate.now();
        if ("same_day".equals(mode)) {
            return date.equals(today) && !pastCutoff(String.valueOf(slot.get("cutoffHm")));
        }
        if ("next_day".equals(mode)) {
            return date.equals(today.plusDays(1));
        }
        return "preorder".equals(mode) && date.isAfter(today);
    }

    private static boolean pastCutoff(String hm) {
        String raw = hm == null ? "" : hm.trim();
        if (raw.isBlank()) return false;
        try {
            LocalTime cut = LocalTime.parse(raw.length() >= 5 ? raw.substring(0, 5) : raw);
            return !LocalTime.now().isBefore(cut);
        } catch (Exception e) {
            return false;
        }
    }

    private static int countBooked(long slotId, LocalDate date) {
        String table = OrderStore.orderTable();
        if (table == null || table.isBlank()) table = "biz_order";
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM " + table + " WHERE slot_id=? AND delivery_on=? AND status<>'cancelled'",
                Integer.class, slotId, date.toString());
        return n == null ? 0 : n;
    }

    private static Map<String, Object> priceOn(LocalDate date) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("rate", 1.0);
        out.put("name", "");
        if (date == null) return out;
        List<Map<String, Object>> rows = db().query(
                "SELECT name, rate FROM price_span WHERE enabled=1 AND date_from<=? AND date_to>=? ORDER BY rate DESC LIMIT 1",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("name", rs.getString("name"));
                    m.put("rate", rs.getDouble("rate"));
                    return m;
                },
                date.toString(), date.toString());
        if (rows != null && !rows.isEmpty()) {
            double rate = ((Number) rows.get(0).get("rate")).doubleValue();
            if (rate < 1) rate = 1;
            out.put("rate", rate);
            out.put("name", rows.get(0).get("name"));
        }
        return out;
    }

    private static Map<String, Object> normalizeSlot(Map<String, Object> body) {
        String label = str(body.get("label"));
        if (label.isBlank()) throw new IllegalArgumentException("请填写时段名称");
        String mode = str(body.get("fulfillMode"));
        if (!"same_day".equals(mode) && !"preorder".equals(mode) && !"next_day".equals(mode)) {
            throw new IllegalArgumentException("请选择当日达、预订或次日达");
        }
        int capacity = (int) longVal(body.get("capacity"));
        if (capacity < 1) throw new IllegalArgumentException("容量至少为 1");
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("label", label);
        row.put("startHm", str(body.get("startHm")));
        row.put("endHm", str(body.get("endHm")));
        row.put("capacity", capacity);
        row.put("fulfillMode", mode);
        row.put("cutoffHm", str(body.get("cutoffHm")));
        row.put("enabled", truth(body.get("enabled")) ? 1 : 0);
        row.put("sortNo", (int) longVal(body.get("sortNo")));
        return row;
    }

    private static Map<String, Object> normalizeSpan(Map<String, Object> body) {
        String name = str(body.get("name"));
        if (name.isBlank()) throw new IllegalArgumentException("请填写节日名称");
        LocalDate from = parseDay(str(body.get("dateFrom")));
        LocalDate to = parseDay(str(body.get("dateTo")));
        if (from == null || to == null) throw new IllegalArgumentException("请填写起止日期");
        if (to.isBefore(from)) throw new IllegalArgumentException("结束日期不能早于开始日期");
        double rate = doubleVal(body.get("rate"));
        if (rate < 1) throw new IllegalArgumentException("倍率不能小于 1");
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("name", name);
        row.put("dateFrom", from.toString());
        row.put("dateTo", to.toString());
        row.put("rate", rate);
        row.put("enabled", truth(body.get("enabled")) ? 1 : 0);
        return row;
    }

    private static Map<String, Object> mapSlot(
            long id, String label, String start, String end, int capacity, String mode,
            String cutoff, int enabledFlag, int sortNo) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", id);
        m.put("label", label == null ? "" : label);
        m.put("startHm", start == null ? "" : start);
        m.put("endHm", end == null ? "" : end);
        m.put("capacity", capacity);
        m.put("fulfillMode", mode == null ? "" : mode);
        m.put("cutoffHm", cutoff == null ? "" : cutoff);
        m.put("enabled", enabledFlag);
        m.put("sortNo", sortNo);
        return m;
    }

    private static Map<String, Object> mapSpan(
            long id, String name, String from, String to, double rate, int enabledFlag) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", id);
        m.put("name", name == null ? "" : name);
        m.put("dateFrom", dayText(from));
        m.put("dateTo", dayText(to));
        m.put("rate", rate);
        m.put("enabled", enabledFlag);
        return m;
    }

    private static String dayText(String raw) {
        if (raw == null) return "";
        return raw.length() >= 10 ? raw.substring(0, 10) : raw;
    }

    private static LocalDate parseDay(String raw) {
        String s = raw == null ? "" : raw.trim();
        if (s.length() >= 10) s = s.substring(0, 10);
        if (s.isBlank()) return null;
        try {
            return LocalDate.parse(s, DAY);
        } catch (Exception e) {
            return null;
        }
    }

    private static void requireOn() {
        if (!enabled) throw new IllegalStateException("配送时段未开启");
    }

    private static String str(Object v) {
        return v == null ? "" : String.valueOf(v).trim();
    }

    private static long longVal(Object v) {
        if (v instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(str(v));
        } catch (Exception e) {
            return 0;
        }
    }

    private static double doubleVal(Object v) {
        if (v instanceof Number n) return n.doubleValue();
        try {
            return Double.parseDouble(str(v));
        } catch (Exception e) {
            return 0;
        }
    }

    private static boolean truth(Object v) {
        if (v == null) return true;
        if (v instanceof Boolean b) return b;
        if (v instanceof Number n) return n.intValue() != 0;
        String s = str(v);
        return !s.equals("0") && !s.equalsIgnoreCase("false") && !s.equals("off");
    }
}
