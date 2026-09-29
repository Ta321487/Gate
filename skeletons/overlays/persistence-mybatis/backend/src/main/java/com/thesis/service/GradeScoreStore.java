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
        return save(username, courseId, termId, score, "");
    }

    /**
     * 录入或更正；UPDATE 分支与删除一样写 grade_score_history（改分留痕）。
     * operator 为操作人账号（管理端登录账号 / CSV 导入同样是登录账号）。
     */
    public static Map<String, Object> save(
            String username, long courseId, long termId, BigDecimal score, String operator) {
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
            long sid = ids.get(0);
            BigDecimal old = mapper().findScore(sid);
            mapper().updateScore(sid, s);
            if (old == null || old.compareTo(s) != 0) {
                mapper().insertHistory(sid, user, courseId, termId, old, s, "update", clip(operator, 64));
            }
        }
        List<Map<String, Object>> rows = mapper().findOne(user, courseId, termId);
        if (rows == null || rows.isEmpty()) throw new IllegalStateException("保存后未能读回成绩");
        return normalize(rows.get(0));
    }

    public static void delete(long id) {
        delete(id, "");
    }

    /** 删除同样留痕：历史快照保留账号/课程/学期，成绩行删后仍可查。 */
    public static void delete(long id, String operator) {
        require();
        Map<String, Object> snap = mapper().findSnapshot(id);
        if (snap == null || snap.isEmpty()) throw new IllegalArgumentException("记录不存在");
        mapper().delete(id);
        recordHistory(
                id,
                snap.get("username") == null ? "" : String.valueOf(snap.get("username")),
                snap.get("courseId") == null ? 0L : ((Number) snap.get("courseId")).longValue(),
                snap.get("termId") == null ? 0L : ((Number) snap.get("termId")).longValue(),
                (BigDecimal) snap.get("score"),
                null,
                "delete",
                operator);
    }

    private static void recordHistory(
            long scoreId,
            String username,
            long courseId,
            long termId,
            BigDecimal oldScore,
            BigDecimal newScore,
            String action,
            String operator) {
        mapper().insertHistory(
                scoreId, clip(username, 64), courseId, termId, oldScore, newScore, action, clip(operator, 64));
    }

    /** 单条成绩的改分记录（成绩删除后仍可按 score_id 查）。 */
    public static List<Map<String, Object>> history(long scoreId) {
        require();
        List<Map<String, Object>> rows = mapper().listHistory(scoreId);
        return rows == null ? List.of() : rows;
    }

    /** 分布与及格率：按课程/学期筛选；及格线固定 60。 */
    public static Map<String, Object> stats(Long courseId, Long termId) {
        require();
        return summarize(mapper().listScores(courseId, termId));
    }

    private static Map<String, Object> summarize(List<BigDecimal> scores) {
        String[] labels = {"60 分以下", "60-69", "70-79", "80-89", "90-100"};
        int[] counts = new int[labels.length];
        int total = 0;
        int pass = 0;
        double sum = 0;
        BigDecimal max = null;
        BigDecimal min = null;
        for (BigDecimal sc : scores == null ? List.<BigDecimal>of() : scores) {
            if (sc == null) continue;
            total++;
            double v = sc.doubleValue();
            sum += v;
            if (v >= 60) pass++;
            int idx = v < 60 ? 0 : v < 70 ? 1 : v < 80 ? 2 : v < 90 ? 3 : 4;
            counts[idx]++;
            if (max == null || sc.compareTo(max) > 0) max = sc;
            if (min == null || sc.compareTo(min) < 0) min = sc;
        }
        List<Map<String, Object>> bands = new java.util.ArrayList<>();
        for (int i = 0; i < labels.length; i++) {
            Map<String, Object> b = new LinkedHashMap<>();
            b.put("label", labels[i]);
            b.put("count", counts[i]);
            b.put("pass", i > 0);
            bands.add(b);
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("total", total);
        out.put("passCount", pass);
        out.put("passRate", total == 0 ? 0.0 : Math.round(pass * 1000.0 / total) / 10.0);
        out.put("avgScore", total == 0 ? null : Math.round(sum / total * 10.0) / 10.0);
        out.put("maxScore", max == null ? null : max.stripTrailingZeros().toPlainString());
        out.put("minScore", min == null ? null : min.stripTrailingZeros().toPlainString());
        out.put("bands", bands);
        return out;
    }

    /** CSV 导入：逐行走既有 save（覆盖即改分并留痕），坏行不影响好行。 */
    public static Map<String, Object> importRows(List<Map<String, Object>> rows, String operator) {
        require();
        int ok = 0;
        int idx = 0;
        List<Map<String, Object>> failed = new java.util.ArrayList<>();
        for (Map<String, Object> r : rows == null ? List.<Map<String, Object>>of() : rows) {
            idx++;
            Map<String, Object> row = r == null ? Map.of() : r;
            Object lineRaw = row.get("line");
            int line = lineRaw == null ? idx : (int) cellLong(lineRaw);
            if (line <= 0) line = idx;
            try {
                save(
                        cellStr(row.get("username")),
                        cellLong(row.get("courseId")),
                        cellLong(row.get("termId")),
                        cellDecimal(row.get("score")),
                        operator);
                ok++;
            } catch (Exception e) {
                Map<String, Object> f = new LinkedHashMap<>();
                f.put("line", line);
                f.put("reason", e.getMessage() == null ? "导入失败" : e.getMessage());
                failed.add(f);
            }
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("ok", ok);
        out.put("failed", failed);
        return out;
    }

    private static String cellStr(Object v) {
        return v == null ? "" : String.valueOf(v).trim();
    }

    private static long cellLong(Object v) {
        String s = cellStr(v);
        if (s.isEmpty()) return 0L;
        try {
            return new BigDecimal(s).longValue();
        } catch (NumberFormatException e) {
            return 0L;
        }
    }

    private static BigDecimal cellDecimal(Object v) {
        String s = cellStr(v);
        if (s.isEmpty()) return null;
        try {
            return new BigDecimal(s);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("分数格式不正确：" + s);
        }
    }
}
