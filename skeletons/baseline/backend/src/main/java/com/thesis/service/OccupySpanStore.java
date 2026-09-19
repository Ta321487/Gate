package com.thesis.service;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 占用明细：复用单据起止时段做相交拒绝，并写入 resource_occupy。
 */
public class OccupySpanStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static boolean enabled;
    private static Boolean tableReady;

    private OccupySpanStore() {}

    public static void configure(boolean on) {
        enabled = on;
        tableReady = null;
    }

    public static boolean enabled() {
        return enabled;
    }

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    public static boolean ready() {
        if (!enabled) return false;
        if (tableReady != null) return tableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='resource_occupy'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static void require() {
        if (!ready()) throw new IllegalStateException("占用明细功能暂不可用");
    }

    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        String s = String.valueOf(o);
        return s.isBlank() ? null : s;
    }

    private static Map<String, Object> mapRow(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("itemId", rs.getObject("item_id"));
        m.put("ticketId", rs.getObject("ticket_id"));
        m.put("title", rs.getString("title"));
        m.put("periodStart", fmt(rs.getTimestamp("period_start")));
        m.put("periodEnd", fmt(rs.getTimestamp("period_end")));
        m.put("status", rs.getString("status"));
        return m;
    }

    /** 同一申请人或同一对象，起止相交则拒绝。 */
    public static void assertNoOverlap(String username, long itemId, LocalDateTime start, LocalDateTime end) {
        if (!enabled || !ready() || start == null || end == null) return;
        if (!end.isAfter(start)) {
            throw new IllegalStateException("结束时间须晚于开始时间");
        }
        List<Map<String, Object>> hits = db().query(
                "SELECT title, period_start, period_end FROM resource_occupy "
                        + "WHERE status='active' AND period_start < ? AND period_end > ? "
                        + "AND (username=? OR item_id=?) LIMIT 1",
                (rs, i) -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("title", rs.getString("title"));
                    row.put("start", rs.getTimestamp("period_start"));
                    row.put("end", rs.getTimestamp("period_end"));
                    return row;
                },
                Timestamp.valueOf(end),
                Timestamp.valueOf(start),
                username,
                itemId);
        if (!hits.isEmpty()) {
            Map<String, Object> row = hits.get(0);
            String title = row.get("title") == null ? "已有占用" : String.valueOf(row.get("title"));
            throw new IllegalStateException(
                    "时间冲突：与「" + title + "」（"
                            + fmt(row.get("start")) + " ~ " + fmt(row.get("end")) + "）重叠");
        }
    }

    public static void record(
            String username,
            long itemId,
            long ticketId,
            String title,
            LocalDateTime start,
            LocalDateTime end) {
        if (!enabled || !ready() || start == null || end == null) return;
        String t = title == null ? "" : title.trim();
        if (t.length() > 200) t = t.substring(0, 200);
        db().update(
                "INSERT INTO resource_occupy (username, item_id, ticket_id, title, period_start, period_end, status) "
                        + "VALUES (?,?,?,?,?,?,'active')",
                username,
                itemId > 0 ? itemId : null,
                ticketId > 0 ? ticketId : null,
                t,
                Timestamp.valueOf(start),
                Timestamp.valueOf(end));
    }

    public static Map<String, Object> pageMine(String username, int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 20;
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM resource_occupy WHERE username=?", Integer.class, username);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM resource_occupy WHERE username=? ORDER BY period_start DESC, id DESC LIMIT ? OFFSET ?",
                (rs, i) -> mapRow(rs),
                username, size, (page - 1) * size);
        return pageOut(list, total, page, size);
    }

    public static Map<String, Object> pageAdmin(int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 20;
        Integer total = db().queryForObject("SELECT COUNT(*) FROM resource_occupy", Integer.class);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM resource_occupy ORDER BY period_start DESC, id DESC LIMIT ? OFFSET ?",
                (rs, i) -> mapRow(rs),
                size, (page - 1) * size);
        return pageOut(list, total, page, size);
    }

    private static Map<String, Object> pageOut(List<?> list, Integer total, int page, int size) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }
}
