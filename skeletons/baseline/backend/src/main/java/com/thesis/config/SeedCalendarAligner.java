package com.thesis.config;

import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * 启动时把演示日历整体平移，使最早一天落到「今天」。
 * <p>
 * 只动业务窗口列（start_at / end_at / apply_deadline_at）。
 * 对齐后最早日即为今天，同日多次启动不会反复挪；跨日再平移 1 天。
 * 忽略过旧日期（早于今天减 365 天），避免学生脏数据把整库猛拉。
 * 不向学生 application.yml 暴露开关。
 */
@Component
@Order(1)
public class SeedCalendarAligner implements ApplicationRunner {

    private static final String[] COLS = {"start_at", "end_at", "apply_deadline_at"};
    /** 早于「今天 − 此天数」的日期不参与锚点，防止脏数据拖垮演示窗 */
    private static final int ANCHOR_LOOKBACK_DAYS = 365;

    @Override
    public void run(ApplicationArguments args) {
        JdbcTemplate jdbc = JdbcSupport.jdbc();
        if (jdbc == null) return;

        List<String[]> targets = discover(jdbc);
        if (targets.isEmpty()) return;

        LocalDate today = LocalDate.now();
        LocalDate floor = today.minusDays(ANCHOR_LOOKBACK_DAYS);
        LocalDate min = null;
        for (String[] t : targets) {
            LocalDate d = minDate(jdbc, t[0], t[1], floor);
            if (d == null) continue;
            if (min == null || d.isBefore(min)) min = d;
        }
        if (min == null || !min.isBefore(today)) return;

        long days = today.toEpochDay() - min.toEpochDay();
        if (days == 0) return;

        for (String[] t : targets) {
            jdbc.update(
                    "UPDATE `" + t[0] + "` SET `" + t[1] + "` = DATE_ADD(`" + t[1]
                            + "`, INTERVAL ? DAY) WHERE `" + t[1] + "` IS NOT NULL"
                            + " AND DATE(`" + t[1] + "`) >= ?",
                    days,
                    floor);
        }
    }

    private static List<String[]> discover(JdbcTemplate jdbc) {
        List<String[]> out = new ArrayList<>();
        for (String col : COLS) {
            List<String> tables = jdbc.query(
                    "SELECT TABLE_NAME FROM information_schema.COLUMNS "
                            + "WHERE TABLE_SCHEMA = DATABASE() AND COLUMN_NAME = ? "
                            + "AND DATA_TYPE IN ('date','datetime','timestamp')",
                    (rs, i) -> rs.getString(1),
                    col);
            for (String table : tables) {
                if (table == null || table.isBlank()) continue;
                String t = table.toLowerCase(Locale.ROOT);
                if (t.startsWith("sys_")) continue;
                out.add(new String[]{table, col});
            }
        }
        return out;
    }

    private static LocalDate minDate(JdbcTemplate jdbc, String table, String col, LocalDate floor) {
        try {
            return jdbc.query(
                    "SELECT MIN(DATE(`" + col + "`)) FROM `" + table
                            + "` WHERE `" + col + "` IS NOT NULL AND DATE(`" + col + "`) >= ?",
                    rs -> rs.next() ? rs.getObject(1, LocalDate.class) : null,
                    floor);
        } catch (Exception e) {
            return null;
        }
    }
}
