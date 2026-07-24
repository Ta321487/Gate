package com.thesis.capability;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 能力 archive_log：挂档案的打卡/随访/评估记录。 */
public final class ArchiveLogStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final DateTimeFormatter DAY = DateTimeFormatter.ofPattern("yyyy-MM-dd");
    private static final String TABLE = "archive_log";
    private static final ObjectMapper JSON = new ObjectMapper();
    private static boolean enabled = false;

    private ArchiveLogStore() {}

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
                            + "item_id BIGINT NOT NULL,"
                            + "username VARCHAR(64) NOT NULL,"
                            + "log_date DATE NOT NULL,"
                            + "log_type VARCHAR(32) NOT NULL DEFAULT 'checkin',"
                            + "payload_json TEXT,"
                            + "abnormal TINYINT DEFAULT 0,"
                            + "remark VARCHAR(512) DEFAULT '',"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "KEY idx_alog_item_date (item_id, log_date),"
                            + "KEY idx_alog_date_type (log_date, log_type),"
                            + "KEY idx_alog_user (username, id)"
                            + ")");
        } catch (Exception ignored) {
        }
    }

    public static Map<String, Object> submit(
            String username,
            long itemId,
            String logType,
            LocalDate logDate,
            Map<String, Object> payload,
            boolean abnormal,
            String remark) {
        require();
        if (username == null || username.isBlank()) {
            throw new IllegalArgumentException("未登录");
        }
        if (itemId <= 0 || ArchiveStore.getItemRaw(itemId) == null) {
            throw new IllegalArgumentException("档案不存在");
        }
        String type = (logType == null || logType.isBlank()) ? "checkin" : logType.trim();
        LocalDate day = logDate == null ? LocalDate.now() : logDate;
        String payloadJson = "{}";
        try {
            payloadJson = JSON.writeValueAsString(payload == null ? Map.of() : payload);
        } catch (Exception ignored) {
        }
        String rem = remark == null ? "" : remark.trim();
        if (rem.length() > 500) rem = rem.substring(0, 500);
        KeyHolder kh = new GeneratedKeyHolder();
        String sql =
                "INSERT INTO " + TABLE
                        + " (item_id,username,log_date,log_type,payload_json,abnormal,remark) VALUES (?,?,?,?,?,?,?)";
        String finalPayload = payloadJson;
        String finalRem = rem;
        db().update(
                con -> {
                    PreparedStatement ps = con.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS);
                    ps.setLong(1, itemId);
                    ps.setString(2, username);
                    ps.setDate(3, java.sql.Date.valueOf(day));
                    ps.setString(4, type);
                    ps.setString(5, finalPayload);
                    ps.setInt(6, abnormal ? 1 : 0);
                    ps.setString(7, finalRem);
                    return ps;
                },
                kh);
        Number key = kh.getKey();
        long id = key == null ? 0L : key.longValue();
        return get(id);
    }

    public static Map<String, Object> get(long id) {
        require();
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM " + TABLE + " WHERE id=?", (rs, i) -> row(rs), id);
        return rows == null || rows.isEmpty() ? null : rows.get(0);
    }

    public static Map<String, Object> pageByItem(long itemId, int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM " + TABLE + " WHERE item_id=?", Integer.class, itemId);
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM " + TABLE + " WHERE item_id=? ORDER BY log_date DESC, id DESC LIMIT ? OFFSET ?",
                (rs, i) -> row(rs),
                itemId, size, (page - 1) * size);
        return pageOut(rows, total, page, size);
    }

    public static Map<String, Object> pageAdmin(
            Long itemId, String logType, LocalDate day, Boolean abnormalOnly, int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        StringBuilder where = new StringBuilder(" WHERE 1=1");
        List<Object> args = new ArrayList<>();
        if (itemId != null && itemId > 0) {
            where.append(" AND item_id=?");
            args.add(itemId);
        }
        if (logType != null && !logType.isBlank()) {
            where.append(" AND log_type=?");
            args.add(logType.trim());
        }
        if (day != null) {
            where.append(" AND log_date=?");
            args.add(java.sql.Date.valueOf(day));
        }
        if (Boolean.TRUE.equals(abnormalOnly)) {
            where.append(" AND abnormal=1");
        }
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM " + TABLE + where, Integer.class, args.toArray());
        List<Object> pageArgs = new ArrayList<>(args);
        pageArgs.add(size);
        pageArgs.add((page - 1) * size);
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM " + TABLE + where + " ORDER BY log_date DESC, id DESC LIMIT ? OFFSET ?",
                (rs, i) -> row(rs),
                pageArgs.toArray());
        if (rows != null) {
            for (Map<String, Object> m : rows) {
                attachItemTitle(m);
            }
        }
        return pageOut(rows, total, page, size);
    }

    /** 今日尚无指定类型记录的档案 id（仅未软删且可上报/在库对象）。 */
    public static List<Map<String, Object>> missingToday(String logType) {
        require();
        String type = (logType == null || logType.isBlank()) ? "checkin" : logType.trim();
        LocalDate today = LocalDate.now();
        String item = ArchiveStore.itemTable();
        String soft = ArchiveStore.softDeleteEnabled()
                ? " AND i.deleted_at IS NULL"
                : "";
        String sql =
                "SELECT i.id, i.title FROM `" + item + "` i"
                        + " WHERE 1=1" + soft
                        + " AND NOT EXISTS ("
                        + "   SELECT 1 FROM " + TABLE + " l"
                        + "   WHERE l.item_id=i.id AND l.log_date=? AND l.log_type=?"
                        + " )"
                        + " ORDER BY i.id DESC LIMIT 200";
        List<Map<String, Object>> rows = db().query(
                sql,
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("title", rs.getString("title"));
                    return m;
                },
                java.sql.Date.valueOf(today),
                type);
        return rows == null ? List.of() : rows;
    }

    public static int countMissingToday(String logType) {
        if (!enabled) return 0;
        try {
            return missingToday(logType).size();
        } catch (Exception e) {
            return 0;
        }
    }

    private static Map<String, Object> pageOut(
            List<Map<String, Object>> rows, Integer total, int page, int size) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", rows == null ? List.of() : rows);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    private static void attachItemTitle(Map<String, Object> m) {
        Object idObj = m.get("itemId");
        if (!(idObj instanceof Number n)) return;
        Map<String, Object> item = ArchiveStore.getItemRaw(n.longValue());
        if (item != null) {
            m.put("itemTitle", item.get("title"));
        }
    }

    private static Map<String, Object> row(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("itemId", rs.getLong("item_id"));
        m.put("username", rs.getString("username"));
        java.sql.Date d = rs.getDate("log_date");
        m.put("logDate", d == null ? null : d.toLocalDate().format(DAY));
        m.put("logType", rs.getString("log_type"));
        String payload = rs.getString("payload_json");
        m.put("payloadJson", payload == null ? "{}" : payload);
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> parsed =
                    payload == null || payload.isBlank()
                            ? Map.of()
                            : JSON.readValue(payload, Map.class);
            m.put("payload", parsed);
        } catch (Exception e) {
            m.put("payload", Map.of());
        }
        m.put("abnormal", rs.getInt("abnormal") == 1);
        m.put("remark", rs.getString("remark") == null ? "" : rs.getString("remark"));
        Timestamp ts = rs.getTimestamp("created_at");
        m.put("createdAt", ts == null ? null : ts.toLocalDateTime().format(FMT));
        return m;
    }

    private static void require() {
        if (!enabled) throw new IllegalStateException("监测记录暂不可用");
    }
}
