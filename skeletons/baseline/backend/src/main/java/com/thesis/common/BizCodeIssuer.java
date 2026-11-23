package com.thesis.common;

import java.util.Locale;
import java.util.concurrent.atomic.AtomicLong;

/**
 * 学生包可见业务号签发（工厂编号合同 C 层）。
 * 前缀表语义保留（CERT≠PK≠VF≠VIS）；正文统一单调序，禁止各处散落 nanoTime/Random。
 */
public final class BizCodeIssuer {

    private static final AtomicLong SEQ = new AtomicLong(System.currentTimeMillis());

    private BizCodeIssuer() {}

    /** 单调递增正文（毫秒底座，同毫秒自旋 +1）。 */
    static long nextBody() {
        while (true) {
            long prev = SEQ.get();
            long now = System.currentTimeMillis();
            long next = Math.max(now, prev + 1);
            if (SEQ.compareAndSet(prev, next)) {
                return next;
            }
        }
    }

    public static String prefixed(String prefix, int digits) {
        if (prefix == null) {
            prefix = "";
        }
        if (digits < 1 || digits > 18) {
            throw new IllegalArgumentException("digits out of range");
        }
        long mod = 1L;
        for (int i = 0; i < digits; i++) {
            mod *= 10L;
        }
        long body = Math.floorMod(nextBody(), mod);
        return prefix + String.format(Locale.ROOT, "%0" + digits + "d", body);
    }

    /** 证明开具流水号：CERT + 8 位。 */
    public static String certIssueNo() {
        return prefixed("CERT", 8);
    }

    /** 领取核销码：PK + 10 位。 */
    public static String pickupRedeemCode() {
        return prefixed("PK", 10);
    }

    /** 真伪查询码：VF + 10 位。 */
    public static String verifyCode() {
        return prefixed("VF", 10);
    }

    /** 访客通行码：VIS + 8 位。 */
    public static String passCode() {
        return prefixed("VIS", 8);
    }

    /** 席位/会议签到短码：M + 5 位。 */
    public static String memberCheckinToken() {
        return prefixed("M", 5);
    }

    /** 影院等取票码：由订单行键派生 4 位（稳定、可复述）。 */
    public static String pickupFromOrderId(long orderId) {
        return String.format(Locale.ROOT, "%04d", (int) (Math.floorMod(orderId, 10000L)));
    }

    /** 订单分享口令：8 位大写十六进制。 */
    public static String orderShareToken() {
        return String.format(Locale.ROOT, "%08X", (int) (nextBody() & 0xFFFFFFFFL));
    }

    /** 数字商品许可码。 */
    public static String permitCode(long itemId) {
        return "PERMIT-" + itemId + "-"
                + String.format(Locale.ROOT, "%08X", (int) (nextBody() & 0xFFFFFFFFL));
    }

    /** 数字商品激活码。 */
    public static String activationCode() {
        return "ACT-" + String.format(Locale.ROOT, "%010d", Math.floorMod(nextBody(), 10_000_000_000L));
    }
}
