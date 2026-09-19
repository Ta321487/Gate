package com.thesis.service;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 额度台账：整数余额账户 + 流水；审批通过时扣减。
 */
public class BalanceLedgerStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static boolean enabled;
    private static boolean debitOnApprove;
    private static Boolean tableReady;
    private static String cachedUnit;

    private BalanceLedgerStore() {}

    public static void configure(boolean on, boolean debitApprove) {
        enabled = on;
        debitOnApprove = debitApprove;
        tableReady = null;
        cachedUnit = null;
    }

    public static boolean enabled() {
        return enabled;
    }

    public static boolean debitOnApprove() {
        return debitOnApprove;
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
                            + "WHERE table_schema=DATABASE() AND table_name='balance_account'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static void require() {
        if (!ready()) throw new IllegalStateException("额度台账功能暂不可用");
    }

    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        String s = String.valueOf(o);
        return s.isBlank() ? null : s;
    }

    private static String clip(String s, int max) {
        if (s == null) return "";
        String t = s.trim();
        return t.length() <= max ? t : t.substring(0, max);
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static int qty(Object o) {
        if (o == null || String.valueOf(o).isBlank()) {
            throw new IllegalArgumentException("额度无效");
        }
        int n;
        if (o instanceof Number num) n = num.intValue();
        else n = Integer.parseInt(String.valueOf(o).trim());
        if (n <= 0) throw new IllegalArgumentException("额度须为正整数");
        if (n > 999999) throw new IllegalArgumentException("单次额度过大");
        return n;
    }

    private static Map<String, Object> pageOut(List<?> list, Integer total, int page, int size) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    private static String unitLabel() {
        if (cachedUnit != null) return cachedUnit;
        String unit = "次";
        try {
            String u = db().queryForObject(
                    "SELECT unit_label FROM balance_subject WHERE id=1",
                    String.class);
            if (u != null && !u.isBlank()) unit = u.trim();
        } catch (Exception ignored) {
            unit = "次";
        }
        cachedUnit = unit;
        return unit;
    }

    private static Map<String, Object> mapAccount(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("subjectId", rs.getLong("subject_id"));
        m.put("balance", rs.getInt("balance"));
        m.put("unitLabel", unitLabel());
        m.put("updatedAt", fmt(rs.getTimestamp("updated_at")));
        return m;
    }

    private static Map<String, Object> mapLedger(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("subjectId", rs.getLong("subject_id"));
        m.put("deltaQty", rs.getInt("delta_qty"));
        m.put("unitLabel", unitLabel());
        m.put("reason", rs.getString("reason"));
        m.put("refType", rs.getString("ref_type"));
        m.put("refId", rs.getObject("ref_id"));
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        return m;
    }

    private static void ensureAccount(String username) {
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM balance_account WHERE username=? AND subject_id=1",
                Integer.class, username);
        if (n == null || n == 0) {
            db().update(
                    "INSERT INTO balance_account (username, subject_id, balance) VALUES (?, 1, 0)",
                    username);
        }
    }

    public static Map<String, Object> getAccount(String username) {
        require();
        String u = clip(username, 64);
        if (u.isBlank()) throw new IllegalArgumentException("用户名无效");
        ensureAccount(u);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM balance_account WHERE username=? AND subject_id=1",
                (rs, i) -> mapAccount(rs), u);
        return list.isEmpty() ? Map.of() : list.get(0);
    }

    public static Map<String, Object> pageAccounts(int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 20;
        Integer total = db().queryForObject("SELECT COUNT(*) FROM balance_account", Integer.class);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM balance_account ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?",
                (rs, i) -> mapAccount(rs),
                size, (page - 1) * size);
        return pageOut(list, total, page, size);
    }

    public static Map<String, Object> pageLedgerMine(String username, int page, int size) {
        require();
        String u = clip(username, 64);
        if (page < 1) page = 1;
        if (size < 1) size = 20;
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM balance_ledger WHERE username=?", Integer.class, u);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM balance_ledger WHERE username=? ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> mapLedger(rs),
                u, size, (page - 1) * size);
        return pageOut(list, total, page, size);
    }

    public static Map<String, Object> pageLedgerAdmin(int page, int size, String username) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 20;
        String u = clip(username, 64);
        Integer total;
        List<Map<String, Object>> list;
        if (u.isBlank()) {
            total = db().queryForObject("SELECT COUNT(*) FROM balance_ledger", Integer.class);
            list = db().query(
                    "SELECT * FROM balance_ledger ORDER BY id DESC LIMIT ? OFFSET ?",
                    (rs, i) -> mapLedger(rs),
                    size, (page - 1) * size);
        } else {
            total = db().queryForObject(
                    "SELECT COUNT(*) FROM balance_ledger WHERE username=?", Integer.class, u);
            list = db().query(
                    "SELECT * FROM balance_ledger WHERE username=? ORDER BY id DESC LIMIT ? OFFSET ?",
                    (rs, i) -> mapLedger(rs),
                    u, size, (page - 1) * size);
        }
        return pageOut(list, total, page, size);
    }

    /** 增加额度（正数）；管理端调整。 */
    public static Map<String, Object> credit(String username, int qty, String reason) {
        require();
        String u = clip(username, 64);
        if (u.isBlank()) throw new IllegalArgumentException("用户名无效");
        int n = qty;
        if (n <= 0) throw new IllegalArgumentException("额度须为正整数");
        ensureAccount(u);
        db().update("UPDATE balance_account SET balance = balance + ? WHERE username=? AND subject_id=1", n, u);
        String why = clip(reason, 255);
        if (why.isBlank()) why = "额度增加";
        db().update(
                "INSERT INTO balance_ledger (username, subject_id, delta_qty, reason, ref_type, ref_id) "
                        + "VALUES (?, 1, ?, ?, 'adjust', NULL)",
                u, n, why);
        return getAccount(u);
    }

    public static Map<String, Object> creditFromBody(Map<String, Object> body) {
        require();
        Map<String, Object> b = body == null ? Map.of() : body;
        String target = clip(str(b.get("username")), 64);
        if (target.isBlank()) throw new IllegalArgumentException("用户名无效");
        int n = qty(b.get("qty") != null ? b.get("qty") : b.get("deltaQty"));
        String reason = str(b.get("reason"));
        if (reason.isBlank()) reason = "管理端调整";
        return credit(target, n, reason);
    }

    /** 审批通过前扣减；余额不足抛错。 */
    public static void debitForTicketApprove(Map<String, Object> ticket) {
        if (!enabled || !debitOnApprove || !ready() || ticket == null) return;
        String u = clip(str(ticket.get("username")), 64);
        if (u.isBlank()) throw new IllegalStateException("单据缺少申请人");
        int need = 1;
        Object qtyObj = ticket.get("qty");
        if (qtyObj instanceof Number num && num.intValue() > 0) {
            need = num.intValue();
        } else if (qtyObj != null && !String.valueOf(qtyObj).isBlank()) {
            need = qty(qtyObj);
        }
        long ticketId = 0L;
        Object id = ticket.get("id");
        if (id instanceof Number n) ticketId = n.longValue();
        else if (id != null && !String.valueOf(id).isBlank()) {
            try {
                ticketId = Long.parseLong(String.valueOf(id));
            } catch (Exception ignored) {
            }
        }
        ensureAccount(u);
        Map<String, Object> acc = getAccount(u);
        int bal = acc.get("balance") instanceof Number n ? n.intValue() : 0;
        if (bal < need) {
            String unit = unitLabel();
            throw new IllegalStateException(
                    "额度不足（当前 " + bal + " " + unit + "，需扣减 " + need + " " + unit + "）");
        }
        db().update(
                "UPDATE balance_account SET balance = balance - ? WHERE username=? AND subject_id=1",
                need, u);
        db().update(
                "INSERT INTO balance_ledger (username, subject_id, delta_qty, reason, ref_type, ref_id) "
                        + "VALUES (?, 1, ?, '审批扣减', 'debit', ?)",
                u, -need, ticketId > 0 ? ticketId : null);
    }
}
