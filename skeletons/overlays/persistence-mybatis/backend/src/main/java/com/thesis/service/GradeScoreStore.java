package com.thesis.service;

import com.thesis.config.MybatisSupport;
import com.thesis.mapper.GradeScoreMapper;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 教务成绩登记（MyBatis 叠层）：已有 grade_score 表上的录入、课内名次。不开新能力岛。
 */
public class GradeScoreStore {

    private static boolean enabled;
    private static Boolean tableReady;

    private GradeScoreStore() {}

    private static GradeScoreMapper mapper() {
        return MybatisSupport.mapper(GradeScoreMapper.class);
    }

    public static void configure(boolean on) {
        enabled = on;
        tableReady = null;
    }

    public static boolean enabled() {
        return enabled;
    }

    public static boolean ready() {
        if (!enabled) return false;
        if (tableReady != null) return tableReady;
        try {
            Integer n = mapper().countTable();
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

    private static Map<String, Object> normalize(Map<String, Object> row) {
        Map<String, Object> m = new LinkedHashMap<>();
        if (row == null) return m;
        m.put("id", row.get("id"));
        m.put("username", row.get("username"));
        m.put("courseId", row.get("courseId"));
        m.put("courseTitle", row.get("courseTitle"));
        m.put("termId", row.get("termId"));
        m.put("termName", row.get("termName"));
        Object score = row.get("score");
        if (score instanceof BigDecimal bd) {
            m.put("score", bd.stripTrailingZeros().toPlainString());
        } else {
            m.put("score", score == null ? null : String.valueOf(score));
        }
        m.put("rankNo", row.get("rankNo"));
        return m;
    }

    public static Map<String, Object> meta() {
        require();
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("terms", mapper().listTerms());
        out.put("courses", mapper().listCourses());
        return out;
    }

    public static List<Map<String, Object>> listAdmin(Long courseId, Long termId) {
        require();
        return mapper().listAdmin(courseId, termId).stream().map(GradeScoreStore::normalize).toList();
    }

    public static List<Map<String, Object>> listMine(String username) {
        require();
        return mapper().listMine(username).stream().map(GradeScoreStore::normalize).toList();
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
        Integer course = mapper().countCourse(courseId);
        if (course == null || course == 0) throw new IllegalArgumentException("课程不存在");
        Integer term = mapper().countTerm(termId);
        if (term == null || term == 0) throw new IllegalArgumentException("学期不存在");
        List<Long> ids = mapper().findIds(user, courseId, termId);
        if (ids == null || ids.isEmpty()) {
            mapper().insert(user, courseId, termId, s);
        } else {
            mapper().updateScore(ids.get(0), s);
        }
        List<Map<String, Object>> rows = mapper().findOne(user, courseId, termId);
        if (rows == null || rows.isEmpty()) throw new IllegalStateException("保存后未能读回成绩");
        return normalize(rows.get(0));
    }

    public static void delete(long id) {
        require();
        int n = mapper().delete(id);
        if (n == 0) throw new IllegalArgumentException("记录不存在");
    }
}
