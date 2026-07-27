package com.thesis.service;

import com.thesis.config.MybatisSupport;
import com.thesis.mapper.TimebankMapper;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/** 时间银行（C-14）MyBatis 叠层。 */
public class TimebankStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static boolean enabled;
    private static boolean redeemOnApprove;
    private static Boolean tableReady;

    private TimebankStore() {}

    private static TimebankMapper mapper() {
        return MybatisSupport.mapper(TimebankMapper.class);
    }

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

    public static boolean ready() {
        if (!enabled) return false;
        if (tableReady != null) return tableReady;
        try {
            Integer n = mapper().countTable();
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
        if (o instanceof java.util.Date d) return new Timestamp(d.getTime()).toLocalDateTime().format(FMT);
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

    private static void normalize(List<Map<String, Object>> rows, String... keys) {
        for (Map<String, Object> m : rows) {
            for (String k : keys) {
                if (m.containsKey(k)) m.put(k, fmt(m.get(k)));
            }
        }
    }

    private static void ensureAccount(String username) {
        Integer n = mapper().countAccount(username);
        if (n == null || n == 0) {
            mapper().insertAccount(username);
        }
    }

    public static Map<String, Object> getAccount(String username) {
        require();
        String u = clip(username, 64);
        if (u.isBlank()) throw new IllegalArgumentException("用户名无效");
        ensureAccount(u);
        Map<String, Object> m = mapper().getAccount(u);
        if (m != null && m.containsKey("updatedAt")) m.put("updatedAt", fmt(m.get("updatedAt")));
        return m == null ? Map.of() : m;
    }

    public static Map<String, Object> pageAccounts(int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 20;
        Integer total = mapper().countAccounts();
        List<Map<String, Object>> list = mapper().pageAccounts(size, (page - 1) * size);
        normalize(list, "updatedAt");
        return pageOut(list, total, page, size);
    }

    public static Map<String, Object> pageLedgerMine(String username, int page, int size) {
        require();
        String u = clip(username, 64);
        if (page < 1) page = 1;
        if (size < 1) size = 20;
        Integer total = mapper().countLedgerMine(u);
        List<Map<String, Object>> list = mapper().pageLedgerMine(u, size, (page - 1) * size);
        normalize(list, "createdAt");
        return pageOut(list, total, page, size);
    }

    public static Map<String, Object> pageLedgerAdmin(int page, int size, String username) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 20;
        String u = clip(username, 64);
        if (u.isBlank()) {
            Integer total = mapper().countLedgerAll();
            List<Map<String, Object>> list = mapper().pageLedgerAll(size, (page - 1) * size);
            normalize(list, "createdAt");
            return pageOut(list, total, page, size);
        }
        return pageLedgerMine(u, page, size);
    }

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
            Integer n = mapper().countOpenService(serviceId);
            if (n == null || n == 0) throw new IllegalArgumentException("服务事项不存在或未开放");
        }
        ensureAccount(u);
        mapper().addBalance(u, h);
        String why = clip(reason, 255);
        if (why.isBlank()) why = "存入时长";
        mapper().insertLedger(
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
        Object balObj = acc.get("balanceHours");
        BigDecimal bal = balObj instanceof BigDecimal b
                ? b
                : new BigDecimal(String.valueOf(balObj == null ? "0" : balObj));
        if (bal.compareTo(h) < 0) {
            throw new IllegalStateException("时长余额不足（当前 " + bal + " 小时，需核销 " + h + " 小时）");
        }
        mapper().subBalance(u, h);
        mapper().insertLedger(u, h.negate(), "核销扣减", "redeem", ticketId > 0 ? ticketId : null);
    }

    public static List<Map<String, Object>> listOpenServices() {
        require();
        return mapper().listOpenServices();
    }
}
