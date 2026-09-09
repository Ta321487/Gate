package com.thesis.capability;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.sql.Date;
import java.sql.Timestamp;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

/** 能力 staff_roster：按员工+日期维护班次；按课题需要启用。 */
public final class StaffRosterStore {

    private static final DateTimeFormatter DAY = DateTimeFormatter.ofPattern("yyyy-MM-dd");
    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final String TABLE = "staff_roster";
    private static boolean enabled = false;

    private StaffRosterStore() {}

    public static void configure(boolean on) {
        enabled = on;
        if (enabled) ensureTable();
    }

    public static boolean enabled() {
        return enabled;
    }

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    private static void ensureTable() {
        try {
            db().execute(
                    "CREATE TABLE IF NOT EXISTS " + TABLE + " ("
                            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
                            + "username VARCHAR(64) NOT NULL,"
                            + "work_date DATE NOT NULL,"
                            + "shift_label VARCHAR(64) NOT NULL DEFAULT '全天',"
                            + "note VARCHAR(256) DEFAULT '',"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "UNIQUE KEY uk_roster_user_day (username, work_date),"
                            + "KEY idx_roster_date (work_date)"
                            + ")");
        } catch (Exception ignored) {
        }
    }

    public static Map<String, Object> page(String username, String from, String to, int page, int size) {
        if (!enabled) throw new IllegalStateException("排班功能暂不可用");
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        StringBuilder where = new StringBuilder(" WHERE 1=1");
        List<Object> args = new ArrayList<>();
        String user = username == null ? "" : username.trim();
        if (!user.isBlank()) {
            where.append(" AND username=?");
            args.add(user);
        }
        LocalDate fromDay = parseDay(from);
        LocalDate toDay = parseDay(to);
        if (fromDay != null) {
            where.append(" AND work_date>=?");
            args.add(Date.valueOf(fromDay));
        }
        if (toDay != null) {
            where.append(" AND work_date<=?");
            args.add(Date.valueOf(toDay));
        }
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM " + TABLE + where, Integer.class, args.toArray());
        args.add(size);
        args.add((page - 1) * size);
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM " + TABLE + where + " ORDER BY work_date DESC, id DESC LIMIT ? OFFSET ?",
                (rs, i) -> mapRow(rs),
                args.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", rows == null ? List.of() : rows);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    public static Map<String, Object> create(String username, String workDate, String shiftLabel, String note) {
        if (!enabled) throw new IllegalStateException("排班功能暂不可用");
        String user = requireUser(username);
        LocalDate day = requireDay(workDate);
        String shift = blankTo(shiftLabel, "全天");
        if (shift.length() > 64) shift = shift.substring(0, 64);
        String tip = note == null ? "" : note.trim();
        if (tip.length() > 256) tip = tip.substring(0, 256);
        Integer exists = db().queryForObject(
                "SELECT COUNT(*) FROM " + TABLE + " WHERE username=? AND work_date=?",
                Integer.class, user, Date.valueOf(day));
        if (exists != null && exists > 0) {
            throw new IllegalArgumentException("该员工该日已有排班");
        }
        db().update(
                "INSERT INTO " + TABLE + " (username,work_date,shift_label,note,created_at) VALUES (?,?,?,?,?)",
                user, Date.valueOf(day), shift, tip, Timestamp.valueOf(LocalDateTime.now()));
        Long id = db().queryForObject(
                "SELECT id FROM " + TABLE + " WHERE username=? AND work_date=?",
                Long.class, user, Date.valueOf(day));
        return get(id == null ? 0L : id);
    }

    public static Map<String, Object> update(long id, String shiftLabel, String note) {
        if (!enabled) throw new IllegalStateException("排班功能暂不可用");
        Map<String, Object> cur = get(id);
        if (cur == null) throw new IllegalArgumentException("排班记录不存在");
        String shift = blankTo(shiftLabel, String.valueOf(cur.getOrDefault("shiftLabel", "全天")));
        if (shift.length() > 64) shift = shift.substring(0, 64);
        String tip = note == null ? String.valueOf(cur.getOrDefault("note", "")) : note.trim();
        if (tip.length() > 256) tip = tip.substring(0, 256);
        db().update("UPDATE " + TABLE + " SET shift_label=?, note=? WHERE id=?", shift, tip, id);
        return get(id);
    }

    public static void delete(long id) {
        if (!enabled) throw new IllegalStateException("排班功能暂不可用");
        int n = db().update("DELETE FROM " + TABLE + " WHERE id=?", id);
        if (n <= 0) throw new IllegalArgumentException("排班记录不存在");
    }

    public static Map<String, Object> get(long id) {
        if (!enabled || id <= 0) return null;
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM " + TABLE + " WHERE id=?",
                (rs, i) -> mapRow(rs),
                id);
        return rows == null || rows.isEmpty() ? null : rows.get(0);
    }

    /** 某日当班列表（预约页弱展示）。 */
    public static List<Map<String, Object>> onDuty(String workDate) {
        if (!enabled) return List.of();
        LocalDate day = parseDay(workDate);
        if (day == null) day = LocalDate.now();
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM " + TABLE + " WHERE work_date=? ORDER BY id ASC",
                (rs, i) -> mapRow(rs),
                Date.valueOf(day));
        return rows == null ? List.of() : rows;
    }

    public static Set<String> onDutyUsernames(String workDate) {
        return onDuty(workDate).stream()
                .map(m -> String.valueOf(m.getOrDefault("username", "")))
                .filter(s -> !s.isBlank())
                .collect(Collectors.toCollection(java.util.LinkedHashSet::new));
    }

    public static boolean isOnDuty(String username, String workDate) {
        if (!enabled) return false;
        String user = username == null ? "" : username.trim();
        if (user.isBlank()) return false;
        LocalDate day = parseDay(workDate);
        if (day == null) day = LocalDate.now();
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM " + TABLE + " WHERE username=? AND work_date=?",
                Integer.class, user, Date.valueOf(day));
        return n != null && n > 0;
    }

    private static Map<String, Object> mapRow(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        Date d = rs.getDate("work_date");
        m.put("workDate", d == null ? null : d.toLocalDate().format(DAY));
        m.put("shiftLabel", rs.getString("shift_label"));
        m.put("note", rs.getString("note"));
        Timestamp c = rs.getTimestamp("created_at");
        m.put("createdAt", c == null ? null : c.toLocalDateTime().format(FMT));
        return m;
    }

    private static String requireUser(String username) {
        String user = username == null ? "" : username.trim();
        if (user.isBlank()) throw new IllegalArgumentException("请选择员工");
        if (user.length() > 64) throw new IllegalArgumentException("用户名过长");
        return user;
    }

    private static LocalDate requireDay(String workDate) {
        LocalDate day = parseDay(workDate);
        if (day == null) throw new IllegalArgumentException("请选择日期");
        return day;
    }

    private static LocalDate parseDay(String raw) {
        if (raw == null || raw.isBlank()) return null;
        String s = raw.trim();
        if (s.length() >= 10) s = s.substring(0, 10);
        try {
            return LocalDate.parse(s, DAY);
        } catch (Exception e) {
            return null;
        }
    }

    private static String blankTo(String raw, String fallback) {
        if (raw == null || raw.isBlank()) return fallback == null ? "" : fallback;
        return raw.trim();
    }
}
