package com.thesis.common;

/** 敏感字段浅脱敏（手机号/证件）；≠ 公安网或完整脱敏中台。 */
public final class MaskUtil {

    private MaskUtil() {}

    /** 大陆 11 位手机：中间四位 *；其它长度保留首尾各 1～2 位。 */
    public static String maskPhone(String phone) {
        if (phone == null) return "";
        String s = phone.trim();
        if (s.isEmpty()) return "";
        if (s.length() == 11 && s.chars().allMatch(Character::isDigit)) {
            return s.substring(0, 3) + "****" + s.substring(7);
        }
        if (s.length() <= 4) return "****";
        int keep = Math.min(2, s.length() / 3);
        return s.substring(0, keep) + "****" + s.substring(s.length() - keep);
    }

    /** 证件号：保留前 4 后 4。 */
    public static String maskIdNo(String idNo) {
        if (idNo == null) return "";
        String s = idNo.trim();
        if (s.isEmpty()) return "";
        if (s.length() <= 8) return "****";
        return s.substring(0, 4) + "****" + s.substring(s.length() - 4);
    }
}
