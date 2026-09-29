package com.thesis.service;

import com.thesis.config.JpaDb;
import com.thesis.config.JpaSupport;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 教务成绩登记（JPA 叠层）：已有 grade_score 表上的录入、课内名次。不开新能力岛。
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

    private static JpaDb db() {
        return JpaSupport.db();
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
        Integer course = db().queryForObject(
                "SELECT COUNT(*) FROM course_item WHERE id=?", Integer.class, courseId);
        if (course == null || course == 0) throw new IllegalArgumentException("课程不存在");
        Integer term = db().queryForObject(
                "SELECT COUNT(*) FROM grade_term WHERE id=?", Integer.class, termId);
        if (term == null || term == 0) throw new IllegalArgumentException("学期不存在");
        List<Map<String, Object>> cur = db().query(
                "SELECT id, score FROM grade_score WHERE username=? AND course_id=? AND term_id=?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("score", rs.getBigDecimal("score"));
                    return m;
                },
                user, courseId, termId);
        if (cur.isEmpty()) {
            db().update(
                    "INSERT INTO grade_score (username, course_id, term_id, score) VALUES (?,?,?,?)",
                    user, courseId, termId, s);
        } else {
            long sid = ((Number) cur.get(0).get("id")).longValue();
            BigDecimal old = (BigDecimal) cur.get(0).get("score");
            db().update("UPDATE grade_score SET score=? WHERE id=?", s, sid);
            if (old == null || old.compareTo(s) != 0) {
                recordHistory(sid, user, courseId, termId, old, s, "update", operator);
            }
        }
        List<Map<String, Object>> rows = db().query(
                RANK_SQL + "WHERE s.username=? AND s.course_id=? AND s.term_id=?",
                (rs, i) -> mapRow(rs),
                user, courseId, termId);
        if (rows.isEmpty()) throw new IllegalStateException("保存后未能读回成绩");
        return rows.get(0);
    }

    public static void delete(long id) {
        delete(id, "");
    }

    /** 删除同样留痕：历史快照保留账号/课程/学期，成绩行删后仍可查。 */
    public static void delete(long id, String operator) {
        require();
        List<Map<String, Object>> snap = snapshot(id);
        if (snap.isEmpty()) throw new IllegalArgumentException("记录不存在");
        db().update("DELETE FROM grade_score WHERE id=?", id);
        Map<String, Object> r = snap.get(0);
        recordHistory(
                id,
                String.valueOf(r.get("username") == null ? "" : r.get("username")),
                r.get("courseId") == null ? 0L : ((Number) r.get("courseId")).longValue(),
                r.get("termId") == null ? 0L : ((Number) r.get("termId")).longValue(),
                (BigDecimal) r.get("score"),
                null,
                "delete",
                operator);
    }

    private static List<Map<String, Object>> snapshot(long id) {
        return db().query(
                "SELECT id, username, course_id, term_id, score FROM grade_score WHERE id=?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("username", rs.getString("username"));
                    m.put("courseId", rs.getLong("course_id"));
                    m.put("termId", rs.getLong("term_id"));
                    m.put("score", rs.getBigDecimal("score"));
                    return m;
                },
                id);
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
        db().update(
                "INSERT INTO grade_score_history "
                        + "(score_id, username, course_id, term_id, old_score, new_score, action, operator) "
                        + "VALUES (?,?,?,?,?,?,?,?)",
                scoreId, clip(username, 64), courseId, termId, oldScore, newScore, action, clip(operator, 64));
    }

    /** 单条成绩的改分记录（成绩删除后仍可按 score_id 查）。 */
    public static List<Map<String, Object>> history(long scoreId) {
        require();
        return db().query(
                "SELECT id, score_id, username, course_id, term_id, old_score, new_score, action, operator, created_at "
                        + "FROM grade_score_history WHERE score_id=? ORDER BY id DESC LIMIT 200",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("scoreId", rs.getLong("score_id"));
                    m.put("username", rs.getString("username"));
                    m.put("courseId", rs.getLong("course_id"));
                    m.put("termId", rs.getLong("term_id"));
                    BigDecimal o = rs.getBigDecimal("old_score");
                    BigDecimal n = rs.getBigDecimal("new_score");
                    m.put("oldScore", o == null ? null : o.stripTrailingZeros().toPlainString());
                    m.put("newScore", n == null ? null : n.stripTrailingZeros().toPlainString());
                    m.put("action", rs.getString("action"));
                    m.put("operator", rs.getString("operator"));
                    m.put("createdAt", rs.getString("created_at"));
                    return m;
                },
                scoreId);
    }

    /** 分布与及格率：按课程/学期筛选；及格线固定 60。 */
    public static Map<String, Object> stats(Long courseId, Long termId) {
        require();
        StringBuilder sql = new StringBuilder("SELECT s.score FROM grade_score s WHERE 1=1 ");
        List<Object> args = new java.util.ArrayList<>();
        if (courseId != null && courseId > 0) {
            sql.append("AND s.course_id=? ");
            args.add(courseId);
        }
        if (termId != null && termId > 0) {
            sql.append("AND s.term_id=? ");
            args.add(termId);
        }
        List<BigDecimal> scores = db().query(
                sql.toString(), (rs, i) -> rs.getBigDecimal("score"), args.toArray());
        return summarize(scores);
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
