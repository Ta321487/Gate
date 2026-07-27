package com.thesis.capability;

import com.github.pagehelper.PageHelper;
import com.thesis.config.DomainResourceJson;
import com.thesis.config.MybatisSupport;
import com.thesis.mapper.LoyaltyMapper;
import com.thesis.mapper.SchemaMapper;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;

/**
 * 忠诚度：账户余额 / 积分 / 满减 / 会员成长（能力开关；非真支付）。
 * 优惠券开关仅作标志；算价与生命周期一律走 {@link CouponStore}。
 */
public final class LoyaltyStore {

    private static boolean walletEnabled;
    private static boolean pointsEnabled;
    private static boolean spendDiscountEnabled;
    private static boolean memberTierEnabled;
    private static boolean couponEnabled;
    private static int pointsEarnPerYuan = 1;
    private static double spendThresholdYuan = 100;
    private static double spendOffYuan = 10;
    private static List<Map<String, Object>> memberTiers = List.of();
    private static boolean schemaReady;

    private LoyaltyStore() {}

    private static LoyaltyMapper mapper() {
        return MybatisSupport.mapper(LoyaltyMapper.class);
    }

    private static SchemaMapper schema() {
        return MybatisSupport.mapper(SchemaMapper.class);
    }

    public static void configure(
            boolean wallet,
            boolean points,
            boolean spendDiscount,
            boolean memberTier,
            int earnPerYuan,
            double thresholdYuan,
            double offYuan) {
        configure(wallet, points, spendDiscount, memberTier, false, earnPerYuan, thresholdYuan, offYuan);
    }

    public static void configure(
            boolean wallet,
            boolean points,
            boolean spendDiscount,
            boolean memberTier,
            boolean coupon,
            int earnPerYuan,
            double thresholdYuan,
            double offYuan) {
        walletEnabled = wallet;
        pointsEnabled = points;
        spendDiscountEnabled = spendDiscount;
        memberTierEnabled = memberTier;
        couponEnabled = coupon;
        pointsEarnPerYuan = Math.max(0, earnPerYuan);
        spendThresholdYuan = Math.max(0, thresholdYuan);
        spendOffYuan = Math.max(0, offYuan);
        if (anyEnabled()) {
            ensureSchema();
            loadTiersFromResource();
        }
    }

    public static boolean anyEnabled() {
        return walletEnabled || pointsEnabled || spendDiscountEnabled || memberTierEnabled || couponEnabled;
    }

    public static boolean isCouponEnabled() {
        return couponEnabled;
    }

    public static boolean isWalletEnabled() {
        return walletEnabled;
    }

    public static boolean isPointsEnabled() {
        return pointsEnabled;
    }

    private static void loadTiersFromResource() {
        Map<String, Object> root = DomainResourceJson.loadObjectMap("domain-loyalty.json");
        if (!root.isEmpty()) {
            Object mt = root.get("memberTiers");
            if (mt instanceof Map<?, ?> map) {
                Object tiers = map.get("tiers");
                if (tiers instanceof List<?> list) {
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
                    if (!out.isEmpty()) {
                        memberTiers = out;
                        return;
                    }
                }
            }
        }
        memberTiers = defaultTiers();
    }

    /** 校验券码；返回抵扣金额（0 表示不适用）。统一委托 CouponStore。 */
    public static Map<String, Object> matchCoupon(String code, double amountYuan) {
        return matchCoupon(null, code, amountYuan);
    }

