package com.thesis.capability;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 能力 audit_log：sys_audit_log；开题扫词才启用（E-04）。 */
public final class AuditLogStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final String TABLE = "sys_audit_log";
    private static boolean enabled = false;
    private static boolean loginOnly = false;

    private AuditLogStore() {}

    public static void configure(boolean on, boolean loginOnlyMode) {
        enabled = on;
        loginOnly = loginOnlyMode;
        if (enabled) ensureTable();
    }

    public static boolean enabled() {
        return enabled;
    }

    public static boolean loginOnly() {
        return loginOnly;
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
                            + "action VARCHAR(64) NOT NULL,"
                            + "target_type VARCHAR(32) DEFAULT '',"
                            + "target_id VARCHAR(64) DEFAULT '',"
                            + "detail VARCHAR(512) DEFAULT '',"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "KEY idx_audit_created (created_at, id),"
                            + "KEY idx_audit_user (username)"
                            + ")");
        } catch (Exception ignored) {
        }
    }

    /** 静默记账：未启用或 loginOnly 过滤时直接返回。 */
    public static void record(
            String username, String action, String targetType, String targetId, String detail) {
        if (!enabled) return;
        String act = action == null ? "" : action.trim();
        if (act.isBlank()) return;
        if (loginOnly && !"login".equals(act)) return;
        String user = username == null || username.isBlank() ? "-" : username.trim();
        String type = targetType == null ? "" : targetType.trim();
        String tid = targetId == null ? "" : targetId.trim();
        String note = detail == null ? "" : detail.trim();
        if (note.length() > 512) note = note.substring(0, 512);
        try {
            db().update(
                    "INSERT INTO " + TABLE
                            + " (username,action,target_type,target_id,detail,created_at) VALUES (?,?,?,?,?,?)",
                    user, act, type, tid, note, Timestamp.valueOf(LocalDateTime.now()));
        } catch (Exception ignored) {
            // 审计失败不影响主业务
        }
    }

    public static Map<String, Object> page(String keyword, String action, int page, int size) {
        if (!enabled) throw new IllegalStateException("操作日志功能暂不可用");
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        String kw = keyword == null ? "" : keyword.trim();
        String act = action == null ? "" : action.trim();
        StringBuilder where = new StringBuilder(" WHERE 1=1");
        java.util.List<Object> args = new java.util.ArrayList<>();
        if (!kw.isBlank()) {
            where.append(" AND (username LIKE ? OR detail LIKE ? OR target_id LIKE ?)");
            String like = "%" + kw + "%";
            args.add(like);
            args.add(like);
            args.add(like);
        }
        if (!act.isBlank()) {
            where.append(" AND action=?");
            args.add(act);
        }
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM " + TABLE + where, Integer.class, args.toArray());
        args.add(size);
        args.add((page - 1) * size);
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM " + TABLE + where + " ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("username", rs.getString("username"));
                    m.put("action", rs.getString("action"));
                    m.put("targetType", rs.getString("target_type"));
                    m.put("targetId", rs.getString("target_id"));
                    m.put("detail", rs.getString("detail"));
                    Timestamp c = rs.getTimestamp("created_at");
                    m.put("createdAt", c == null ? null : c.toLocalDateTime().format(FMT));
                    return m;
                },
                args.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", rows == null ? List.of() : rows);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }
}
