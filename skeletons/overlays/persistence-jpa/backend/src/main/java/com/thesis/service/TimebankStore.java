package com.thesis.service;

import com.thesis.config.JpaSupport;
import com.thesis.config.JpaDb;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 时间银行（C-14）：时长账户、流水加减；核销审批时扣减。
 */
public class TimebankStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static boolean enabled;
    private static boolean redeemOnApprove;
    private static Boolean tableReady;

    private TimebankStore() {}

    public static void configure(boolean on, boolean redeemApprove) {
        enabled = on;
        redeemOnApprove = redeemApprove;
        tableReady = null;
    }

    public static boolean enabled() {
        return enabled;
    }

    public static boolean redeemOnApprove() {
        return redeemOnApprove;
    }

    private static JpaDb db() {
        return JpaSupport.db();
    }

    public static boolean ready() {
        if (!enabled) return false;
        if (tableReady != null) return tableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='tb_account'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static void require() {
        if (!ready()) throw new IllegalStateException("时间银行功能暂不可用");
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

    private static BigDecimal hours(Object o) {
        if (o == null || String.valueOf(o).isBlank()) {
            throw new IllegalArgumentException("小时数无效");
        }
        BigDecimal h = new BigDecimal(String.valueOf(o).trim()).setScale(2, RoundingMode.HALF_UP);
        if (h.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("小时数须为正数");
        }
        if (h.compareTo(new BigDecimal("9999")) > 0) {
            throw new IllegalArgumentException("单次小时数过大");
        }
        return h;
    }

    private static Map<String, Object> pageOut(List<?> list, Integer total, int page, int size) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    private static Map<String, Object> mapAccount(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("balanceHours", rs.getBigDecimal("balance_hours"));
        m.put("updatedAt", fmt(rs.getTimestamp("updated_at")));
        return m;
    }

    private static Map<String, Object> mapLedger(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("deltaHours", rs.getBigDecimal("delta_hours"));
        m.put("reason", rs.getString("reason"));
        m.put("refType", rs.getString("ref_type"));
        m.put("refId", rs.getObject("ref_id"));
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        return m;
    }

    private static void ensureAccount(String username) {
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM tb_account WHERE username=?", Integer.class, username);
        if (n == null || n == 0) {
            db().update("INSERT INTO tb_account (username, balance_hours) VALUES (?, 0)", username);
        }
    }

    public static Map<String, Object> getAccount(String username) {
        require();
        String u = clip(username, 64);
        if (u.isBlank()) throw new IllegalArgumentException("用户名无效");
        ensureAccount(u);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM tb_account WHERE username=?", (rs, i) -> mapAccount(rs), u);
        return list.isEmpty() ? Map.of() : list.get(0);
    }

    public static Map<String, Object> pageAccounts(int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 20;
        Integer total = db().queryForObject("SELECT COUNT(*) FROM tb_account", Integer.class);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM tb_account ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?",
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
                "SELECT COUNT(*) FROM tb_ledger WHERE username=?", Integer.class, u);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM tb_ledger WHERE username=? ORDER BY id DESC LIMIT ? OFFSET ?",
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
            total = db().queryForObject("SELECT COUNT(*) FROM tb_ledger", Integer.class);
            list = db().query(
                    "SELECT * FROM tb_ledger ORDER BY id DESC LIMIT ? OFFSET ?",
                    (rs, i) -> mapLedger(rs),
                    size, (page - 1) * size);
        } else {
            total = db().queryForObject(
                    "SELECT COUNT(*) FROM tb_ledger WHERE username=?", Integer.class, u);
            list = db().query(
                    "SELECT * FROM tb_ledger WHERE username=? ORDER BY id DESC LIMIT ? OFFSET ?",
                    (rs, i) -> mapLedger(rs),
                    u, size, (page - 1) * size);
        }
        return pageOut(list, total, page, size);
    }

    /** 存入（正数小时）；用户自助或管理端调整。 */
    public static Map<String, Object> credit(
            String username, BigDecimal hours, String reason, Long serviceId) {
        require();
        String u = clip(username, 64);
        if (u.isBlank()) throw new IllegalArgumentException("用户名无效");
        BigDecimal h = hours == null ? null : hours.setScale(2, RoundingMode.HALF_UP);
        if (h == null || h.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("存入小时数须为正数");
        }
        if (serviceId != null && serviceId > 0) {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM tb_service WHERE id=? AND status='available'",
                    Integer.class, serviceId);
            if (n == null || n == 0) throw new IllegalArgumentException("服务事项不存在或未开放");
        }
        ensureAccount(u);
        db().update(
                "UPDATE tb_account SET balance_hours = balance_hours + ? WHERE username=?",
                h, u);
        String why = clip(reason, 255);
        if (why.isBlank()) why = "存入时长";
        db().update(
                "INSERT INTO tb_ledger (username, delta_hours, reason, ref_type, ref_id) VALUES (?,?,?,?,?)",
                u, h, why, serviceId != null && serviceId > 0 ? "service" : "adjust", serviceId);
        return getAccount(u);
    }

    public static Map<String, Object> creditFromBody(String actor, Map<String, Object> body, boolean admin) {
        require();
        String target = admin ? clip(str(body.get("username")), 64) : clip(actor, 64);
        if (!admin) target = clip(actor, 64);
        if (target.isBlank()) throw new IllegalArgumentException("用户名无效");
        BigDecimal h = hours(body.get("hours") != null ? body.get("hours") : body.get("deltaHours"));
        String reason = str(body.get("reason"));
        Long serviceId = null;
        Object sid = body.get("serviceId");
        if (sid == null) sid = body.get("service_id");
        if (sid != null && !String.valueOf(sid).isBlank()) {
            serviceId = Long.parseLong(String.valueOf(sid));
        }
        if (!admin && (serviceId == null || serviceId <= 0)) {
            throw new IllegalArgumentException("请选择服务事项");
        }
        if (reason.isBlank()) {
            reason = admin ? "管理端调整存入" : "服务事项存入";
        }
        return credit(target, h, reason, serviceId);
    }

    /** 核销审批通过前扣减；余额不足抛错。 */
    public static void debitForTicketApprove(Map<String, Object> ticket) {
        if (!enabled || !redeemOnApprove || !ready() || ticket == null) return;
        String u = clip(str(ticket.get("username")), 64);
        if (u.isBlank()) throw new IllegalStateException("核销单据缺少申请人");
        BigDecimal h;
        Object qty = ticket.get("qty");
        if (qty instanceof Number n && n.doubleValue() > 0) {
            h = BigDecimal.valueOf(n.doubleValue()).setScale(2, RoundingMode.HALF_UP);
        } else {
            try {
                h = hours(qty);
            } catch (Exception e) {
                h = BigDecimal.ONE;
            }
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
        BigDecimal bal = (BigDecimal) acc.get("balanceHours");
        if (bal == null) bal = BigDecimal.ZERO;
        if (bal.compareTo(h) < 0) {
            throw new IllegalStateException("时长余额不足（当前 " + bal + " 小时，需核销 " + h + " 小时）");
        }
        db().update(
                "UPDATE tb_account SET balance_hours = balance_hours - ? WHERE username=?",
                h, u);
        db().update(
                "INSERT INTO tb_ledger (username, delta_hours, reason, ref_type, ref_id) VALUES (?,?,?,?,?)",
                u, h.negate(), "核销扣减", "redeem", ticketId > 0 ? ticketId : null);
    }

    public static List<Map<String, Object>> listOpenServices() {
        require();
        return db().query(
                "SELECT id, title, author, isbn, category_id AS categoryId, stock, status "
                        + "FROM tb_service WHERE status='available' AND stock>0 ORDER BY id DESC",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("title", rs.getString("title"));
                    m.put("author", rs.getString("author"));
                    m.put("isbn", rs.getString("isbn"));
                    m.put("categoryId", rs.getObject("categoryId"));
                    m.put("stock", rs.getInt("stock"));
                    m.put("status", rs.getString("status"));
                    return m;
                });
    }
}
