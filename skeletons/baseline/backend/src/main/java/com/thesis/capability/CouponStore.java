package com.thesis.capability;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.config.JdbcSupport;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;

import java.io.InputStream;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 优惠券完整生命周期：券模板领取 → 我的券 → 下单核销 → 过期扫标。
 * 仍兼容下单直接填码（未领取的模板码）。
 */
public final class CouponStore {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final String PROMO = "promo_coupon";
    private static final String MINE = "user_coupon";

    private static boolean enabled;

    private CouponStore() {}

    public static void configure(boolean on) {
        enabled = on;
        if (enabled) {
            ensureTables();
            seedFromResourceIfEmpty();
        }
    }

    public static boolean enabled() {
        return enabled;
    }

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    private static void ensureTables() {
        try {
            db().execute(
                    "CREATE TABLE IF NOT EXISTS " + PROMO + " ("
                            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
                            + "code VARCHAR(32) NOT NULL,"
                            + "label VARCHAR(64) DEFAULT '',"
                            + "min_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,"
                            + "off_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,"
                            + "total_quota INT NOT NULL DEFAULT 0,"
                            + "claimed INT NOT NULL DEFAULT 0,"
                            + "expire_at DATETIME NULL,"
                            + "status VARCHAR(16) NOT NULL DEFAULT 'active',"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "UNIQUE KEY uk_promo_code (code)"
                            + ")");
            db().execute(
                    "CREATE TABLE IF NOT EXISTS " + MINE + " ("
                            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
                            + "username VARCHAR(64) NOT NULL,"
                            + "coupon_id BIGINT NOT NULL,"
                            + "status VARCHAR(16) NOT NULL DEFAULT 'unused',"
                            + "claimed_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "used_at DATETIME NULL,"
                            + "order_id BIGINT NULL,"
                            + "UNIQUE KEY uk_user_coupon (username, coupon_id),"
                            + "KEY idx_user_coupon_user (username, status, id)"
                            + ")");
        } catch (Exception ignored) {
        }
    }

    private static void seedFromResourceIfEmpty() {
        try {
            Integer n = db().queryForObject("SELECT COUNT(*) FROM " + PROMO, Integer.class);
            if (n != null && n > 0) return;
        } catch (Exception e) {
            return;
        }
        List<Map<String, Object>> seeds = loadSeedItems();
        Timestamp expire = Timestamp.valueOf(LocalDateTime.now().plusDays(90));
        for (Map<String, Object> c : seeds) {
            try {
                db().update(
                        "INSERT INTO " + PROMO + " (code,label,min_yuan,off_yuan,total_quota,claimed,expire_at,status) "
                                + "VALUES (?,?,?,?,0,0,?,'active')",
                        String.valueOf(c.getOrDefault("code", "")).trim().toUpperCase(Locale.ROOT),
                        String.valueOf(c.getOrDefault("label", "")),
                        toD(c.get("minYuan")),
                        toD(c.get("offYuan")),
                        expire);
            } catch (Exception ignored) {
            }
        }
    }

    private static List<Map<String, Object>> loadSeedItems() {
        try {
            ClassPathResource res = new ClassPathResource("domain-loyalty.json");
            if (res.exists()) {
                try (InputStream in = res.getInputStream()) {
                    Map<String, Object> root = JSON.readValue(in, new TypeReference<>() {});
                    Object cp = root.get("coupons");
                    if (cp instanceof Map<?, ?> map) {
                        Object items = map.get("items");
                        if (items instanceof List<?> list && !list.isEmpty()) {
                            List<Map<String, Object>> out = new ArrayList<>();
                            for (Object o : list) {
                                if (o instanceof Map<?, ?> m) {
                                    Map<String, Object> row = new LinkedHashMap<>();
                                    for (Map.Entry<?, ?> e : m.entrySet()) {
                                        row.put(String.valueOf(e.getKey()), e.getValue());
                                    }
                                    out.add(row);
                                }
                            }
                            if (!out.isEmpty()) return out;
                        }
                    }
                }
            }
        } catch (Exception ignored) {
        }
        return List.of(
                Map.of("code", "SAVE10", "label", "满50减10", "minYuan", 50, "offYuan", 10),
                Map.of("code", "WELCOME5", "label", "满30减5", "minYuan", 30, "offYuan", 5));
    }

