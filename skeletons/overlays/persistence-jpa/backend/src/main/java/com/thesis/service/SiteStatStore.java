package com.thesis.service;

import com.thesis.config.JpaDb;
import com.thesis.config.JpaSupport;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * XD-02 简易站点 PV（sys_site_stat）— JpaDb。
 */
public class SiteStatStore {

    private static final DateTimeFormatter DAY = DateTimeFormatter.ofPattern("yyyy-MM-dd");
    private static Boolean tableReady;

    private static JpaDb db() {
        return JpaSupport.db();
    }

    public static synchronized void ensureTable() {
        if (Boolean.TRUE.equals(tableReady)) return;
        try {
            db().execute(
                    "CREATE TABLE IF NOT EXISTS sys_site_stat ("
                            + "day_key VARCHAR(10) NOT NULL,"
                            + "pv INT NOT NULL DEFAULT 0,"
                            + "PRIMARY KEY (day_key)"
                            + ")");
            tableReady = true;
        } catch (Exception e) {
            tableReady = false;
        }
    }

    /** 门户一次浏览 +1（按自然日）。 */
    public static void bumpPv() {
        ensureTable();
        if (!Boolean.TRUE.equals(tableReady)) return;
        String day = LocalDate.now().format(DAY);
        try {
            int n = db().update(
                    "UPDATE sys_site_stat SET pv = pv + 1 WHERE day_key=?", day);
            if (n == 0) {
                db().update("INSERT INTO sys_site_stat (day_key, pv) VALUES (?, 1)", day);
            }
        } catch (Exception ignored) {
            try {
                db().update(
                        "INSERT INTO sys_site_stat (day_key, pv) VALUES (?, 1) "
                                + "ON DUPLICATE KEY UPDATE pv = pv + 1",
                        day);
            } catch (Exception ignored2) {
            }
        }
    }

    public static Map<String, Object> snapshot() {
        ensureTable();
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("pvToday", 0);
        out.put("pvTotal", 0);
        if (!Boolean.TRUE.equals(tableReady)) return out;
        String day = LocalDate.now().format(DAY);
        try {
            Integer today = db().queryForObject(
                    "SELECT pv FROM sys_site_stat WHERE day_key=?", Integer.class, day);
            out.put("pvToday", today == null ? 0 : today);
        } catch (Exception ignored) {
            out.put("pvToday", 0);
        }
        try {
            Integer total = db().queryForObject(
                    "SELECT COALESCE(SUM(pv),0) FROM sys_site_stat", Integer.class);
            out.put("pvTotal", total == null ? 0 : total);
        } catch (Exception ignored) {
            out.put("pvTotal", 0);
        }
        return out;
    }
}
