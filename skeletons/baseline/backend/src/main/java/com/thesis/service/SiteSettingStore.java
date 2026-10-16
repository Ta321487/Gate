package com.thesis.service;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 站点浅设置（sys_site_setting）。
 * 只承载名称/Logo/登录背景/脱敏/维护条；禁止把工厂 AppPolicy 键摊进本表。
 */
public final class SiteSettingStore {

    public static final String KEY_SITE_NAME = "site_name";
    public static final String KEY_LOGO_URL = "logo_url";
    public static final String KEY_LOGIN_BG = "login_bg_url";
    public static final String KEY_MASK_PHONE = "mask_phone";
    public static final String KEY_MAINTENANCE_ON = "maintenance_on";
    public static final String KEY_MAINTENANCE_TEXT = "maintenance_text";

    private static final String[] PUBLIC_KEYS = {
            KEY_SITE_NAME, KEY_LOGO_URL, KEY_LOGIN_BG, KEY_MAINTENANCE_ON, KEY_MAINTENANCE_TEXT
    };

    private static Boolean tableReady;

    private SiteSettingStore() {}

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    public static synchronized void ensureTable() {
        if (Boolean.TRUE.equals(tableReady)) return;
        try {
            db().execute(
                    "CREATE TABLE IF NOT EXISTS sys_site_setting ("
                            + "setting_key VARCHAR(64) NOT NULL,"
                            + "setting_value VARCHAR(1024) NOT NULL DEFAULT '',"
                            + "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,"
                            + "PRIMARY KEY (setting_key)"
                            + ")");
            tableReady = true;
        } catch (Exception e) {
            tableReady = false;
        }
    }

    public static String get(String key) {
        ensureTable();
        if (!Boolean.TRUE.equals(tableReady) || key == null || key.isBlank()) return "";
        try {
            List<String> rows = db().query(
                    "SELECT setting_value FROM sys_site_setting WHERE setting_key=?",
                    (rs, i) -> rs.getString("setting_value"),
                    key.trim());
            if (rows.isEmpty() || rows.get(0) == null) return "";
            return rows.get(0).trim();
        } catch (Exception e) {
            return "";
        }
    }

    public static void put(String key, String value) {
        ensureTable();
        if (!Boolean.TRUE.equals(tableReady)) {
            throw new IllegalStateException("系统设置暂不可用");
        }
        String k = key == null ? "" : key.trim();
        if (k.isBlank() || k.length() > 64) {
            throw new IllegalArgumentException("设置键无效");
        }
        String v = value == null ? "" : value.trim();
        if (v.length() > 1024) {
            throw new IllegalArgumentException("设置值过长");
        }
        db().update(
                "INSERT INTO sys_site_setting (setting_key, setting_value) VALUES (?,?) "
                        + "ON DUPLICATE KEY UPDATE setting_value=VALUES(setting_value)",
                k, v);
    }

    public static boolean maskPhoneEnabled() {
        String v = get(KEY_MASK_PHONE);
        return "1".equals(v) || "true".equalsIgnoreCase(v) || "yes".equalsIgnoreCase(v);
    }

    /** 登录页 / 顶栏可读的公开项（不含脱敏策略）。 */
    public static Map<String, Object> publicMap() {
        Map<String, Object> m = new LinkedHashMap<>();
        for (String k : PUBLIC_KEYS) {
            m.put(toCamel(k), get(k));
        }
        m.put("maintenanceOn", isOn(get(KEY_MAINTENANCE_ON)));
        return m;
    }

    /** 管理端全量（含脱敏开关）。 */
    public static Map<String, Object> adminMap() {
        Map<String, Object> m = publicMap();
        m.put("maskPhone", maskPhoneEnabled());
        return m;
    }

    public static Map<String, Object> saveAdmin(Map<String, Object> body) {
        if (body == null) body = Map.of();
        if (body.containsKey("siteName")) put(KEY_SITE_NAME, str(body.get("siteName")));
        if (body.containsKey("logoUrl")) put(KEY_LOGO_URL, str(body.get("logoUrl")));
        if (body.containsKey("loginBgUrl")) put(KEY_LOGIN_BG, str(body.get("loginBgUrl")));
        if (body.containsKey("maintenanceText")) put(KEY_MAINTENANCE_TEXT, str(body.get("maintenanceText")));
        if (body.containsKey("maintenanceOn")) {
            put(KEY_MAINTENANCE_ON, boolOn(body.get("maintenanceOn")) ? "1" : "0");
        }
        if (body.containsKey("maskPhone")) {
            put(KEY_MASK_PHONE, boolOn(body.get("maskPhone")) ? "1" : "0");
        }
        return adminMap();
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static boolean boolOn(Object o) {
        if (o instanceof Boolean b) return b;
        String s = str(o);
        return "1".equals(s) || "true".equalsIgnoreCase(s) || "yes".equalsIgnoreCase(s);
    }

    private static boolean isOn(String v) {
        return "1".equals(v) || "true".equalsIgnoreCase(v) || "yes".equalsIgnoreCase(v);
    }

    private static String toCamel(String snake) {
        StringBuilder sb = new StringBuilder();
        boolean up = false;
        for (char c : snake.toCharArray()) {
            if (c == '_') {
                up = true;
                continue;
            }
            sb.append(up ? Character.toUpperCase(c) : c);
            up = false;
        }
        return sb.toString();
    }
}
