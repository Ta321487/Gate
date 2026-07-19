package com.thesis.common;

import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;

/**
 * 密码编解码：由 thesis.password-hash 控制（none / bcrypt / md5 / sha256）。
 * 种子账号可能仍是明文；登录成功后会升级为当前算法。
 */
public final class PasswordHashes {

    private static volatile String mode = "none";
    private static final BCryptPasswordEncoder BCRYPT = new BCryptPasswordEncoder();

    private PasswordHashes() {}

    public static void bind(String m) {
        if (m == null || m.isBlank()) {
            mode = "none";
            return;
        }
        String n = m.trim().toLowerCase(Locale.ROOT);
        if ("sha".equals(n) || "sha-256".equals(n) || "sha_256".equals(n)) n = "sha256";
        if (!n.equals("none") && !n.equals("bcrypt") && !n.equals("md5") && !n.equals("sha256")) {
            n = "none";
        }
        mode = n;
    }

    public static String mode() {
        return mode;
    }

    public static String encode(String raw) {
        if (raw == null) return "";
        return switch (mode) {
            case "bcrypt" -> BCRYPT.encode(raw);
            case "md5" -> digestHex("MD5", raw);
            case "sha256" -> digestHex("SHA-256", raw);
            default -> raw;
        };
    }

    public static boolean matches(String raw, String stored) {
        if (raw == null || stored == null) return false;
        if ("none".equals(mode)) return stored.equals(raw);
        if (isEncoded(stored)) {
            return switch (mode) {
                case "bcrypt" -> BCRYPT.matches(raw, stored);
                case "md5" -> digestHex("MD5", raw).equalsIgnoreCase(stored);
                case "sha256" -> digestHex("SHA-256", raw).equalsIgnoreCase(stored);
                default -> stored.equals(raw);
            };
        }
        // 种子/历史明文
        return stored.equals(raw);
    }

    /** 当前策略非明文，且库内仍是明文 → 登录后应重写 */
    public static boolean needsUpgrade(String stored) {
        if ("none".equals(mode) || stored == null) return false;
        return !isEncoded(stored);
    }

    private static boolean isEncoded(String stored) {
        return switch (mode) {
            case "bcrypt" -> stored.startsWith("$2a$") || stored.startsWith("$2b$") || stored.startsWith("$2y$");
            case "md5" -> stored.matches("(?i)^[a-f0-9]{32}$");
            case "sha256" -> stored.matches("(?i)^[a-f0-9]{64}$");
            default -> false;
        };
    }

    private static String digestHex(String algo, String raw) {
        try {
            MessageDigest md = MessageDigest.getInstance(algo);
            byte[] dig = md.digest(raw.getBytes(StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder(dig.length * 2);
            for (byte b : dig) sb.append(String.format("%02x", b));
            return sb.toString();
        } catch (Exception e) {
            throw new IllegalStateException("摘要算法不可用: " + algo, e);
        }
    }
}
