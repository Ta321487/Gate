package com.thesis.service;

import com.thesis.capability.TicketStore;
import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 房源成交台账旁路岛：带看跟进办结后登记成交价与成交日。
 * 只记成交事实，不接管交易/支付；房源档案仍由档案维护。
 */
public class ListingDealStore {

    private static Boolean tableReady;

    private ListingDealStore() {}

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    public static boolean ready() {
        if (tableReady != null) return tableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='listing_deal'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static void require() {
        if (!ready()) throw new IllegalStateException("成交登记暂不可用");
    }

    private static String clip(String s, int max) {
        if (s == null) return "";
        String t = s.trim();
        return t.length() <= max ? t : t.substring(0, max);
    }

    private static Object blankToNull(String s) {
        return s == null || s.trim().isEmpty() ? null : s.trim();
    }

    private static String ticketTable() {
        String t = TicketStore.ticketTable();
        return t == null ? "" : t.trim();
    }

    private static String selectSql(String tail) {
        String t = ticketTable();
        if (t.isEmpty()) {
            return "SELECT d.id, d.ticket_id, '' AS username, d.deal_price, d.deal_at, "
                    + "d.operator, d.remark, d.created_at FROM listing_deal d " + tail;
        }
        return "SELECT d.id, d.ticket_id, IFNULL(t.username,'') AS username, d.deal_price, d.deal_at, "
                + "d.operator, d.remark, d.created_at "
                + "FROM listing_deal d LEFT JOIN `" + t + "` t ON t.id=d.ticket_id " + tail;
    }

    private static Map<String, Object> mapRow(ResultSet rs, int rowNum) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("ticketId", rs.getLong("ticket_id"));
        m.put("username", rs.getString("username"));
        BigDecimal price = rs.getBigDecimal("deal_price");
        m.put("dealPrice", price == null ? "0" : price.stripTrailingZeros().toPlainString());
        m.put("dealAt", rs.getString("deal_at"));
        m.put("operator", rs.getString("operator"));
        m.put("remark", rs.getString("remark"));
        m.put("createdAt", rs.getString("created_at"));
        return m;
    }

    /** 管理端：成交台账（含看房客户账号）。 */
    public static List<Map<String, Object>> listAdmin() {
        require();
        return db().query(selectSql("ORDER BY d.id DESC LIMIT 200"), (rs, i) -> mapRow(rs, i));
    }

    /** 登记成交：跟进单须已办结（未通过/待审一律拒）。 */
    public static Map<String, Object> save(
            long ticketId, BigDecimal dealPrice, String dealAt, String operator, String remark) {
        require();
        String t = ticketTable();
        if (t.isEmpty()) throw new IllegalStateException("当前系统没有带看跟进单");
        if (ticketId <= 0) throw new IllegalArgumentException("请选择带看跟进单");
        if (dealPrice == null) throw new IllegalArgumentException("请填写成交价");
        BigDecimal price = dealPrice.setScale(2, RoundingMode.HALF_UP);
        if (price.compareTo(BigDecimal.ZERO) < 0) throw new IllegalArgumentException("成交价不能为负");
        List<Map<String, Object>> rows = db().query(
                "SELECT status FROM `" + t + "` WHERE id=?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("status", rs.getString("status"));
                    return m;
                },
                ticketId);
        if (rows.isEmpty()) throw new IllegalArgumentException("跟进单不存在");
        String st = String.valueOf(rows.get(0).get("status"));
        if ("pending".equals(st)
                || "pending_mid".equals(st)
                || "pending_final".equals(st)
                || "rejected".equals(st)) {
            throw new IllegalStateException("仅已办结的带看跟进可登记成交");
        }
        db().update(
                "INSERT INTO listing_deal (ticket_id, deal_price, deal_at, operator, remark) "
                        + "VALUES (?,?,?,?,?)",
                ticketId,
                price,
                blankToNull(dealAt),
                clip(operator, 64),
                clip(remark, 255));
        List<Map<String, Object>> out = db().query(
                selectSql("WHERE d.ticket_id=? ORDER BY d.id DESC LIMIT 1"),
                (rs, i) -> mapRow(rs, i),
                ticketId);
        if (out.isEmpty()) throw new IllegalStateException("成交登记后未能读回");
        return out.get(0);
    }

    /** 成交总额（答辩口径：台账只记事实）。 */
    public static String total() {
        require();
        BigDecimal sum = db().queryForObject(
                "SELECT IFNULL(SUM(deal_price),0) FROM listing_deal", BigDecimal.class);
        return sum == null ? "0" : sum.stripTrailingZeros().toPlainString();
    }

    public static void remove(long id) {
        require();
        int n = db().update("DELETE FROM listing_deal WHERE id=?", id);
        if (n == 0) throw new IllegalArgumentException("成交记录不存在");
    }
}
