package com.thesis.config;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Locale;
import java.util.UUID;

/** 上传目录：读写共用同一绝对路径，避免 file:uploads/ 相对 cwd 找不到文件。 */
public final class UploadStorage {
    private UploadStorage() {}

    public static Path root() {
        Path dir = Paths.get(System.getProperty("user.dir", "."), "uploads")
                .toAbsolutePath()
                .normalize();
        try {
            Files.createDirectories(dir);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        return dir;
    }

    public static Path avatars() {
        Path dir = root().resolve("avatars");
        try {
            Files.createDirectories(dir);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        return dir;
    }

    /** Spring ResourceHandler 用的 file:///.../uploads/ */
    public static String resourceLocation() {
        String loc = root().toUri().toString();
        return loc.endsWith("/") ? loc : loc + "/";
    }

    /**
     * 生成 URL 安全文件名：时间戳 + 短 UUID + 扩展名。
     * 避免中文/空格/井号等原名直接进 /uploads/xxx 导致前端 &lt;img&gt; 404。
     */
    public static String safeStoredName(String originalFilename) {
        String ext = "";
        String raw = originalFilename == null ? "" : originalFilename.trim();
        int dot = raw.lastIndexOf('.');
        if (dot >= 0 && dot < raw.length() - 1) {
            String e = raw.substring(dot + 1).replaceAll("[^A-Za-z0-9]", "");
            if (!e.isBlank() && e.length() <= 8) {
                ext = "." + e.toLowerCase(Locale.ROOT);
            }
        }
        String id = UUID.randomUUID().toString().replace("-", "");
        if (id.length() > 12) id = id.substring(0, 12);
        return System.currentTimeMillis() + "_" + id + ext;
    }
}
