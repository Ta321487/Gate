package com.thesis.service;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.util.LinkedHashMap;
import java.util.Map;

/** 使用说明单页。 */
public final class HelpStore {

    private static Boolean tableReady;

    private HelpStore() {}

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    public static synchronized void ensureTable() {
        if (Boolean.TRUE.equals(tableReady)) return;
        try {
            db().execute(
                    "CREATE TABLE IF NOT EXISTS sys_help_doc ("
                            + "id TINYINT PRIMARY KEY,"
                            + "title VARCHAR(64) NOT NULL,"
                            + "body VARCHAR(4000) NOT NULL,"
                            + "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
                            + ")");
            Integer n = db().queryForObject("SELECT COUNT(*) FROM sys_help_doc WHERE id=1", Integer.class);
            if (n == null || n == 0) {
                db().update(
                        "INSERT INTO sys_help_doc (id, title, body) VALUES (1, ?, ?)",
                        "使用说明",
                        "这里说明本系统的常用操作。管理员可在后台修改本文。");
            }
            tableReady = true;
        } catch (Exception e) {
            tableReady = false;
        }
    }

    public static Map<String, Object> get() {
        ensureTable();
        Map<String, Object> empty = new LinkedHashMap<>();
        empty.put("title", "使用说明");
        empty.put("body", "");
        if (!Boolean.TRUE.equals(tableReady)) return empty;
        try {
            return db().queryForObject(
                    "SELECT title, body FROM sys_help_doc WHERE id=1",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("title", rs.getString("title"));
                        m.put("body", rs.getString("body"));
                        return m;
                    });
        } catch (Exception e) {
            return empty;
        }
    }

    public static Map<String, Object> save(String title, String body) {
        ensureTable();
        String t = title == null ? "" : title.trim();
        String b = body == null ? "" : body.trim();
        if (t.isBlank() || t.length() > 64) throw new IllegalArgumentException("标题无效");
        if (b.isBlank() || b.length() > 4000) throw new IllegalArgumentException("正文无效");
        db().update(
                "INSERT INTO sys_help_doc (id, title, body) VALUES (1, ?, ?) "
                        + "ON DUPLICATE KEY UPDATE title=VALUES(title), body=VALUES(body)",
                t,
                b);
        return get();
    }
}
