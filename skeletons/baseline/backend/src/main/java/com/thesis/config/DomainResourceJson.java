package com.thesis.config;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.core.io.ClassPathResource;

import java.io.InputStream;
import java.util.Collections;
import java.util.Map;

/** bake 写入的 domain-*.json 读取（列映射等）。 */
public final class DomainResourceJson {

    private static final ObjectMapper JSON = new ObjectMapper();

    private DomainResourceJson() {}

    public static Map<String, Object> loadObjectMap(String classpathName) {
        try {
            ClassPathResource res = new ClassPathResource(classpathName);
            if (!res.exists()) return Collections.emptyMap();
            try (InputStream in = res.getInputStream()) {
                Map<String, Object> root = JSON.readValue(in, new TypeReference<>() {});
                return root == null ? Collections.emptyMap() : root;
            }
        } catch (Exception e) {
            return Collections.emptyMap();
        }
    }

    public static String str(Map<String, Object> root, String key, String fallback) {
        if (root == null || key == null) return fallback;
        Object v = root.get(key);
        if (v == null) return fallback;
        String s = String.valueOf(v).trim();
        return s.isBlank() ? fallback : s;
    }
}
