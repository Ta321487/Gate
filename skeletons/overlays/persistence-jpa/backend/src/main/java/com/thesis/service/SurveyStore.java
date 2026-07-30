package com.thesis.service;

import com.thesis.config.JpaSupport;
import com.thesis.config.JpaDb;
import com.thesis.config.GeneratedKeyHolder;
import com.thesis.config.KeyHolder;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 简易问卷（C-03）：题目配置、填写、回收、选项计数。
 */
public class SurveyStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static boolean enabled;
    private static Boolean tableReady;

    private SurveyStore() {}

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
                            + "WHERE table_schema=DATABASE() AND table_name='survey_question'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static void require() {
        if (!ready()) throw new IllegalStateException("问卷功能暂不可用");
    }

    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        String s = String.valueOf(o);
        return s.isBlank() ? null : s;
    }

    private static String clip(String s, int max) {
        if (s == null) return "";
        String t = s.trim();
        return t.length() <= max ? t : t.substring(0, max);
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static Long toLong(Object o) {
        if (o == null || String.valueOf(o).isBlank()) return null;
        return Long.parseLong(String.valueOf(o));
    }

    private static int toInt(Object o, int def) {
        if (o == null || String.valueOf(o).isBlank()) return def;
        return Integer.parseInt(String.valueOf(o));
    }

    private static Map<String, Object> pageOut(List<?> list, Integer total, int page, int size) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    private static String normalizeType(String type) {
        String t = type == null ? "" : type.trim().toLowerCase(Locale.ROOT);
        if (!Set.of("single", "multi", "text").contains(t)) {
            throw new IllegalArgumentException("题型须为 single/multi/text");
        }
        return t;
    }

    private static Map<String, Object> mapForm(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("title", rs.getString("title"));
        m.put("author", rs.getString("author"));
        m.put("isbn", rs.getString("isbn"));
        m.put("categoryId", rs.getObject("category_id"));
        m.put("stock", rs.getInt("stock"));
        m.put("status", rs.getString("status"));
        return m;
    }

    private static Map<String, Object> mapQuestion(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("formId", rs.getLong("form_id"));
        m.put("type", rs.getString("type"));
        m.put("stem", rs.getString("stem"));
        m.put("optionsJson", rs.getString("options_json"));
        m.put("sortNo", rs.getInt("sort_no"));
        m.put("required", rs.getInt("required") == 1);
        return m;
    }

    public static List<Map<String, Object>> listOpenForms() {
        require();
        return db().query(
                "SELECT * FROM survey_form WHERE status='available' AND stock>0 ORDER BY id DESC",
                (rs, i) -> mapForm(rs));
    }

    public static Map<String, Object> getForm(long id) {
        if (!ready()) return null;
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM survey_form WHERE id=?", (rs, i) -> mapForm(rs), id);
        return list.isEmpty() ? null : list.get(0);
    }

    public static List<Map<String, Object>> listQuestions(long formId) {
        require();
        return db().query(
                "SELECT * FROM survey_question WHERE form_id=? ORDER BY sort_no, id",
                (rs, i) -> mapQuestion(rs),
                formId);
    }

    public static Map<String, Object> pageQuestionsAdmin(long formId, int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 20;
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM survey_question WHERE form_id=?", Integer.class, formId);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM survey_question WHERE form_id=? ORDER BY sort_no, id LIMIT ? OFFSET ?",
                (rs, i) -> mapQuestion(rs),
                formId, size, (page - 1) * size);
        return pageOut(list, total, page, size);
    }

    public static Map<String, Object> createQuestion(Map<String, Object> body) {
        require();
        long formId = toLong(body.get("formId")) != null
                ? toLong(body.get("formId"))
                : toLong(body.get("form_id"));
        if (formId <= 0 || getForm(formId) == null) throw new IllegalArgumentException("问卷不存在");
        String type = normalizeType(str(body.get("type")));
        String stem = clip(str(body.get("stem")), 2000);
        if (stem.isBlank()) throw new IllegalArgumentException("题干不能为空");
        String options = str(body.get("optionsJson"));
        if (options.isBlank()) options = str(body.get("options_json"));
        int sortNo = toInt(body.get("sortNo"), toInt(body.get("sort_no"), 0));
        boolean required = !"0".equals(str(body.get("required"))) && !"false".equalsIgnoreCase(str(body.get("required")));
        KeyHolder kh = new GeneratedKeyHolder();
        String finalOptions = options;
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO survey_question (form_id,type,stem,options_json,sort_no,required) VALUES (?,?,?,?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, formId);
            ps.setString(2, type);
            ps.setString(3, stem);
            ps.setString(4, finalOptions);
            ps.setInt(5, sortNo);
            ps.setInt(6, required ? 1 : 0);
            return ps;
        }, kh);
        Number key = kh.getKey();
        long id = key == null ? 0L : key.longValue();
        List<Map<String, Object>> one = db().query(
                "SELECT * FROM survey_question WHERE id=?", (rs, i) -> mapQuestion(rs), id);
        return one.isEmpty() ? Map.of() : one.get(0);
    }

    public static boolean deleteQuestion(long id) {
        require();
        return db().update("DELETE FROM survey_question WHERE id=?", id) > 0;
    }

    public static Map<String, Object> submit(String username, long formId, List<Map<String, Object>> answers) {
        require();
        Map<String, Object> form = getForm(formId);
        if (form == null || !"available".equals(str(form.get("status")))) {
            throw new IllegalStateException("问卷未开放");
        }
        Integer dup = db().queryForObject(
                "SELECT COUNT(*) FROM survey_response WHERE form_id=? AND username=?",
                Integer.class, formId, username);
        if (dup != null && dup > 0) throw new IllegalStateException("您已填写过该问卷");
        List<Map<String, Object>> qs = listQuestions(formId);
        Map<Long, String> ansMap = new HashMap<>();
        if (answers != null) {
            for (Map<String, Object> a : answers) {
                Long qid = toLong(a.get("questionId"));
                if (qid == null) qid = toLong(a.get("question_id"));
                if (qid == null) continue;
                String text = str(a.get("answerText"));
                if (text.isBlank()) text = str(a.get("answer_text"));
                ansMap.put(qid, clip(text, 2000));
            }
        }
        for (Map<String, Object> q : qs) {
            if (Boolean.TRUE.equals(q.get("required"))) {
                String v = ansMap.getOrDefault(toLong(q.get("id")), "");
                if (v.isBlank()) throw new IllegalArgumentException("请完成必填题：" + q.get("stem"));
            }
        }
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO survey_response (form_id,username,submitted_at) VALUES (?,?,NOW())",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, formId);
            ps.setString(2, username);
            return ps;
        }, kh);
        long responseId = kh.getKey() == null ? 0L : kh.getKey().longValue();
        for (Map<String, Object> q : qs) {
            long qid = toLong(q.get("id"));
            String text = ansMap.getOrDefault(qid, "");
            db().update(
                    "INSERT INTO survey_answer (response_id,question_id,answer_text) VALUES (?,?,?)",
                    responseId, qid, text);
        }
        return getResponse(responseId);
    }

    public static Map<String, Object> getResponse(long id) {
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM survey_response WHERE id=?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("formId", rs.getLong("form_id"));
                    m.put("username", rs.getString("username"));
                    m.put("submittedAt", fmt(rs.getTimestamp("submitted_at")));
                    return m;
                },
                id);
        return list.isEmpty() ? null : list.get(0);
    }

    public static Map<String, Object> pageMine(String username, int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM survey_response WHERE username=?", Integer.class, username);
        List<Map<String, Object>> list = db().query(
                "SELECT r.*, f.title AS form_title FROM survey_response r "
                        + "LEFT JOIN survey_form f ON f.id=r.form_id "
                        + "WHERE r.username=? ORDER BY r.id DESC LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("formId", rs.getLong("form_id"));
                    m.put("formTitle", rs.getString("form_title"));
                    m.put("submittedAt", fmt(rs.getTimestamp("submitted_at")));
                    return m;
                },
                username, size, (page - 1) * size);
        return pageOut(list, total, page, size);
    }

    public static Map<String, Object> pageResponsesAdmin(long formId, int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM survey_response WHERE form_id=?", Integer.class, formId);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM survey_response WHERE form_id=? ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("formId", rs.getLong("form_id"));
                    m.put("username", rs.getString("username"));
                    m.put("submittedAt", fmt(rs.getTimestamp("submitted_at")));
                    return m;
                },
                formId, size, (page - 1) * size);
        return pageOut(list, total, page, size);
    }

    /** 按题统计选项出现次数（text 题仅计非空份数）。 */
    public static List<Map<String, Object>> stats(long formId) {
        require();
        List<Map<String, Object>> qs = listQuestions(formId);
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> q : qs) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("questionId", q.get("id"));
            row.put("stem", q.get("stem"));
            row.put("type", q.get("type"));
            String type = str(q.get("type"));
            if ("text".equals(type)) {
                Integer n = db().queryForObject(
                        "SELECT COUNT(*) FROM survey_answer WHERE question_id=? AND answer_text<>''",
                        Integer.class, q.get("id"));
                row.put("filledCount", n == null ? 0 : n);
                row.put("options", List.of());
            } else {
                List<String> opts = parseOpts(str(q.get("optionsJson")));
                List<Map<String, Object>> counts = new ArrayList<>();
                for (int i = 0; i < opts.size(); i++) {
                    String letter = String.valueOf((char) ('A' + i));
                    String label = opts.get(i);
                    Integer n = db().queryForObject(
                            "SELECT COUNT(*) FROM survey_answer WHERE question_id=? AND ("
                                    + "answer_text=? OR answer_text LIKE ? OR answer_text LIKE ? OR answer_text LIKE ?)",
                            Integer.class,
                            q.get("id"),
                            letter,
                            letter + ",%",
                            "%," + letter,
                            "%," + letter + ",%");
                    // also match by full label
                    Integer n2 = db().queryForObject(
                            "SELECT COUNT(*) FROM survey_answer WHERE question_id=? AND ("
                                    + "answer_text=? OR answer_text LIKE ? OR answer_text LIKE ? OR answer_text LIKE ?)",
                            Integer.class,
                            q.get("id"),
                            label,
                            label + ",%",
                            "%," + label,
                            "%," + label + ",%");
                    Map<String, Object> oc = new LinkedHashMap<>();
                    oc.put("key", letter);
                    oc.put("label", label);
                    oc.put("count", Math.max(n == null ? 0 : n, n2 == null ? 0 : n2));
                    counts.add(oc);
                }
                row.put("options", counts);
            }
            out.add(row);
        }
        return out;
    }

    private static List<String> parseOpts(String json) {
        if (json == null || json.isBlank()) return List.of();
        try {
            String t = json.trim();
            if (!t.startsWith("[")) return List.of();
            t = t.substring(1, t.endsWith("]") ? t.length() - 1 : t.length());
            List<String> out = new ArrayList<>();
            for (String p : t.split("\",\"")) {
                String x = p.replace("\"", "").trim();
                if (!x.isEmpty()) out.add(x);
            }
            return out;
        } catch (Exception e) {
            return List.of();
        }
    }
}