    public static List<Map<String, Object>> listActiveTemplates() {
        require();
        expireSweep();
        return db().query(
                "SELECT * FROM " + PROMO + " WHERE status='active' ORDER BY id",
                (rs, i) -> mapPromo(rs));
    }

    public static Map<String, Object> pageAdmin(int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        Integer total = db().queryForObject("SELECT COUNT(*) FROM " + PROMO, Integer.class);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM " + PROMO + " ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> mapPromo(rs),
                size, (page - 1) * size);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list == null ? List.of() : list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    public static Map<String, Object> createTemplate(Map<String, Object> body) {
        require();
        String code = str(body.get("code")).toUpperCase(Locale.ROOT);
        if (code.isBlank()) throw new IllegalArgumentException("请填写券码");
        if (code.length() > 32) code = code.substring(0, 32);
        double min = toD(body.get("minYuan"));
        double off = toD(body.get("offYuan"));
        if (off <= 0) throw new IllegalArgumentException("优惠金额须大于 0");
        int quota = body.get("totalQuota") == null ? 0 : (int) toD(body.get("totalQuota"));
        Timestamp exp = parseTs(body.get("expireAt"));
        if (exp == null) exp = Timestamp.valueOf(LocalDateTime.now().plusDays(90));
        KeyHolder kh = new GeneratedKeyHolder();
        String finalCode = code;
        Timestamp finalExp = exp;
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO " + PROMO + " (code,label,min_yuan,off_yuan,total_quota,claimed,expire_at,status) "
                            + "VALUES (?,?,?,?,?,0,?,'active')",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, finalCode);
            ps.setString(2, str(body.get("label")));
            ps.setBigDecimal(3, bd(min));
            ps.setBigDecimal(4, bd(off));
            ps.setInt(5, Math.max(0, quota));
            ps.setTimestamp(6, finalExp);
            return ps;
        }, kh);
        Number key = kh.getKey();
        return getPromo(key == null ? 0L : key.longValue());
    }

    public static Map<String, Object> updateTemplate(long id, Map<String, Object> body) {
        require();
        Map<String, Object> cur = getPromo(id);
        if (cur == null) throw new IllegalArgumentException("券不存在");
        String label = body.containsKey("label") ? str(body.get("label")) : String.valueOf(cur.get("label"));
        String status = body.containsKey("status") ? str(body.get("status")) : String.valueOf(cur.get("status"));
        if (!"active".equals(status) && !"off".equals(status)) status = "active";
        double min = body.containsKey("minYuan") ? toD(body.get("minYuan")) : toD(cur.get("minYuan"));
        double off = body.containsKey("offYuan") ? toD(body.get("offYuan")) : toD(cur.get("offYuan"));
        int quota = body.containsKey("totalQuota") ? (int) toD(body.get("totalQuota")) : ((Number) cur.get("totalQuota")).intValue();
        Timestamp exp = body.containsKey("expireAt") ? parseTs(body.get("expireAt")) : parseTs(cur.get("expireAt"));
        db().update(
                "UPDATE " + PROMO + " SET label=?, min_yuan=?, off_yuan=?, total_quota=?, expire_at=?, status=? WHERE id=?",
                label, bd(min), bd(off), Math.max(0, quota), exp, status, id);
        return getPromo(id);
    }

    public static Map<String, Object> claim(String username, long couponId) {
        require();
        expireSweep();
        Map<String, Object> promo = getPromo(couponId);
        if (promo == null || !"active".equals(String.valueOf(promo.get("status")))) {
            throw new IllegalStateException("券不可领");
        }
        if (promo.get("expireAt") != null) {
            Timestamp exp = parseTs(promo.get("expireAt"));
            if (exp != null && exp.before(Timestamp.valueOf(LocalDateTime.now()))) {
                throw new IllegalStateException("券已过期");
            }
        }
        int quota = ((Number) promo.get("totalQuota")).intValue();
        int claimed = ((Number) promo.get("claimed")).intValue();
        if (quota > 0 && claimed >= quota) throw new IllegalStateException("券已领完");
        Integer mine = db().queryForObject(
                "SELECT COUNT(*) FROM " + MINE + " WHERE username=? AND coupon_id=?",
                Integer.class, username, couponId);
        if (mine != null && mine > 0) throw new IllegalStateException("您已领取过该券");
        db().update(
                "INSERT INTO " + MINE + " (username,coupon_id,status,claimed_at) VALUES (?,?, 'unused', ?)",
                username, couponId, Timestamp.valueOf(LocalDateTime.now()));
        db().update("UPDATE " + PROMO + " SET claimed=claimed+1 WHERE id=?", couponId);
        return getMineRow(username, couponId);
    }

    public static Map<String, Object> pageMine(String username, String status, int page, int size) {
        require();
        expireSweep();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        StringBuilder where = new StringBuilder(" WHERE u.username=?");
        List<Object> args = new ArrayList<>();
        args.add(username);
        if (status != null && !status.isBlank()) {
            where.append(" AND u.status=?");
            args.add(status);
        }
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM " + MINE + " u" + where, Integer.class, args.toArray());
        args.add(size);
        args.add((page - 1) * size);
        List<Map<String, Object>> list = db().query(
                "SELECT u.*, p.code, p.label, p.min_yuan, p.off_yuan, p.expire_at AS promo_expire "
                        + "FROM " + MINE + " u JOIN " + PROMO + " p ON p.id=u.coupon_id"
                        + where + " ORDER BY u.id DESC LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("couponId", rs.getLong("coupon_id"));
                    m.put("status", rs.getString("status"));
                    m.put("claimedAt", fmt(rs.getTimestamp("claimed_at")));
                    m.put("usedAt", fmt(rs.getTimestamp("used_at")));
                    long oid = rs.getLong("order_id");
                    if (!rs.wasNull()) m.put("orderId", oid);
                    m.put("code", rs.getString("code"));
                    m.put("label", rs.getString("label"));
                    m.put("minYuan", rs.getDouble("min_yuan"));
                    m.put("offYuan", rs.getDouble("off_yuan"));
                    m.put("expireAt", fmt(rs.getTimestamp("promo_expire")));
                    return m;
                },
                args.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list == null ? List.of() : list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    /** 下单算价：优先用户已领券码；否则匹配可领模板码。 */
    public static Map<String, Object> matchForCheckout(String username, String code, double amountYuan) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("ok", false);
        out.put("offYuan", 0);
        out.put("code", code == null ? "" : code.trim());
        if (!enabled || code == null || code.isBlank()) return out;
        expireSweep();
        String want = code.trim().toUpperCase(Locale.ROOT);
        // 1) 我的未用券
        if (username != null && !username.isBlank()) {
            List<Map<String, Object>> mine = db().query(
                    "SELECT u.id AS user_coupon_id, p.* FROM " + MINE + " u JOIN " + PROMO + " p ON p.id=u.coupon_id "
                            + "WHERE u.username=? AND u.status='unused' AND UPPER(p.code)=?",
                    (rs, i) -> {
                        Map<String, Object> m = mapPromo(rs);
                        m.put("userCouponId", rs.getLong("user_coupon_id"));
                        return m;
                    },
                    username, want);
            if (mine != null && !mine.isEmpty()) {
                return applyPromoHit(out, mine.get(0), amountYuan);
            }
        }
        // 2) 模板码（未领取也可演示核销）
        List<Map<String, Object>> promos = db().query(
                "SELECT * FROM " + PROMO + " WHERE status='active' AND UPPER(code)=?",
                (rs, i) -> mapPromo(rs),
                want);
        if (promos != null && !promos.isEmpty()) {
            return applyPromoHit(out, promos.get(0), amountYuan);
        }
        out.put("message", "券码无效");
        return out;
    }

    private static Map<String, Object> applyPromoHit(Map<String, Object> out, Map<String, Object> promo, double amountYuan) {
        Timestamp exp = parseTs(promo.get("expireAt"));
        if (exp != null && exp.before(Timestamp.valueOf(LocalDateTime.now()))) {
            out.put("message", "券已过期");
            return out;
        }
        double min = toD(promo.get("minYuan"));
        double off = toD(promo.get("offYuan"));
        if (amountYuan + 1e-9 < min) {
            out.put("message", "未满 ¥" + round2(min) + "，不可用该券");
            return out;
        }
        out.put("ok", true);
        out.put("offYuan", round2(off));
        out.put("code", promo.get("code"));
        out.put("label", promo.get("label"));
        if (promo.get("userCouponId") != null) out.put("userCouponId", promo.get("userCouponId"));
        return out;
    }

    public static void markUsed(String username, String code, long orderId) {
        if (!enabled || username == null || code == null || code.isBlank()) return;
        String want = code.trim().toUpperCase(Locale.ROOT);
        try {
            List<Long> ids = db().query(
                    "SELECT u.id FROM " + MINE + " u JOIN " + PROMO + " p ON p.id=u.coupon_id "
                            + "WHERE u.username=? AND u.status='unused' AND UPPER(p.code)=? LIMIT 1",
                    (rs, i) -> rs.getLong(1),
                    username, want);
            if (ids == null || ids.isEmpty()) return;
            db().update(
                    "UPDATE " + MINE + " SET status='used', used_at=?, order_id=? WHERE id=?",
                    Timestamp.valueOf(LocalDateTime.now()), orderId, ids.get(0));
        } catch (Exception ignored) {
        }
    }

    /** 定时：未用且模板已过期 → expired */
    public static int expireSweep() {
        if (!enabled) return 0;
        try {
            return db().update(
                    "UPDATE " + MINE + " u JOIN " + PROMO + " p ON p.id=u.coupon_id "
                            + "SET u.status='expired' "
                            + "WHERE u.status='unused' AND p.expire_at IS NOT NULL AND p.expire_at < NOW()");
        } catch (Exception e) {
            return 0;
        }
    }

    private static Map<String, Object> getPromo(long id) {
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM " + PROMO + " WHERE id=?", (rs, i) -> mapPromo(rs), id);
        return rows == null || rows.isEmpty() ? null : rows.get(0);
    }

    private static Map<String, Object> getMineRow(String username, long couponId) {
        List<Map<String, Object>> rows = db().query(
                "SELECT u.*, p.code, p.label, p.min_yuan, p.off_yuan, p.expire_at AS promo_expire "
                        + "FROM " + MINE + " u JOIN " + PROMO + " p ON p.id=u.coupon_id "
                        + "WHERE u.username=? AND u.coupon_id=?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("couponId", rs.getLong("coupon_id"));
                    m.put("status", rs.getString("status"));
                    m.put("code", rs.getString("code"));
                    m.put("label", rs.getString("label"));
                    m.put("minYuan", rs.getDouble("min_yuan"));
                    m.put("offYuan", rs.getDouble("off_yuan"));
                    m.put("expireAt", fmt(rs.getTimestamp("promo_expire")));
                    return m;
                },
                username, couponId);
        return rows == null || rows.isEmpty() ? Map.of() : rows.get(0);
    }

    private static Map<String, Object> mapPromo(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("code", rs.getString("code"));
        m.put("label", rs.getString("label"));
        m.put("minYuan", rs.getDouble("min_yuan"));
        m.put("offYuan", rs.getDouble("off_yuan"));
        m.put("totalQuota", rs.getInt("total_quota"));
        m.put("claimed", rs.getInt("claimed"));
        m.put("expireAt", fmt(rs.getTimestamp("expire_at")));
        m.put("status", rs.getString("status"));
        try {
            m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        } catch (Exception ignored) {
        }
        return m;
    }

    private static void require() {
        if (!enabled) throw new IllegalStateException("优惠券功能暂不可用");
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static double toD(Object o) {
        if (o instanceof Number n) return n.doubleValue();
        try {
            return Double.parseDouble(String.valueOf(o));
        } catch (Exception e) {
            return 0;
        }
    }

    private static BigDecimal bd(double v) {
        return BigDecimal.valueOf(v).setScale(2, RoundingMode.HALF_UP);
    }

    private static double round2(double v) {
        return bd(v).doubleValue();
    }

    private static String fmt(Timestamp ts) {
        return ts == null ? null : ts.toLocalDateTime().format(FMT);
    }

    private static Timestamp parseTs(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp t) return t;
        String s = String.valueOf(o).trim();
        if (s.isBlank() || "null".equals(s)) return null;
        try {
            if (s.length() == 10) s = s + " 23:59:59";
            return Timestamp.valueOf(s.replace('T', ' ').substring(0, Math.min(19, s.length())));
        } catch (Exception e) {
            return null;
        }
    }
}
