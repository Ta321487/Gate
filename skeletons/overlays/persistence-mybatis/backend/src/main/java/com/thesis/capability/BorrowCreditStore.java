package com.thesis.capability;

import com.thesis.config.MbSql;
import com.thesis.config.MybatisSupport;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 借用信誉分（分值列）：开题写「信誉分/逾期扣分/低于 N 停借」时挂。
 * 与 maxOverdueTimes 次数冻结可并存；本类只在 creditOnOverdue=true 时生效。
 * persistence=mybatis：尚未 Mapper 化的原生 SQL 走 MybatisSupport.db()（与 MyBatis 共用库）。
 */
public final class BorrowCreditStore {
    private BorrowCreditStore() {}

    static boolean enabled = false;
    static int initialScore = 100;
    static int overdueDelta = 5;
    static int blockBelow = 60;
    private static boolean schemaReady = false;

    public static void configure(boolean on, int initial, int delta, int block) {
        enabled = on;
        initialScore = Math.max(1, Math.min(999, initial <= 0 ? 100 : initial));
        overdueDelta = Math.max(1, Math.min(100, delta <= 0 ? 5 : delta));
        blockBelow = Math.max(0, Math.min(999, block));
        if (enabled) {
            ensureSchema();
        }
    }

    public static boolean enabled() {
        return enabled;
    }

    private static MbSql db() {
        return MybatisSupport.db();
    }

    static void ensureSchema() {
        if (schemaReady) return;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS "
                            + "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='sys_user' AND COLUMN_NAME='credit_score'",
                    Integer.class);
            if (n == null || n == 0) {
                db().execute(
                        "ALTER TABLE sys_user ADD COLUMN credit_score INT NOT NULL DEFAULT "
                                + initialScore);
            }
        } catch (Exception ignored) {
        }
        try {
            db().execute(
                    "CREATE TABLE IF NOT EXISTS credit_ledger ("
                            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
                            + "username VARCHAR(64) NOT NULL,"
                            + "delta INT NOT NULL,"
                            + "score_after INT NOT NULL DEFAULT 0,"
                            + "reason VARCHAR(128) DEFAULT '',"
                            + "ref_type VARCHAR(32) DEFAULT '',"
                            + "ref_id BIGINT NULL,"
                            + "operator VARCHAR(64) DEFAULT '',"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "KEY idx_credit_user (username, id))");
        } catch (Exception ignored) {
        }
        schemaReady = true;
    }

    public static int getScore(String username) {
        if (!enabled || username == null || username.isBlank()) return initialScore;
        ensureSchema();
        try {
            Integer s = db().queryForObject(
                    "SELECT credit_score FROM sys_user WHERE username=?",
                    Integer.class,
                    username.trim());
            if (s == null) return initialScore;
            return s;
        } catch (Exception e) {
            return initialScore;
        }
    }

    /** 首次逾期标记时扣分（同一 ticket 不重复扣）。 */
    public static void penalizeOverdue(String username, long ticketId) {
        if (!enabled || username == null || username.isBlank() || ticketId <= 0) return;
        ensureSchema();
        String u = username.trim();
        try {
            Integer exists = db().queryForObject(
                    "SELECT COUNT(*) FROM credit_ledger WHERE username=? AND ref_type='ticket_overdue' AND ref_id=?",
                    Integer.class,
                    u,
                    ticketId);
            if (exists != null && exists > 0) return;
        } catch (Exception ignored) {
        }
        applyDelta(u, -overdueDelta, "逾期扣分 -" + overdueDelta, "ticket_overdue", ticketId, "system");
    }


    public static void assertCanBorrow(String username) {
        if (!enabled || username == null || username.isBlank()) return;
        int score = getScore(username);
        if (score < blockBelow) {
            throw new IllegalStateException(
                    "信誉分 " + score + " 低于 " + blockBelow + "，暂不可再借");
        }
    }

    public static Map<String, Object> snapshot(String username) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("enabled", enabled);
        m.put("score", getScore(username));
        m.put("initial", initialScore);
        m.put("overdueDelta", overdueDelta);
        m.put("blockBelow", blockBelow);
        return m;
    }

    public static List<Map<String, Object>> listLedger(String username, int limit) {
        if (!enabled || username == null || username.isBlank()) return List.of();
        ensureSchema();
        int lim = Math.min(100, Math.max(1, limit));
        try {
            return db().query(
                    "SELECT id, username, delta, score_after, reason, ref_type, ref_id, operator, created_at "
                            + "FROM credit_ledger WHERE username=? ORDER BY id DESC LIMIT ?",
                    (rs, i) -> row(rs),
                    username.trim(),
                    lim);
        } catch (Exception e) {
            return List.of();
        }
    }

    public static List<Map<String, Object>> listAllRecent(int limit) {
        if (!enabled) return List.of();
        ensureSchema();
        int lim = Math.min(200, Math.max(1, limit));
        try {
            return db().query(
                    "SELECT id, username, delta, score_after, reason, ref_type, ref_id, operator, created_at "
                            + "FROM credit_ledger ORDER BY id DESC LIMIT ?",
                    (rs, i) -> row(rs),
                    lim);
        } catch (Exception e) {
            return new ArrayList<>();
        }
    }

    private static Map<String, Object> row(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", rs.getLong("id"));
        row.put("username", rs.getString("username"));
        row.put("delta", rs.getInt("delta"));
        row.put("scoreAfter", rs.getInt("score_after"));
        row.put("reason", rs.getString("reason"));
        row.put("refType", rs.getString("ref_type"));
        row.put("refId", rs.getObject("ref_id"));
        row.put("operator", rs.getString("operator"));
        java.sql.Timestamp ts = rs.getTimestamp("created_at");
        row.put("createdAt", ts == null ? null : ts.toLocalDateTime().toString().replace('T', ' '));
        return row;
    }

    public static Map<String, Object> adjust(
            String username, int delta, String reason, String operator) {
        if (!enabled) throw new IllegalStateException("未开启信誉分");
        if (username == null || username.isBlank()) throw new IllegalStateException("缺少用户名");
        if (delta == 0) throw new IllegalStateException("调整分值不能为 0");
        String r = reason == null || reason.isBlank() ? "管理员调整" : reason.trim();
        if (r.length() > 128) r = r.substring(0, 128);
        int after = applyDelta(
                username.trim(),
                delta,
                r,
                "admin",
                null,
                operator == null ? "" : operator.trim());
        Map<String, Object> out = snapshot(username.trim());
        out.put("score", after);
        return out;
    }

    private static int applyDelta(
            String username, int delta, String reason, String refType, Long refId, String operator) {
        ensureSchema();
        int before = getScore(username);
        int after = Math.max(0, Math.min(999, before + delta));
        try {
            db().update("UPDATE sys_user SET credit_score=? WHERE username=?", after, username);
        } catch (Exception e) {
            throw new IllegalStateException("信誉分写库失败");
        }
        try {
            db().update(
                    "INSERT INTO credit_ledger(username, delta, score_after, reason, ref_type, ref_id, operator) "
                            + "VALUES(?,?,?,?,?,?,?)",
                    username,
                    delta,
                    after,
                    reason,
                    refType == null ? "" : refType,
                    refId,
                    operator == null ? "" : operator);
        } catch (Exception ignored) {
        }
        return after;
    }
}
