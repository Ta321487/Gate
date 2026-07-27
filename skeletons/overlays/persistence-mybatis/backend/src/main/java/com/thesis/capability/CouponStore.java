package com.thesis.capability;

import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.thesis.config.DomainResourceJson;
import com.thesis.config.MybatisSupport;
import com.thesis.mapper.CouponMapper;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 优惠券完整生命周期：券模板领取 → 我的券 → 下单核销 → 过期扫标。
 * 仍兼容下单直接填码（未领取的模板码）。
 */
public final class CouponStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private static boolean enabled;

    private CouponStore() {}

    private static CouponMapper mapper() {
        return MybatisSupport.mapper(CouponMapper.class);
    }

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

    private static void ensureTables() {
        try {
            mapper().ensurePromoTable();
            mapper().ensureMineTable();
        } catch (Exception ignored) {
        }
    }

    private static void seedFromResourceIfEmpty() {
        try {
            if (mapper().countPromo() > 0) return;
        } catch (Exception e) {
            return;
        }
        List<Map<String, Object>> seeds = loadSeedItems();
        Timestamp expire = Timestamp.valueOf(LocalDateTime.now().plusDays(90));
        for (Map<String, Object> c : seeds) {
            try {
                mapper().insertSeed(
                        String.valueOf(c.getOrDefault("code", "")).trim().toUpperCase(Locale.ROOT),
                        String.valueOf(c.getOrDefault("label", "")),
                        bd(toD(c.get("minYuan"))),
                        bd(toD(c.get("offYuan"))),
                        expire);
            } catch (Exception ignored) {
            }
        }
    }

    private static List<Map<String, Object>> loadSeedItems() {
        Map<String, Object> root = DomainResourceJson.loadObjectMap("domain-loyalty.json");
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
        return List.of(
                Map.of("code", "SAVE10", "label", "满50减10", "minYuan", 50, "offYuan", 10),
                Map.of("code", "WELCOME5", "label", "满30减5", "minYuan", 30, "offYuan", 5));
    }

    public static List<Map<String, Object>> listActiveTemplates() {
        require();
        expireSweep();
        List<Map<String, Object>> raw = mapper().selectActivePromos();
        List<Map<String, Object>> out = new ArrayList<>();
        if (raw != null) {
            for (Map<String, Object> r : raw) out.add(shapePromo(r));
        }
        return out;
    }

    public static Map<String, Object> pageAdmin(int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        PageHelper.startPage(page, size);
        List<Map<String, Object>> raw = mapper().selectAllPromosDesc();
        PageInfo<Map<String, Object>> pi = new PageInfo<>(raw == null ? List.of() : raw);
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> r : pi.getList()) list.add(shapePromo(r));
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", pi.getTotal());
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
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("code", code);
        row.put("label", str(body.get("label")));
        row.put("minYuan", bd(min));
        row.put("offYuan", bd(off));
        row.put("totalQuota", Math.max(0, quota));
        row.put("expireAt", exp);
        mapper().insertPromo(row);
        long id = row.get("id") == null ? 0L : ((Number) row.get("id")).longValue();
        return getPromo(id);
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
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", id);
        row.put("label", label);
        row.put("minYuan", bd(min));
        row.put("offYuan", bd(off));
        row.put("totalQuota", Math.max(0, quota));
        row.put("expireAt", exp);
        row.put("status", status);
        mapper().updatePromo(row);
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
        if (mapper().countMine(username, couponId) > 0) throw new IllegalStateException("您已领取过该券");
        mapper().insertMine(username, couponId, Timestamp.valueOf(LocalDateTime.now()));
        mapper().bumpClaimed(couponId);
        return getMineRow(username, couponId);
    }

    public static Map<String, Object> pageMine(String username, String status, int page, int size) {
        require();
        expireSweep();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        String st = status == null || status.isBlank() ? null : status.trim();
        PageHelper.startPage(page, size);
        List<Map<String, Object>> raw = mapper().selectMineJoined(username, st);
        PageInfo<Map<String, Object>> pi = new PageInfo<>(raw == null ? List.of() : raw);
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> r : pi.getList()) list.add(shapeMine(r));
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", pi.getTotal());
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
        if (username != null && !username.isBlank()) {
            List<Map<String, Object>> mine = mapper().selectUnusedMineByCode(username, want);
            if (mine != null && !mine.isEmpty()) {
                Map<String, Object> hit = shapePromo(mine.get(0));
                Object ucid = mine.get(0).get("userCouponId");
                if (ucid == null) ucid = mine.get(0).get("user_coupon_id");
                if (ucid != null) hit.put("userCouponId", ucid);
                return applyPromoHit(out, hit, amountYuan);
            }
        }
        List<Map<String, Object>> promos = mapper().selectActivePromoByCode(want);
        if (promos != null && !promos.isEmpty()) {
            return applyPromoHit(out, shapePromo(promos.get(0)), amountYuan);
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
            Long id = mapper().selectUnusedMineIdByCode(username, want);
            if (id == null) return;
            mapper().markMineUsed(id, Timestamp.valueOf(LocalDateTime.now()), orderId);
        } catch (Exception ignored) {
        }
    }

    /** 取消/售后通过：按订单回退已核销券（仍未过期则回到 unused） */
    public static void releaseByOrder(long orderId) {
        if (!enabled || orderId <= 0) return;
        try {
            mapper().releaseByOrder(orderId);
        } catch (Exception ignored) {
        }
    }

    /** 定时：未用且模板已过期 → expired */
    public static int expireSweep() {
        if (!enabled) return 0;
        try {
            return mapper().expireSweep();
        } catch (Exception e) {
            return 0;
        }
    }

    private static Map<String, Object> getPromo(long id) {
        return shapePromo(mapper().selectPromoById(id));
    }

    private static Map<String, Object> getMineRow(String username, long couponId) {
        Map<String, Object> row = mapper().selectMineJoinedOne(username, couponId);
        return row == null ? Map.of() : shapeMine(row);
    }

    private static Map<String, Object> shapePromo(Map<String, Object> raw) {
        if (raw == null) return null;
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", num(raw.get("id")));
        m.put("code", str(raw.get("code")));
        m.put("label", str(raw.get("label")));
        m.put("minYuan", toD(first(raw, "minYuan", "min_yuan")));
        m.put("offYuan", toD(first(raw, "offYuan", "off_yuan")));
        m.put("totalQuota", (int) toD(first(raw, "totalQuota", "total_quota")));
        m.put("claimed", (int) toD(first(raw, "claimed", "claimed")));
        m.put("expireAt", fmt(first(raw, "expireAt", "expire_at")));
        m.put("status", str(raw.get("status")));
        Object created = first(raw, "createdAt", "created_at");
        if (created != null) m.put("createdAt", fmt(created));
        return m;
    }

    private static Map<String, Object> shapeMine(Map<String, Object> raw) {
        if (raw == null) return null;
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", num(raw.get("id")));
        m.put("couponId", num(first(raw, "couponId", "coupon_id")));
        m.put("status", str(raw.get("status")));
        m.put("claimedAt", fmt(first(raw, "claimedAt", "claimed_at")));
        m.put("usedAt", fmt(first(raw, "usedAt", "used_at")));
        Object oid = first(raw, "orderId", "order_id");
        if (oid != null) m.put("orderId", num(oid));
        m.put("code", str(raw.get("code")));
        m.put("label", str(raw.get("label")));
        m.put("minYuan", toD(first(raw, "minYuan", "min_yuan")));
        m.put("offYuan", toD(first(raw, "offYuan", "off_yuan")));
        m.put("expireAt", fmt(first(raw, "expireAt", "promoExpire", "promo_expire")));
        return m;
    }

    private static Object first(Map<String, Object> raw, String... keys) {
        for (String k : keys) {
            if (raw.containsKey(k) && raw.get(k) != null) return raw.get(k);
        }
        return null;
    }

    private static long num(Object o) {
        if (o instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(String.valueOf(o));
        } catch (Exception e) {
            return 0L;
        }
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

    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        String s = String.valueOf(o).trim();
        return s.isBlank() || "null".equals(s) ? null : s;
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
