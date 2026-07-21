package com.thesis.config;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

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
}
