package com.thesis.service;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 教务成绩登记：已有 grade_score 表上的录入、课内名次。不开新能力岛。
 */
public class GradeScoreStore {

    private static boolean enabled;
    private static Boolean tableReady;

    private GradeScoreStore() {}

    public static void configure(boolean on) {
        enabled = on;
        tableReady = null;
    }

    public static boolean enabled() {
        return enabled;
    }

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    public static boolean ready() {
        if (!enabled) return false;
        if (tableReady != null) return tableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='grade_score'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static void require() {
        if (!ready()) throw new IllegalStateException("成绩登记暂不可用");
    }

    private static String clip(String s, int max) {
        if (s == null) return "";
        String t = s.trim();
        return t.length() <= max ? t : t.substring(0, max);
    }

    public static Map<String, Object> meta() {
        require();
        List<Map<String, Object>> terms = db().query(
                "SELECT id, name FROM grade_term ORDER BY id",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("name", rs.getString("name"));
                    return m;
                });
        List<Map<String, Object>> courses = db().query(
                "SELECT id, title FROM course_item ORDER BY id",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("title", rs.getString("title"));
                    return m;
                });
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("terms", terms);
        out.put("courses", courses);
        return out;
    }

    private static final String RANK_SQL =
            "SELECT s.id, s.username, s.course_id, c.title AS course_title, "
                    + "s.term_id, t.name AS term_name, s.score, "
                    + "(SELECT 1 + COUNT(*) FROM grade_score s2 "
                    + " WHERE s2.course_id=s.course_id AND s2.term_id=s.term_id "
                    + " AND s2.score > s.score) AS rank_no "
                    + "FROM grade_score s "
                    + "JOIN course_item c ON c.id=s.course_id "
                    + "JOIN grade_term t ON t.id=s.term_id ";

    private static Map<String, Object> mapRow(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("courseId", rs.getLong("course_id"));
        m.put("courseTitle", rs.getString("course_title"));
        m.put("termId", rs.getLong("term_id"));
        m.put("termName", rs.getString("term_name"));
        BigDecimal score = rs.getBigDecimal("score");
        m.put("score", score == null ? null : score.stripTrailingZeros().toPlainString());
        m.put("rankNo", rs.getInt("rank_no"));
        return m;
    }

    public static List<Map<String, Object>> listAdmin(Long courseId, Long termId) {
        require();
        StringBuilder sql = new StringBuilder(RANK_SQL).append("WHERE 1=1 ");
        List<Object> args = new java.util.ArrayList<>();
        if (courseId != null && courseId > 0) {
            sql.append("AND s.course_id=? ");
            args.add(courseId);
        }
        if (termId != null && termId > 0) {
            sql.append("AND s.term_id=? ");
            args.add(termId);
        }
        sql.append("ORDER BY s.term_id, s.course_id, rank_no, s.username");
        return db().query(sql.toString(), (rs, i) -> mapRow(rs), args.toArray());
    }

    public static List<Map<String, Object>> listMine(String username) {
        require();
        return db().query(
                RANK_SQL + "WHERE s.username=? ORDER BY s.term_id, s.course_id",
                (rs, i) -> mapRow(rs),
                username);
    }

    public static Map<String, Object> save(String username, long courseId, long termId, BigDecimal score) {
        require();
        String user = clip(username, 64);
        if (user.isEmpty()) throw new IllegalArgumentException("请填写学生账号");
        if (score == null) throw new IllegalArgumentException("请填写分数");
        BigDecimal s = score.setScale(2, RoundingMode.HALF_UP);
        if (s.compareTo(BigDecimal.ZERO) < 0 || s.compareTo(new BigDecimal("100")) > 0) {
            throw new IllegalArgumentException("分数须在 0 到 100 之间");
        }
        Integer course = db().queryForObject(
                "SELECT COUNT(*) FROM course_item WHERE id=?", Integer.class, courseId);
        if (course == null || course == 0) throw new IllegalArgumentException("课程不存在");
        Integer term = db().queryForObject(
                "SELECT COUNT(*) FROM grade_term WHERE id=?", Integer.class, termId);
        if (term == null || term == 0) throw new IllegalArgumentException("学期不存在");
        List<Long> ids = db().query(
                "SELECT id FROM grade_score WHERE username=? AND course_id=? AND term_id=?",
                (rs, i) -> rs.getLong("id"),
                user, courseId, termId);
        if (ids.isEmpty()) {
            db().update(
                    "INSERT INTO grade_score (username, course_id, term_id, score) VALUES (?,?,?,?)",
                    user, courseId, termId, s);
        } else {
            db().update("UPDATE grade_score SET score=? WHERE id=?", s, ids.get(0));
        }
        List<Map<String, Object>> rows = db().query(
                RANK_SQL + "WHERE s.username=? AND s.course_id=? AND s.term_id=?",
                (rs, i) -> mapRow(rs),
                user, courseId, termId);
        if (rows.isEmpty()) throw new IllegalStateException("保存后未能读回成绩");
        return rows.get(0);
    }

    public static void delete(long id) {
        require();
        int n = db().update("DELETE FROM grade_score WHERE id=?", id);
        if (n == 0) throw new IllegalArgumentException("记录不存在");
    }
}
