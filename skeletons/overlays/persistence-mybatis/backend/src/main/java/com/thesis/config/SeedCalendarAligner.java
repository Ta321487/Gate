package com.thesis.config;

import com.thesis.mapper.SchemaMapper;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.sql.Date;
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
        SchemaMapper schema = MybatisSupport.mapper(SchemaMapper.class);

        List<String[]> targets = discover(schema);
        if (targets.isEmpty()) return;

        LocalDate today = LocalDate.now();
        LocalDate floor = today.minusDays(ANCHOR_LOOKBACK_DAYS);
        Date floorSql = Date.valueOf(floor);
        LocalDate min = null;
        for (String[] t : targets) {
            LocalDate d = schema.minDate(t[0], t[1], floorSql);
            if (d == null) continue;
            if (min == null || d.isBefore(min)) min = d;
        }
        if (min == null || !min.isBefore(today)) return;

        long days = today.toEpochDay() - min.toEpochDay();
        if (days == 0) return;

        for (String[] t : targets) {
            schema.shiftDates(t[0], t[1], days, floorSql);
        }
    }

    private static List<String[]> discover(SchemaMapper schema) {
        List<String[]> out = new ArrayList<>();
        for (String col : COLS) {
            List<String> tables = schema.listTablesWithColumn(col);
            if (tables == null) continue;
            for (String table : tables) {
                if (table == null || table.isBlank()) continue;
                String t = table.toLowerCase(Locale.ROOT);
                if (t.startsWith("sys_")) continue;
                out.add(new String[]{table, col});
            }
        }
        return out;
    }
}
