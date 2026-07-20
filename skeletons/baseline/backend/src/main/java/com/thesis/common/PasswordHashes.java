package com.thesis.common;

import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;

/**
 * 密码编解码：由 thesis.password-hash 控制（none / bcrypt / md5 / sha256）。
 * <p>
 * 校验按<strong>库内实际形态</strong>识别（明文 / bcrypt / md5 / sha256），不依赖当前策略；
 * 换算法或改回 none 后，旧哈希仍可登录，成功后升级为当前策略。
 * 种子账号常为明文，同理。
 */
public final class PasswordHashes {

    private static volatile String mode = "none";
    private static final BCryptPasswordEncoder BCRYPT = new BCryptPasswordEncoder();

    private enum StoredKind {
        PLAIN,
        BCRYPT,
        MD5,
        SHA256
    }

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
        return switch (detect(stored)) {
            case BCRYPT -> BCRYPT.matches(raw, stored);
            case MD5 -> digestHex("MD5", raw).equalsIgnoreCase(stored);
            case SHA256 -> digestHex("SHA-256", raw).equalsIgnoreCase(stored);
            case PLAIN -> stored.equals(raw);
        };
    }

    /** 库内形态与当前策略不一致 → 登录后应重写（含哈希→明文、明文→哈希、哈希互转） */
    public static boolean needsUpgrade(String stored) {
        if (stored == null) return false;
        return detect(stored) != kindForMode(mode);
    }

    private static StoredKind kindForMode(String m) {
        return switch (m == null ? "none" : m) {
            case "bcrypt" -> StoredKind.BCRYPT;
            case "md5" -> StoredKind.MD5;
            case "sha256" -> StoredKind.SHA256;
            default -> StoredKind.PLAIN;
        };
    }

    /** 按存储串形态识别，与当前 password-hash 无关 */
    private static StoredKind detect(String stored) {
        if (stored.startsWith("$2a$") || stored.startsWith("$2b$") || stored.startsWith("$2y$")) {
            return StoredKind.BCRYPT;
        }
        if (stored.matches("(?i)^[a-f0-9]{64}$")) {
            return StoredKind.SHA256;
        }
        if (stored.matches("(?i)^[a-f0-9]{32}$")) {
            return StoredKind.MD5;
        }
        return StoredKind.PLAIN;
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
