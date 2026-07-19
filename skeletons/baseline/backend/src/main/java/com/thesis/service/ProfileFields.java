package com.thesis.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.InputStream;
import java.util.*;
import java.util.regex.Pattern;

/**
 * 从 bake 写入的 domain-profile-fields.json 读取资料字段定义，供注册/资料校验。
 * 格式校验仅手机 / 邮箱；其余业务字段只做必填与白名单。
 */
public final class ProfileFields {

    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final Pattern PHONE = Pattern.compile("^1[3-9]\\d{9}$");
    private static final Pattern EMAIL = Pattern.compile("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$");
    private static volatile List<Map<String, Object>> CACHED;

    private ProfileFields() {}

    public static List<Map<String, Object>> all() {
        List<Map<String, Object>> local = CACHED;
        if (local != null) return local;
        synchronized (ProfileFields.class) {
            if (CACHED != null) return CACHED;
            try (InputStream in = ProfileFields.class.getClassLoader()
                    .getResourceAsStream("domain-profile-fields.json")) {
                if (in == null) {
                    CACHED = List.of();
                } else {
                    CACHED = MAPPER.readValue(in, new TypeReference<List<Map<String, Object>>>() {});
                }
            } catch (Exception e) {
                CACHED = List.of();
            }
            return CACHED;
        }
    }

    /** 校验必填 + 手机/邮箱格式。 */
    public static void requireFilled(String phone, Map<String, String> extras, boolean registerOnly) {
        Map<String, String> ex = extras == null ? Map.of() : extras;
        for (Map<String, Object> f : all()) {
            if (registerOnly && !truthy(f.get("onRegister"))) continue;
            String key = str(f.get("key"));
            if (key.isBlank()) continue;
            String storage = str(f.get("storage"));
            String fmt = str(f.get("format"));
            if (fmt.isBlank()) {
                if ("phone".equals(storage) || "phone".equals(key)) fmt = "phone";
                else if ("email".equals(key)) fmt = "email";
            }
            String val;
            if ("phone".equals(storage) || "phone".equals(key)) {
                val = phone == null ? "" : phone.trim();
            } else {
                val = ex.getOrDefault(key, "");
                if (val != null) val = val.trim();
                else val = "";
            }
            if (truthy(f.get("required")) && val.isBlank()) {
                throw new IllegalArgumentException("请填写" + str(f.get("label")));
            }
            if (!val.isBlank()) {
                checkFormat(fmt, val, str(f.get("label")));
            }
        }
        // schema 未加载时仍兜底校验传入的手机/邮箱
        if (all().isEmpty()) {
            String ph = phone == null ? "" : phone.trim();
            if (!ph.isBlank()) checkFormat("phone", ph, "手机");
            String em = ex.getOrDefault("email", "");
            if (em != null && !em.isBlank()) checkFormat("email", em.trim(), "邮箱");
        }
    }

    private static void checkFormat(String fmt, String val, String label) {
        if ("phone".equals(fmt) && !PHONE.matcher(val).matches()) {
            throw new IllegalArgumentException(label + "格式不正确（11 位手机号）");
        }
        if ("email".equals(fmt) && !EMAIL.matcher(val).matches()) {
            throw new IllegalArgumentException(label + "格式不正确");
        }
    }

    /** 只保留 schema 声明的 json 字段。 */
    public static Map<String, String> filterExtras(Map<String, ?> raw) {
        Map<String, String> out = new LinkedHashMap<>();
        if (raw == null) return out;
        Set<String> allowed = new HashSet<>();
        for (Map<String, Object> f : all()) {
            String storage = str(f.get("storage"));
            if ("phone".equals(storage)) continue;
            String key = str(f.get("key"));
            if (!key.isBlank()) allowed.add(key);
        }
        if (allowed.isEmpty()) {
            for (Map.Entry<String, ?> e : raw.entrySet()) {
                if (e.getValue() != null) out.put(e.getKey(), String.valueOf(e.getValue()).trim());
            }
            return out;
        }
        for (String key : allowed) {
            if (!raw.containsKey(key) || raw.get(key) == null) continue;
            out.put(key, String.valueOf(raw.get(key)).trim());
        }
        return out;
    }

    private static boolean truthy(Object o) {
        if (o instanceof Boolean b) return b;
        return "true".equalsIgnoreCase(String.valueOf(o));
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }
}