    public static Map<String, Object> matchCoupon(String username, String code, double amountYuan) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("ok", false);
        out.put("offYuan", 0);
        out.put("code", code == null ? "" : code.trim());
        if (!couponEnabled || code == null || code.isBlank()) return out;
        if (!CouponStore.enabled()) {
            out.put("message", "券码无效");
            return out;
        }
        return CouponStore.matchForCheckout(username, code, amountYuan);
    }

    private static double toD(Object o) {
        if (o instanceof Number n) return n.doubleValue();
        try {
            return Double.parseDouble(String.valueOf(o));
        } catch (Exception e) {
            return 0;
        }
    }

    private static List<Map<String, Object>> defaultTiers() {
        return List.of(
                Map.of("id", "normal", "label", "普通", "minSpend", 0, "discountRate", 1),
                Map.of("id", "silver", "label", "银卡", "minSpend", 200, "discountRate", 0.95),
                Map.of("id", "gold", "label", "金卡", "minSpend", 500, "discountRate", 0.9));
    }

    public static synchronized void ensureSchema() {
        if (schemaReady) return;
        ensureUserCol("balance_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0");
        ensureUserCol("points", "INT NOT NULL DEFAULT 0");
        ensureUserCol("member_tier", "VARCHAR(32) DEFAULT ''");
        ensureUserCol("spend_total_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0");
        try {
            mapper().ensureLedgerTable();
        } catch (Exception ignored) {
        }
        schemaReady = true;
    }

    private static void ensureUserCol(String col, String ddl) {
        try {
            Integer n = schema().countColumn("sys_user", col);
            if (n != null && n > 0) return;
            schema().executeDdl("ALTER TABLE sys_user ADD COLUMN " + col + " " + ddl);
        } catch (Exception ignored) {
        }
    }

    public static Map<String, Object> getAccount(String username) {
        if (anyEnabled()) ensureSchema();
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("walletEnabled", walletEnabled);
        m.put("pointsEnabled", pointsEnabled);
        m.put("spendDiscountEnabled", spendDiscountEnabled);
        m.put("memberTierEnabled", memberTierEnabled);
        m.put("couponEnabled", couponEnabled);
        if (couponEnabled) {
            try {
                m.put("coupons", CouponStore.enabled() ? CouponStore.listActiveTemplates() : List.of());
            } catch (Exception e) {
                m.put("coupons", List.of());
            }
        }
        m.put("balanceYuan", 0.0);
        m.put("points", 0);
        m.put("memberTier", "");
        m.put("memberTierLabel", "");
        m.put("spendTotalYuan", 0.0);
        if (username == null || username.isBlank()) return m;
        try {
            Map<String, Object> row = mapper().selectAccount(username);
            if (row != null) {
                m.put("balanceYuan", toD(first(row, "balanceYuan", "balance_yuan")));
                m.put("points", (int) toD(first(row, "points", "points")));
                String tier = nullToEmpty(String.valueOf(first(row, "memberTier", "member_tier")));
                if ("null".equals(tier)) tier = "";
                m.put("memberTier", tier);
                m.put("spendTotalYuan", toD(first(row, "spendTotalYuan", "spend_total_yuan")));
                m.put("memberTierLabel", tierLabel(tier));
            }
        } catch (Exception ignored) {
        }
        return m;
    }

    public static List<Map<String, Object>> listLedger(String username, int limit) {
        if (!anyEnabled()) return List.of();
        ensureSchema();
        int lim = Math.min(100, Math.max(1, limit));
        try {
            PageHelper.startPage(1, lim, false);
            List<Map<String, Object>> raw = mapper().selectLedger(username);
            List<Map<String, Object>> out = new ArrayList<>();
            if (raw != null) {
                for (Map<String, Object> r : raw) {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("id", r.get("id"));
                    row.put("kind", r.get("kind"));
                    row.put("delta", toD(r.get("delta")));
                    row.put("balanceAfter", toD(first(r, "balanceAfter", "balance_after")));
                    row.put("reason", r.get("reason"));
                    row.put("refType", first(r, "refType", "ref_type"));
                    row.put("refId", first(r, "refId", "ref_id"));
                    row.put("operator", r.get("operator"));
                    row.put("createdAt", String.valueOf(first(r, "createdAt", "created_at")));
                    out.add(row);
                }
            }
            return out;
        } catch (Exception e) {
            return List.of();
        }
    }

    /** 管理端充值：仅 wallet */
    public static Map<String, Object> adminRecharge(String username, double amount, String operator) {
        if (!walletEnabled) throw new IllegalStateException("未开启账户余额");
        if (amount <= 0) throw new IllegalArgumentException("充值金额须大于 0");
        ensureSchema();
        return adjustWallet(username, amount, "recharge", "admin", null, operator == null ? "" : operator);
    }

    public static Map<String, Object> previewPrice(double subtotal, String username) {
        return previewPrice(subtotal, username, null);
    }

    public static Map<String, Object> previewPrice(double subtotal, String username, String couponCode) {
        Map<String, Object> out = new LinkedHashMap<>();
        double sub = round2(Math.max(0, subtotal));
        out.put("subtotalYuan", sub);
        double afterTier = sub;
        double tierRate = 1.0;
        String tierId = "";
        if (memberTierEnabled && username != null && !username.isBlank()) {
            Map<String, Object> acc = getAccount(username);
            tierId = String.valueOf(acc.getOrDefault("memberTier", ""));
            tierRate = tierDiscountRate(tierId);
            afterTier = round2(sub * tierRate);
        }
        out.put("memberTier", tierId);
        out.put("tierDiscountRate", tierRate);
        out.put("afterTierYuan", afterTier);

        double discount = 0;
        if (spendDiscountEnabled && spendOffYuan > 0 && afterTier + 1e-9 >= spendThresholdYuan) {
            discount = Math.min(spendOffYuan, afterTier);
        }
        Map<String, Object> couponHit = matchCoupon(username, couponCode, afterTier);
        double couponOff = Boolean.TRUE.equals(couponHit.get("ok"))
                ? ((Number) couponHit.get("offYuan")).doubleValue()
                : 0;
        out.put("couponOffYuan", round2(couponOff));
        if (couponOff > discount) {
            discount = couponOff;
            out.put("couponCode", couponHit.get("code"));
            out.put("couponLabel", couponHit.get("label"));
        } else if (couponCode != null && !couponCode.isBlank() && !Boolean.TRUE.equals(couponHit.get("ok"))) {
            out.put("couponMessage", couponHit.get("message"));
        } else if (couponOff > 0 && couponOff <= discount) {
            out.put("couponMessage", "满减已更优，未使用该券");
        }
        out.put("couponEnabled", couponEnabled);
        out.put("discountYuan", round2(discount));
        double payable = round2(Math.max(0, afterTier - discount));
        out.put("payableYuan", payable);

        Map<String, Object> acc = getAccount(username == null ? "" : username);
        out.put("balanceYuan", acc.get("balanceYuan"));
        out.put("points", acc.get("points"));
        out.put("walletEnabled", walletEnabled);
        boolean enough = !walletEnabled || ((Number) acc.get("balanceYuan")).doubleValue() + 1e-9 >= payable;
        out.put("balanceEnough", enough);
        if (walletEnabled && !enough) {
            out.put(
                    "message",
                    "账户余额不足，请联系管理员充值（当前 ¥"
                            + round2(((Number) acc.get("balanceYuan")).doubleValue())
                            + "，需 ¥"
                            + payable
                            + "）");
        }
        return out;
    }

    /** 下单扣余额；返回实付与折扣快照 */
    public static Map<String, Object> settleOnPlace(String username, double subtotal, long orderId) {
        return settleOnPlace(username, subtotal, orderId, null);
    }

    public static Map<String, Object> settleOnPlace(
            String username, double subtotal, long orderId, String couponCode) {
        Map<String, Object> preview = previewPrice(subtotal, username, couponCode);
        double payable = ((Number) preview.get("payableYuan")).doubleValue();
        double discount = ((Number) preview.get("discountYuan")).doubleValue();
        if (walletEnabled) {
            double bal = ((Number) getAccount(username).get("balanceYuan")).doubleValue();
            if (bal + 1e-9 < payable) {
                throw new IllegalStateException("账户余额不足，请联系管理员充值（当前 ¥" + round2(bal) + "，需 ¥" + payable + "）");
            }
            if (payable > 0) {
                adjustWallet(username, -payable, "order_pay", "order", orderId, username);
            }
        }
        Map<String, Object> snap = new LinkedHashMap<>(preview);
        snap.put("payBalanceYuan", walletEnabled ? payable : 0.0);
        snap.put("discountYuan", discount);
        return snap;
    }

    /** 订单完成后：赠积分、累计消费、升级 */
    public static void onOrderCompleted(String username, long orderId, double payYuan) {
        if (!pointsEnabled && !memberTierEnabled) return;
        ensureSchema();
        double pay = round2(Math.max(0, payYuan));
        int earned = 0;
        if (pointsEnabled && pointsEarnPerYuan > 0 && pay > 0) {
            earned = (int) Math.floor(pay) * pointsEarnPerYuan;
            if (earned > 0) {
                creditPoints(username, earned, "order_earn", "order", orderId);
            }
        }
        if (memberTierEnabled && pay > 0) {
            mapper().addSpend(username, BigDecimal.valueOf(pay).setScale(2, RoundingMode.HALF_UP));
            Map<String, Object> acc = getAccount(username);
            double spend = ((Number) acc.get("spendTotalYuan")).doubleValue();
            String next = resolveTierId(spend);
            mapper().updateTier(username, next);
        }
        if (earned > 0) {
            try {
                mapper().updateOrderPoints(orderId, earned);
            } catch (Exception ignored) {
            }
        }
    }

    /** 取消已扣余额订单时退回 */
    public static void refundOrderPay(String username, long orderId, double payYuan) {
        if (!walletEnabled || payYuan <= 0) return;
        ensureSchema();
        adjustWallet(username, payYuan, "order_refund", "order", orderId, "system");
    }

    /** 已完成后售后/冲正：扣回赠分与累计消费（不低于 0） */
    public static void clawbackOrderCompleted(String username, long orderId, int pointsEarned, double payYuan) {
        if (!pointsEnabled && !memberTierEnabled) return;
        if (username == null || username.isBlank()) return;
        ensureSchema();
        if (pointsEnabled && pointsEarned > 0) {
            debitPoints(username, pointsEarned, "order_clawback", "order", orderId);
            try {
                mapper().updateOrderPoints(orderId, 0);
            } catch (Exception ignored) {
            }
        }
        double pay = round2(Math.max(0, payYuan));
        if (memberTierEnabled && pay > 0) {
            mapper().subtractSpend(username, BigDecimal.valueOf(pay).setScale(2, RoundingMode.HALF_UP));
            Map<String, Object> acc = getAccount(username);
            double spend = ((Number) acc.get("spendTotalYuan")).doubleValue();
            String next = resolveTierId(spend);
            mapper().updateTier(username, next);
        }
    }

    private static Map<String, Object> adjustWallet(
            String username, double delta, String reason, String refType, Long refId, String operator) {
        ensureSchema();
        Map<String, Object> acc = getAccount(username);
        double before = ((Number) acc.get("balanceYuan")).doubleValue();
        double after = round2(before + delta);
        if (after < -1e-9) throw new IllegalStateException("余额不足");
        mapper().updateBalance(username, BigDecimal.valueOf(after).setScale(2, RoundingMode.HALF_UP));
        appendLedger(username, "wallet", delta, after, reason, refType, refId, operator);
        return getAccount(username);
    }

    private static void creditPoints(String username, int delta, String reason, String refType, Long refId) {
        if (delta <= 0) return;
        ensureSchema();
        Map<String, Object> acc = getAccount(username);
        int before = ((Number) acc.get("points")).intValue();
        int after = before + delta;
        mapper().updatePoints(username, after);
        appendLedger(username, "points", delta, after, reason, refType, refId, "system");
    }

    private static void debitPoints(String username, int delta, String reason, String refType, Long refId) {
        if (delta <= 0) return;
        ensureSchema();
        Map<String, Object> acc = getAccount(username);
        int before = ((Number) acc.get("points")).intValue();
        int after = Math.max(0, before - delta);
        mapper().updatePoints(username, after);
        appendLedger(username, "points", after - before, after, reason, refType, refId, "system");
    }

    private static void appendLedger(
            String username,
            String kind,
            double delta,
            double after,
            String reason,
            String refType,
            Long refId,
            String operator) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("username", username);
        row.put("kind", kind);
        row.put("delta", BigDecimal.valueOf(delta).setScale(2, RoundingMode.HALF_UP));
        row.put("balanceAfter", BigDecimal.valueOf(after).setScale(2, RoundingMode.HALF_UP));
        row.put("reason", reason == null ? "" : reason);
        row.put("refType", refType == null ? "" : refType);
        row.put("refId", refId);
        row.put("operator", operator == null ? "" : operator);
        mapper().insertLedger(row);
    }

    private static Object first(Map<String, Object> raw, String... keys) {
        for (String k : keys) {
            if (raw.containsKey(k) && raw.get(k) != null) return raw.get(k);
        }
        return null;
    }

    private static double tierDiscountRate(String tierId) {
        String id = tierId == null ? "" : tierId.trim();
        for (Map<String, Object> t : memberTiers) {
            if (id.equals(String.valueOf(t.get("id")))) {
                Object r = t.get("discountRate");
                if (r instanceof Number n) return n.doubleValue();
                try {
                    return Double.parseDouble(String.valueOf(r));
                } catch (Exception e) {
                    return 1.0;
                }
            }
        }
        return 1.0;
    }

    private static String resolveTierId(double spend) {
        String best = "normal";
        double bestMin = -1;
        for (Map<String, Object> t : memberTiers) {
            double min = toDouble(t.get("minSpend"));
            if (spend + 1e-9 >= min && min >= bestMin) {
                bestMin = min;
                best = String.valueOf(t.getOrDefault("id", "normal"));
            }
        }
        return best;
    }

    private static String tierLabel(String id) {
        for (Map<String, Object> t : memberTiers) {
            if (String.valueOf(t.get("id")).equals(id)) {
                return String.valueOf(t.getOrDefault("label", id));
            }
        }
        return id == null || id.isBlank() ? "—" : id;
    }

    private static String nullToEmpty(String s) {
        return s == null ? "" : s;
    }

    private static double toDouble(Object o) {
        if (o instanceof Number n) return n.doubleValue();
        try {
            return Double.parseDouble(String.valueOf(o));
        } catch (Exception e) {
            return 0;
        }
    }

    private static double round2(double v) {
        return Math.round(v * 100.0) / 100.0;
    }
}
