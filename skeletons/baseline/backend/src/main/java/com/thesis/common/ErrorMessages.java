package com.thesis.common;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.InputStream;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

/**
 * 业务错误码默认中文。优先读 classpath {@code error-messages.json}，
 * 缺文件时用内置回落，避免空白英文码露脸。
 */
public final class ErrorMessages {
    private static final Map<String, String> FALLBACK;
    private static final Map<String, String> LOADED;

    static {
        Map<String, String> fb = new HashMap<>();
        fb.put("OK", "成功");
        fb.put("BAD_REQUEST", "请求无效");
        fb.put("UNAUTHORIZED", "请先登录");
        fb.put("CAPTCHA_INVALID", "验证码不正确");
        fb.put("ACCOUNT_DISABLED", "账号已停用");
        fb.put("ACCOUNT_LOCKED", "登录失败过多，请稍后再试");
        fb.put("FORBIDDEN", "没有权限");
        fb.put("NOT_FOUND", "未找到相关内容");
        fb.put("INTERNAL", "服务繁忙，请稍后再试");
        FALLBACK = Collections.unmodifiableMap(fb);
        LOADED = loadClasspath();
    }

    private ErrorMessages() {}

    private static Map<String, String> loadClasspath() {
        try (InputStream in = ErrorMessages.class.getResourceAsStream("/error-messages.json")) {
            if (in == null) return Collections.emptyMap();
            Map<String, String> m = new ObjectMapper().readValue(in, new TypeReference<Map<String, String>>() {});
            return m == null ? Collections.emptyMap() : Collections.unmodifiableMap(m);
        } catch (Exception e) {
            return Collections.emptyMap();
        }
    }

    /** 有业务句用业务句；空则回落默认中文。 */
    public static String of(ErrorCode code, String message) {
        if (message != null) {
            String t = message.trim();
            if (!t.isEmpty()) return t;
        }
        if (code == null) return "请求失败";
        String hit = LOADED.get(code.name());
        if (hit != null && !hit.isBlank()) return hit;
        String fb = FALLBACK.get(code.name());
        return fb != null ? fb : "请求失败";
    }
}
