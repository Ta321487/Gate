package com.thesis.capability;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.sql.ResultSet;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

final class TicketSql {

    static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private TicketSql() {}

    static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    static String now() {
        return LocalDateTime.now().format(FMT);
    }

    static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        String s = String.valueOf(o);
        return (s.isBlank() || "null".equals(s)) ? null : s;
    }

    static long toLong(Object o) {
        if (o == null) return 0L;
        if (o instanceof Number n) return n.longValue();
        return Long.parseLong(String.valueOf(o));
    }

    static double toDouble(Object o) {
        if (o == null) return 0.0;
        if (o instanceof Number n) return n.doubleValue();
        try {
            return Double.parseDouble(String.valueOf(o));
        } catch (Exception e) {
            return 0.0;
        }
    }

    static String str(Object o) {
        return o == null ? "" : String.valueOf(o);
    }

    static String blankTo(String s, String fallback) {
        return s == null || s.isBlank() ? fallback : s;
    }

    static Timestamp safeTs(ResultSet rs, String col) {
        try {
            return rs.getTimestamp(col);
        } catch (Exception e) {
            return null;
        }
    }

    static String safeStr(ResultSet rs, String col) {
        try {
            String v = rs.getString(col);
            return v == null ? "" : v;
        } catch (Exception e) {
            return "";
        }
    }

    static double safeDouble(ResultSet rs, String col) {
        try {
            return rs.getDouble(col);
        } catch (Exception e) {
            return 0.0;
        }
    }

    static long safeLong(ResultSet rs, String col) {
        try {
            long v = rs.getLong(col);
            return rs.wasNull() ? 0L : v;
        } catch (Exception e) {
            return 0L;
        }
    }

    /** @param endOfDay true 时仅日期补 23:59:59，否则补 00:00:00 */
    static LocalDateTime parseDateTimeFlexible(String raw, boolean endOfDay) {
        String s = raw.length() >= 19 ? raw.substring(0, 19) : raw;
        try {
            if (s.length() == 10) {
                return LocalDateTime.parse(s + (endOfDay ? " 23:59:59" : " 00:00:00"), FMT);
            }
            return LocalDateTime.parse(s, FMT);
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("日期格式无效");
        }
    }

    static LocalDateTime parseDateTimeFlexible(String raw) {
        return parseDateTimeFlexible(raw, true);
    }
}
