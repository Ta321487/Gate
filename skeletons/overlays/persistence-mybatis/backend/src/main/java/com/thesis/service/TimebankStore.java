package com.thesis.service;

import com.thesis.config.MybatisSupport;
import com.thesis.config.MbSql;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 时间银行：时长账户、流水加减；核销审批时扣减。
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

    private static MbSql db() {
        return MybatisSupport.db();
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

    private static boolean hasAccountColumn(String col) {
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS "
                            + "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='tb_account' AND COLUMN_NAME=?",
                    Integer.class, col);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    private static boolean tableExists(String table) {
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name=?",
                    Integer.class, table);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    private static Map<String, Object> mapAccount(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        BigDecimal bal = rs.getBigDecimal("balance_hours");
        m.put("balanceHours", bal);
        try {
            m.put("skillTags", rs.getString("skill_tags"));
        } catch (Exception ignored) {
            m.put("skillTags", "");
        }
        try {
            m.put("skillCertified", rs.getInt("skill_certified"));
        } catch (Exception ignored) {
            m.put("skillCertified", 0);
        }
        try {
            m.put("creditScore", rs.getInt("credit_score"));
        } catch (Exception ignored) {
            m.put("creditScore", 100);
        }
        BigDecimal frozen = BigDecimal.ZERO;
        try {
            frozen = rs.getBigDecimal("frozen_hours");
            if (frozen == null) frozen = BigDecimal.ZERO;
        } catch (Exception ignored) {
            frozen = BigDecimal.ZERO;
        }
        m.put("frozenHours", frozen);
        BigDecimal avail = bal == null ? BigDecimal.ZERO : bal.subtract(frozen);
        if (avail.compareTo(BigDecimal.ZERO) < 0) avail = BigDecimal.ZERO;
        m.put("availableHours", avail);
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
        if (qty == null || String.valueOf(qty).isBlank() || "null".equalsIgnoreCase(String.valueOf(qty))) {
            h = BigDecimal.ONE;
        } else if (qty instanceof Number n && n.doubleValue() > 0) {
            h = BigDecimal.valueOf(n.doubleValue()).setScale(2, RoundingMode.HALF_UP);
        } else {
            h = hours(qty);
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
        BigDecimal avail = (BigDecimal) acc.get("availableHours");
        if (avail == null) {
            BigDecimal bal = (BigDecimal) acc.get("balanceHours");
            avail = bal == null ? BigDecimal.ZERO : bal;
        }
        if (avail.compareTo(h) < 0) {
            throw new IllegalStateException(
                    "可用时长不足（当前可用 " + avail + " 小时，需核销 " + h + " 小时）");
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

    /** 按时长余额排行（只读）。 */
    public static List<Map<String, Object>> rankByHours(int limit) {
        require();
        int lim = Math.max(1, Math.min(100, limit));
        return db().query(
                "SELECT username, balance_hours AS balanceHours FROM tb_account "
                        + "ORDER BY balance_hours DESC, id ASC LIMIT ?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("rank", i + 1);
                    m.put("username", rs.getString("username"));
                    m.put("balanceHours", rs.getBigDecimal("balanceHours"));
                    return m;
                },
                lim);
    }

    /** 流水 CSV（管理端对账导出）。 */
    public static String exportLedgerCsv(String username) {
        require();
        String u = clip(username, 64);
        List<Map<String, Object>> rows;
        if (u.isBlank()) {
            rows = db().query(
                    "SELECT id, username, delta_hours, reason, ref_type, ref_id, created_at "
                            + "FROM tb_ledger ORDER BY id DESC LIMIT 5000",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("id", rs.getLong("id"));
                        m.put("username", rs.getString("username"));
                        m.put("delta", rs.getBigDecimal("delta_hours"));
                        m.put("reason", rs.getString("reason"));
                        m.put("refType", rs.getString("ref_type"));
                        m.put("refId", rs.getObject("ref_id"));
                        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
                        return m;
                    });
        } else {
            rows = db().query(
                    "SELECT id, username, delta_hours, reason, ref_type, ref_id, created_at "
                            + "FROM tb_ledger WHERE username=? ORDER BY id DESC LIMIT 5000",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("id", rs.getLong("id"));
                        m.put("username", rs.getString("username"));
                        m.put("delta", rs.getBigDecimal("delta_hours"));
                        m.put("reason", rs.getString("reason"));
                        m.put("refType", rs.getString("ref_type"));
                        m.put("refId", rs.getObject("ref_id"));
                        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
                        return m;
                    },
                    u);
        }
        StringBuilder sb = new StringBuilder("id,username,delta_hours,reason,ref_type,ref_id,created_at\n");
        for (Map<String, Object> r : rows) {
            sb.append(r.get("id")).append(',')
                    .append(csv(r.get("username"))).append(',')
                    .append(r.get("delta")).append(',')
                    .append(csv(r.get("reason"))).append(',')
                    .append(csv(r.get("refType"))).append(',')
                    .append(r.get("refId") == null ? "" : r.get("refId")).append(',')
                    .append(csv(r.get("createdAt"))).append('\n');
        }
        return sb.toString();
    }

    private static String csv(Object o) {
        String s = o == null ? "" : String.valueOf(o).replace("\"", "\"\"");
        if (s.contains(",") || s.contains("\"") || s.contains("\n")) {
            return "\"" + s + "\"";
        }
        return s;
    }

    /** 更新技能标签 / 认证勾选。 */
    public static Map<String, Object> updateSkills(
            String username, String skillTags, Boolean certified, boolean admin) {
        require();
        String u = clip(username, 64);
        if (u.isBlank()) throw new IllegalArgumentException("用户名无效");
        ensureAccount(u);
        if (hasAccountColumn("skill_tags") && skillTags != null) {
            db().update(
                    "UPDATE tb_account SET skill_tags=? WHERE username=?",
                    clip(skillTags, 255), u);
        }
        if (admin && certified != null && hasAccountColumn("skill_certified")) {
            db().update(
                    "UPDATE tb_account SET skill_certified=? WHERE username=?",
                    certified ? 1 : 0, u);
        }
        return getAccount(u);
    }

    /** 冻结 / 解冻时长。 */
    public static Map<String, Object> adjustFreeze(String username, BigDecimal hours, boolean freeze) {
        require();
        if (!hasAccountColumn("frozen_hours")) {
            throw new IllegalStateException("当前未开通时长冻结");
        }
        String u = clip(username, 64);
        if (u.isBlank()) throw new IllegalArgumentException("用户名无效");
        BigDecimal h = hours == null ? null : hours.setScale(2, RoundingMode.HALF_UP);
        if (h == null || h.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("小时数须为正数");
        }
        ensureAccount(u);
        Map<String, Object> acc = getAccount(u);
        BigDecimal bal = (BigDecimal) acc.get("balanceHours");
        if (bal == null) bal = BigDecimal.ZERO;
        BigDecimal frozen = (BigDecimal) acc.get("frozenHours");
        if (frozen == null) frozen = BigDecimal.ZERO;
        if (freeze) {
            BigDecimal avail = bal.subtract(frozen);
            if (avail.compareTo(h) < 0) {
                throw new IllegalStateException("可冻结时长不足");
            }
            db().update(
                    "UPDATE tb_account SET frozen_hours = frozen_hours + ? WHERE username=?",
                    h, u);
        } else {
            if (frozen.compareTo(h) < 0) {
                throw new IllegalStateException("冻结时长不足，无法解冻这么多");
            }
            db().update(
                    "UPDATE tb_account SET frozen_hours = frozen_hours - ? WHERE username=?",
                    h, u);
        }
        return getAccount(u);
    }

    /** 爽约扣信用分。 */
    public static void penalizeCredit(String username, int delta) {
        if (!enabled || !ready() || !hasAccountColumn("credit_score")) return;
        String u = clip(username, 64);
        if (u.isBlank() || delta <= 0) return;
        ensureAccount(u);
        db().update(
                "UPDATE tb_account SET credit_score = GREATEST(0, credit_score - ?) WHERE username=?",
                delta, u);
    }

    /** 时长转让（流水。 */
    public static Map<String, Object> transfer(String fromUser, String toUser, BigDecimal hours, String reason) {
        require();
        String from = clip(fromUser, 64);
        String to = clip(toUser, 64);
        if (from.isBlank() || to.isBlank()) throw new IllegalArgumentException("账号无效");
        if (from.equals(to)) throw new IllegalArgumentException("不能转让给自己");
        BigDecimal h = hours == null ? null : hours.setScale(2, RoundingMode.HALF_UP);
        if (h == null || h.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("转让小时数须为正数");
        }
        ensureAccount(from);
        ensureAccount(to);
        Map<String, Object> acc = getAccount(from);
        BigDecimal avail = (BigDecimal) acc.get("availableHours");
        if (avail == null) avail = BigDecimal.ZERO;
        if (avail.compareTo(h) < 0) {
            throw new IllegalStateException("可用时长不足，无法转让");
        }
        String why = clip(reason, 255);
        if (why.isBlank()) why = "时长转让";
        db().update("UPDATE tb_account SET balance_hours = balance_hours - ? WHERE username=?", h, from);
        db().update("UPDATE tb_account SET balance_hours = balance_hours + ? WHERE username=?", h, to);
        db().update(
                "INSERT INTO tb_ledger (username, delta_hours, reason, ref_type, ref_id) VALUES (?,?,?,?,NULL)",
                from, h.negate(), why + "→" + to, "transfer");
        db().update(
                "INSERT INTO tb_ledger (username, delta_hours, reason, ref_type, ref_id) VALUES (?,?,?,?,NULL)",
                to, h, why + "←" + from, "transfer");
        return getAccount(from);
    }

    public static List<Map<String, Object>> listCatalog(boolean onlyEnabled) {
        require();
        if (!tableExists("tb_catalog")) return List.of();
        String sql = onlyEnabled
                ? "SELECT * FROM tb_catalog WHERE enabled=1 AND stock>0 ORDER BY id DESC"
                : "SELECT * FROM tb_catalog ORDER BY id DESC";
        return db().query(sql, (rs, i) -> mapCatalog(rs));
    }

    private static Map<String, Object> mapCatalog(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("title", rs.getString("title"));
        m.put("costHours", rs.getBigDecimal("cost_hours"));
        m.put("stock", rs.getInt("stock"));
        m.put("enabled", rs.getInt("enabled"));
        m.put("remark", rs.getString("remark"));
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        return m;
    }

    public static Map<String, Object> saveCatalog(Long id, String title, BigDecimal cost, int stock, boolean enabled, String remark) {
        require();
        if (!tableExists("tb_catalog")) throw new IllegalStateException("兑换目录未就绪");
        String t = clip(title, 120);
        if (t.isBlank()) throw new IllegalArgumentException("请填写名称");
        BigDecimal c = cost == null ? BigDecimal.ONE : cost.setScale(2, RoundingMode.HALF_UP);
        if (c.compareTo(BigDecimal.ZERO) <= 0) throw new IllegalArgumentException("所需时长须为正数");
        int st = Math.max(0, Math.min(9999, stock));
        String note = clip(remark, 255);
        if (id == null || id <= 0) {
            db().update(
                    "INSERT INTO tb_catalog (title, cost_hours, stock, enabled, remark) VALUES (?,?,?,?,?)",
                    t, c, st, enabled ? 1 : 0, note);
            Long newId = db().queryForObject("SELECT MAX(id) FROM tb_catalog", Long.class);
            return listCatalog(false).stream()
                    .filter(r -> Objects.equals(r.get("id"), newId))
                    .findFirst()
                    .orElse(Map.of("id", newId));
        }
        db().update(
                "UPDATE tb_catalog SET title=?, cost_hours=?, stock=?, enabled=?, remark=? WHERE id=?",
                t, c, st, enabled ? 1 : 0, note, id);
        return listCatalog(false).stream()
                .filter(r -> Objects.equals(r.get("id"), id))
                .findFirst()
                .orElse(Map.of("id", id));
    }

    public static Map<String, Object> redeemCatalog(String username, long catalogId) {
        require();
        if (!tableExists("tb_catalog")) throw new IllegalStateException("兑换目录未就绪");
        String u = clip(username, 64);
        if (u.isBlank()) throw new IllegalArgumentException("用户名无效");
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM tb_catalog WHERE id=? AND enabled=1",
                (rs, i) -> mapCatalog(rs), catalogId);
        if (rows.isEmpty()) throw new IllegalArgumentException("兑换项目不存在或已下架");
        Map<String, Object> cat = rows.get(0);
        int stock = ((Number) cat.get("stock")).intValue();
        if (stock <= 0) throw new IllegalStateException("库存不足");
        BigDecimal cost = (BigDecimal) cat.get("costHours");
        ensureAccount(u);
        Map<String, Object> acc = getAccount(u);
        BigDecimal avail = (BigDecimal) acc.get("availableHours");
        if (avail == null) avail = BigDecimal.ZERO;
        if (avail.compareTo(cost) < 0) {
            throw new IllegalStateException("可用时长不足");
        }
        Object scoreObj = acc.get("creditScore");
        int score = scoreObj instanceof Number n ? n.intValue() : 100;
        if (score < 60) {
            throw new IllegalStateException("信用分过低，暂不可兑换");
        }
        int n = db().update(
                "UPDATE tb_catalog SET stock=stock-1 WHERE id=? AND stock>=1", catalogId);
        if (n <= 0) throw new IllegalStateException("库存不足");
        db().update("UPDATE tb_account SET balance_hours = balance_hours - ? WHERE username=?", cost, u);
        db().update(
                "INSERT INTO tb_ledger (username, delta_hours, reason, ref_type, ref_id) VALUES (?,?,?,?,?)",
                u, cost.negate(), "兑换：" + cat.get("title"), "catalog", catalogId);
        return getAccount(u);
    }

    public static Map<String, Object> submitAppeal(String username, String reason) {
        require();
        if (!tableExists("tb_appeal")) throw new IllegalStateException("申诉功能未就绪");
        String u = clip(username, 64);
        String why = clip(reason, 255);
        if (u.isBlank()) throw new IllegalArgumentException("用户名无效");
        if (why.isBlank()) throw new IllegalArgumentException("请填写申诉说明");
        db().update(
                "INSERT INTO tb_appeal (username, reason, status) VALUES (?,?, 'pending')",
                u, why);
        Long id = db().queryForObject("SELECT MAX(id) FROM tb_appeal WHERE username=?", Long.class, u);
        return Map.of("id", id == null ? 0 : id, "status", "pending");
    }

    public static Map<String, Object> pageAppeals(int page, int size, String username) {
        require();
        if (!tableExists("tb_appeal")) return pageOut(List.of(), 0, page, size);
        if (page < 1) page = 1;
        if (size < 1) size = 20;
        String u = clip(username, 64);
        Integer total;
        List<Map<String, Object>> list;
        if (u.isBlank()) {
            total = db().queryForObject("SELECT COUNT(*) FROM tb_appeal", Integer.class);
            list = db().query(
                    "SELECT * FROM tb_appeal ORDER BY id DESC LIMIT ? OFFSET ?",
                    (rs, i) -> mapAppeal(rs), size, (page - 1) * size);
        } else {
            total = db().queryForObject(
                    "SELECT COUNT(*) FROM tb_appeal WHERE username=?", Integer.class, u);
            list = db().query(
                    "SELECT * FROM tb_appeal WHERE username=? ORDER BY id DESC LIMIT ? OFFSET ?",
                    (rs, i) -> mapAppeal(rs), u, size, (page - 1) * size);
        }
        return pageOut(list, total, page, size);
    }

    private static Map<String, Object> mapAppeal(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("reason", rs.getString("reason"));
        m.put("status", rs.getString("status"));
        m.put("adminRemark", rs.getString("admin_remark"));
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        return m;
    }

    public static Map<String, Object> resolveAppeal(long id, boolean pass, String adminRemark) {
        require();
        if (!tableExists("tb_appeal")) throw new IllegalStateException("申诉功能未就绪");
        String note = clip(adminRemark, 255);
        String st = pass ? "approved" : "rejected";
        int n = db().update(
                "UPDATE tb_appeal SET status=?, admin_remark=? WHERE id=? AND status='pending'",
                st, note, id);
        if (n <= 0) throw new IllegalStateException("申诉不存在或已处理");
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM tb_appeal WHERE id=?", (rs, i) -> mapAppeal(rs), id);
        return rows.isEmpty() ? Map.of("id", id, "status", st) : rows.get(0);
    }

    public static String getClearRule() {
        require();
        if (!tableExists("tb_clear_rule")) return "";
        try {
            List<String> rows = db().query(
                    "SELECT body FROM tb_clear_rule ORDER BY id DESC LIMIT 1",
                    (rs, i) -> rs.getString("body"));
            return rows.isEmpty() || rows.get(0) == null ? "" : rows.get(0);
        } catch (Exception e) {
            return "";
        }
    }

    public static String saveClearRule(String body) {
        require();
        if (!tableExists("tb_clear_rule")) throw new IllegalStateException("清零说明未就绪");
        String text = clip(body, 512);
        Integer n = db().queryForObject("SELECT COUNT(*) FROM tb_clear_rule", Integer.class);
        if (n == null || n == 0) {
            db().update("INSERT INTO tb_clear_rule (body) VALUES (?)", text);
        } else {
            Long rid = db().queryForObject("SELECT id FROM tb_clear_rule ORDER BY id DESC LIMIT 1", Long.class);
            if (rid != null) {
                db().update("UPDATE tb_clear_rule SET body=? WHERE id=?", text, rid);
            } else {
                db().update("INSERT INTO tb_clear_rule (body) VALUES (?)", text);
            }
        }
        return text;
    }
}
