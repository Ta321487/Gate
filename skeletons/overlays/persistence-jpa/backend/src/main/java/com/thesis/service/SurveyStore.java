package com.thesis.service;

import com.thesis.config.GeneratedKeyHolder;
import com.thesis.config.JpaDb;
import com.thesis.config.JpaSupport;
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
 * I-09：开放截止/匿名/跳题显隐/进度/限填/必答/矩阵/草稿/组织投放/回收率/截止提醒。
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

    private static boolean toBool(Object o, boolean def) {
        if (o == null || String.valueOf(o).isBlank()) return def;
        String s = str(o);
        if ("1".equals(s) || "true".equalsIgnoreCase(s)) return true;
        if ("0".equals(s) || "false".equalsIgnoreCase(s)) return false;
        return def;
    }

    private static LocalDateTime parseDt(Object o) {
        if (o == null || str(o).isBlank()) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime();
        if (o instanceof LocalDateTime ldt) return ldt;
        String s = str(o).replace('T', ' ');
        if (s.length() == 10) s = s + " 00:00:00";
        try {
            return LocalDateTime.parse(s, FMT);
        } catch (Exception e) {
            try {
                return LocalDateTime.parse(s.substring(0, Math.min(19, s.length())), FMT);
            } catch (Exception e2) {
                return null;
            }
        }
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
        if (!Set.of("single", "multi", "text", "matrix").contains(t)) {
            throw new IllegalArgumentException("题型须为 single/multi/text/matrix");
        }
        return t;
    }

    private static boolean hasCol(ResultSet rs, String col) {
        try {
            rs.findColumn(col);
            return true;
        } catch (SQLException e) {
            return false;
        }
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
        if (hasCol(rs, "open_at")) m.put("openAt", fmt(rs.getTimestamp("open_at")));
        if (hasCol(rs, "close_at")) m.put("closeAt", fmt(rs.getTimestamp("close_at")));
        if (hasCol(rs, "anonymous")) m.put("anonymous", rs.getInt("anonymous") == 1);
        else m.put("anonymous", false);
        if (hasCol(rs, "once_only")) m.put("onceOnly", rs.getInt("once_only") == 1);
        else m.put("onceOnly", true);
        if (hasCol(rs, "target_org")) m.put("targetOrg", rs.getString("target_org"));
        else m.put("targetOrg", "");
        if (hasCol(rs, "remind_before_hours")) m.put("remindBeforeHours", rs.getInt("remind_before_hours"));
        else m.put("remindBeforeHours", 0);
        if (hasCol(rs, "target_count")) m.put("targetCount", rs.getInt("target_count"));
        else m.put("targetCount", 0);
        return m;
    }

    private static Map<String, Object> mapQuestion(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("formId", rs.getLong("form_id"));
        m.put("type", rs.getString("type"));
        m.put("stem", rs.getString("stem"));
        m.put("optionsJson", ChoiceOptionOps.loadJson(db(), "survey_option", rs.getLong("id")));
        m.put("sortNo", rs.getInt("sort_no"));
        m.put("required", rs.getInt("required") == 1);
        if (hasCol(rs, "skip_when_label")) m.put("skipWhenLabel", str(rs.getString("skip_when_label")));
        else m.put("skipWhenLabel", "");
        if (hasCol(rs, "skip_to_sort")) {
            Object v = rs.getObject("skip_to_sort");
            m.put("skipToSort", v == null ? null : rs.getInt("skip_to_sort"));
        } else m.put("skipToSort", null);
        if (hasCol(rs, "show_when_qid")) {
            Object v = rs.getObject("show_when_qid");
            m.put("showWhenQid", v == null ? null : rs.getLong("show_when_qid"));
        } else m.put("showWhenQid", null);
        if (hasCol(rs, "show_when_label")) m.put("showWhenLabel", str(rs.getString("show_when_label")));
        else m.put("showWhenLabel", "");
        if (hasCol(rs, "matrix_rows")) m.put("matrixRows", str(rs.getString("matrix_rows")));
        else m.put("matrixRows", "");
        return m;
    }

    private static String userDept(String username) {
        if (username == null || username.isBlank()) return "";
        try {
            List<String> rows = db().query(
                    "SELECT profile_json FROM sys_user WHERE username=?",
                    (rs, i) -> str(rs.getString(1)),
                    username);
            if (rows.isEmpty()) return "";
            String json = rows.get(0);
            int idx = json.indexOf("\"dept\"");
            if (idx < 0) return "";
            int colon = json.indexOf(':', idx);
            int q1 = json.indexOf('"', colon + 1);
            int q2 = json.indexOf('"', q1 + 1);
            if (q1 < 0 || q2 < 0) return "";
            return json.substring(q1 + 1, q2).trim();
        } catch (Exception e) {
            return "";
        }
    }

    private static boolean inAudience(long formId, String username) {
        try {
            Integer total = db().queryForObject(
                    "SELECT COUNT(*) FROM survey_audience WHERE form_id=?", Integer.class, formId);
            if (total == null || total == 0) return true;
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM survey_audience WHERE form_id=? AND username=?",
                    Integer.class, formId, username);
            return n != null && n > 0;
        } catch (Exception e) {
            return true;
        }
    }

    private static boolean inOpenWindow(Map<String, Object> form) {
        LocalDateTime now = LocalDateTime.now();
        LocalDateTime open = parseDt(form.get("openAt"));
        LocalDateTime close = parseDt(form.get("closeAt"));
        if (open != null && now.isBefore(open)) return false;
        if (close != null && now.isAfter(close)) return false;
        return true;
    }

    public static List<Map<String, Object>> listOpenForms() {
        return listOpenForms(null);
    }

    public static List<Map<String, Object>> listOpenForms(String username) {
        require();
        List<Map<String, Object>> all = db().query(
                "SELECT * FROM survey_form WHERE status='available' AND stock>0 ORDER BY id DESC",
                (rs, i) -> mapForm(rs));
        String dept = username == null ? "" : userDept(username);
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> f : all) {
            if (!inOpenWindow(f)) continue;
            String org = str(f.get("targetOrg"));
            if (!org.isBlank() && (dept.isBlank() || !dept.contains(org) && !org.contains(dept))) {
                continue;
            }
            long fid = toLong(f.get("id"));
            if (username != null && !inAudience(fid, username)) continue;
            out.add(f);
        }
        return out;
    }

    public static List<Map<String, Object>> listAdminForms() {
        require();
        return db().query("SELECT * FROM survey_form ORDER BY id DESC", (rs, i) -> mapForm(rs));
    }

    public static Map<String, Object> getForm(long id) {
        if (!ready()) return null;
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM survey_form WHERE id=?", (rs, i) -> mapForm(rs), id);
        return list.isEmpty() ? null : list.get(0);
    }

    public static Map<String, Object> updateFormSettings(long formId, Map<String, Object> body) {
        require();
        if (getForm(formId) == null) throw new IllegalArgumentException("问卷不存在");
        if (body == null) body = Map.of();
        if (body.containsKey("openAt") || body.containsKey("open_at")) {
            LocalDateTime dt = parseDt(body.containsKey("openAt") ? body.get("openAt") : body.get("open_at"));
            db().update("UPDATE survey_form SET open_at=? WHERE id=?",
                    dt == null ? null : Timestamp.valueOf(dt), formId);
        }
        if (body.containsKey("closeAt") || body.containsKey("close_at")) {
            LocalDateTime dt = parseDt(body.containsKey("closeAt") ? body.get("closeAt") : body.get("close_at"));
            db().update("UPDATE survey_form SET close_at=? WHERE id=?",
                    dt == null ? null : Timestamp.valueOf(dt), formId);
        }
        if (body.containsKey("anonymous")) {
            db().update("UPDATE survey_form SET anonymous=? WHERE id=?",
                    toBool(body.get("anonymous"), false) ? 1 : 0, formId);
        }
        if (body.containsKey("onceOnly") || body.containsKey("once_only")) {
            Object v = body.containsKey("onceOnly") ? body.get("onceOnly") : body.get("once_only");
            db().update("UPDATE survey_form SET once_only=? WHERE id=?", toBool(v, true) ? 1 : 0, formId);
        }
        if (body.containsKey("targetOrg") || body.containsKey("target_org")) {
            String org = clip(str(body.containsKey("targetOrg") ? body.get("targetOrg") : body.get("target_org")), 128);
            db().update("UPDATE survey_form SET target_org=? WHERE id=?", org, formId);
        }
        if (body.containsKey("remindBeforeHours") || body.containsKey("remind_before_hours")) {
            Object v = body.containsKey("remindBeforeHours")
                    ? body.get("remindBeforeHours") : body.get("remind_before_hours");
            db().update("UPDATE survey_form SET remind_before_hours=? WHERE id=?", toInt(v, 0), formId);
        }
        if (body.containsKey("targetCount") || body.containsKey("target_count")) {
            Object v = body.containsKey("targetCount") ? body.get("targetCount") : body.get("target_count");
            db().update("UPDATE survey_form SET target_count=? WHERE id=?", toInt(v, 0), formId);
        }
        if (body.containsKey("status")) {
            db().update("UPDATE survey_form SET status=? WHERE id=?", clip(str(body.get("status")), 32), formId);
        }
        return getForm(formId);
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
        boolean required = toBool(body.get("required"), true);
        String skipWhen = clip(str(body.containsKey("skipWhenLabel")
                ? body.get("skipWhenLabel") : body.get("skip_when_label")), 8);
        Integer skipTo = null;
        if (body.containsKey("skipToSort") || body.containsKey("skip_to_sort")) {
            Object v = body.containsKey("skipToSort") ? body.get("skipToSort") : body.get("skip_to_sort");
            if (v != null && !str(v).isBlank()) skipTo = toInt(v, 0);
        }
        Long showQid = toLong(body.containsKey("showWhenQid")
                ? body.get("showWhenQid") : body.get("show_when_qid"));
        String showLabel = clip(str(body.containsKey("showWhenLabel")
                ? body.get("showWhenLabel") : body.get("show_when_label")), 8);
        String matrixRows = clip(str(body.containsKey("matrixRows")
                ? body.get("matrixRows") : body.get("matrix_rows")), 1000);
        KeyHolder kh = new GeneratedKeyHolder();
        String finalOptions = options;
        Integer finalSkipTo = skipTo;
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO survey_question (form_id,type,stem,sort_no,required,"
                            + "skip_when_label,skip_to_sort,show_when_qid,show_when_label,matrix_rows) "
                            + "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, formId);
            ps.setString(2, type);
            ps.setString(3, stem);
            ps.setInt(4, sortNo);
            ps.setInt(5, required ? 1 : 0);
            ps.setString(6, skipWhen);
            if (finalSkipTo == null) ps.setObject(7, null);
            else ps.setInt(7, finalSkipTo);
            if (showQid == null) ps.setObject(8, null);
            else ps.setLong(8, showQid);
            ps.setString(9, showLabel);
            ps.setString(10, matrixRows);
            return ps;
        }, kh);
        Number key = kh.getKey();
        long id = key == null ? 0L : key.longValue();
        ChoiceOptionOps.replace(db(), "survey_option", id, finalOptions);
        List<Map<String, Object>> one = db().query(
                "SELECT * FROM survey_question WHERE id=?", (rs, i) -> mapQuestion(rs), id);
        return one.isEmpty() ? Map.of() : one.get(0);
    }

    public static boolean deleteQuestion(long id) {
        require();
        db().update("DELETE FROM survey_option WHERE question_id=?", id);
        return db().update("DELETE FROM survey_question WHERE id=?", id) > 0;
    }

    private static void ensureDraftTable() {
        try {
            db().execute(
                    "CREATE TABLE IF NOT EXISTS survey_draft ("
                            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
                            + "form_id BIGINT NOT NULL,"
                            + "username VARCHAR(64) NOT NULL,"
                            + "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,"
                            + "UNIQUE KEY uk_survey_draft (form_id, username))");
            db().execute(
                    "CREATE TABLE IF NOT EXISTS survey_draft_answer ("
                            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
                            + "form_id BIGINT NOT NULL,"
                            + "username VARCHAR(64) NOT NULL,"
                            + "question_id BIGINT NOT NULL,"
                            + "answer_text VARCHAR(2000) DEFAULT '',"
                            + "UNIQUE KEY uk_survey_draft_ans (form_id, username, question_id),"
                            + "KEY idx_survey_draft_ans (form_id, username))");
        } catch (Exception ignored) {
        }
    }

    public static Map<String, Object> loadDraft(String username, long formId) {
        require();
        ensureDraftTable();
        try {
            List<Map<String, Object>> head = db().query(
                    "SELECT updated_at FROM survey_draft WHERE form_id=? AND username=?",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("updatedAt", fmt(rs.getTimestamp("updated_at")));
                        return m;
                    },
                    formId, username);
            if (head.isEmpty()) return Map.of();
            List<Map<String, Object>> answers = db().query(
                    "SELECT question_id, answer_text FROM survey_draft_answer "
                            + "WHERE form_id=? AND username=? ORDER BY question_id",
                    (rs, i) -> {
                        Map<String, Object> a = new LinkedHashMap<>();
                        a.put("questionId", rs.getLong("question_id"));
                        a.put("answerText", str(rs.getString("answer_text")));
                        return a;
                    },
                    formId, username);
            Map<String, Object> out = new LinkedHashMap<>(head.get(0));
            out.put("answers", answers);
            return out;
        } catch (Exception e) {
            return Map.of();
        }
    }

    public static void saveDraft(String username, long formId, List<Map<String, Object>> answers) {
        require();
        ensureDraftTable();
        db().update(
                "INSERT INTO survey_draft (form_id, username) VALUES (?,?) "
                        + "ON DUPLICATE KEY UPDATE updated_at=NOW()",
                formId, username);
        db().update("DELETE FROM survey_draft_answer WHERE form_id=? AND username=?", formId, username);
        if (answers == null) return;
        for (Map<String, Object> a : answers) {
            Long qid = toLong(a.get("questionId"));
            if (qid == null) qid = toLong(a.get("question_id"));
            if (qid == null) continue;
            String text = str(a.get("answerText"));
            if (text.isBlank()) text = str(a.get("answer_text"));
            db().update(
                    "INSERT INTO survey_draft_answer (form_id, username, question_id, answer_text) VALUES (?,?,?,?)",
                    formId, username, qid, clip(text, 2000));
        }
    }

    private static void clearDraft(String username, long formId) {
        try {
            db().update("DELETE FROM survey_draft_answer WHERE form_id=? AND username=?", formId, username);
            db().update("DELETE FROM survey_draft WHERE form_id=? AND username=?", formId, username);
        } catch (Exception ignored) {
        }
    }

    public static Map<String, Object> submit(String username, long formId, List<Map<String, Object>> answers) {
        require();
        Map<String, Object> form = getForm(formId);
        if (form == null || !"available".equals(str(form.get("status")))) {
            throw new IllegalStateException("问卷未开放");
        }
        if (!inOpenWindow(form)) throw new IllegalStateException("不在问卷开放时段内");
        String org = str(form.get("targetOrg"));
        if (!org.isBlank()) {
            String dept = userDept(username);
            if (dept.isBlank() || (!dept.contains(org) && !org.contains(dept))) {
                throw new IllegalStateException("本问卷未对您所在组织开放");
            }
        }
        if (!inAudience(formId, username)) throw new IllegalStateException("您不在本问卷投放名单中");
        boolean onceOnly = Boolean.TRUE.equals(form.get("onceOnly"));
        Integer dup = db().queryForObject(
                "SELECT COUNT(*) FROM survey_response WHERE form_id=? AND username=?",
                Integer.class, formId, username);
        if (onceOnly && dup != null && dup > 0) throw new IllegalStateException("您已填写过该问卷");
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
        Set<Long> visible = visibleQuestionIds(qs, ansMap);
        for (Map<String, Object> q : qs) {
            long qid = toLong(q.get("id"));
            if (!visible.contains(qid)) continue;
            if (Boolean.TRUE.equals(q.get("required"))) {
                String v = ansMap.getOrDefault(qid, "");
                if (v.isBlank()) throw new IllegalArgumentException("请完成必填题：" + q.get("stem"));
            }
        }
        String storeUser = username;
        if (!onceOnly && dup != null && dup > 0) {
            storeUser = clip(username + "#" + System.currentTimeMillis() % 1000000, 64);
        }
        KeyHolder kh = new GeneratedKeyHolder();
        String finalUser = storeUser;
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO survey_response (form_id,username,submitted_at) VALUES (?,?,NOW())",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, formId);
            ps.setString(2, finalUser);
            return ps;
        }, kh);
        long responseId = kh.getKey() == null ? 0L : kh.getKey().longValue();
        for (Map<String, Object> q : qs) {
            long qid = toLong(q.get("id"));
            if (!visible.contains(qid)) continue;
            String text = ansMap.getOrDefault(qid, "");
            db().update(
                    "INSERT INTO survey_answer (response_id,question_id,answer_text) VALUES (?,?,?)",
                    responseId, qid, text);
        }
        clearDraft(username, formId);
        Map<String, Object> resp = getResponse(responseId);
        if (resp != null) {
            resp.put("thanks", true);
            resp.put("formId", formId);
        }
        return resp;
    }

    /** 按跳题/显隐规则求当前可见题 ID（提交校验用）。 */
    private static Set<Long> visibleQuestionIds(List<Map<String, Object>> qs, Map<Long, String> ansMap) {
        List<Map<String, Object>> ordered = new ArrayList<>(qs);
        ordered.sort(Comparator.comparingInt(q -> toInt(q.get("sortNo"), 0)));
        Set<Long> visible = new LinkedHashSet<>();
        Integer jumpTo = null;
        boolean ended = false;
        for (Map<String, Object> q : ordered) {
            int sort = toInt(q.get("sortNo"), 0);
            if (ended) break;
            if (jumpTo != null && sort < jumpTo) continue;
            jumpTo = null;
            Long showQid = toLong(q.get("showWhenQid"));
            String showLabel = str(q.get("showWhenLabel")).toUpperCase(Locale.ROOT);
            if (showQid != null && showQid > 0 && !showLabel.isBlank()) {
                String ans = str(ansMap.get(showQid)).toUpperCase(Locale.ROOT);
                if (!ans.contains(showLabel)) continue;
            }
            long qid = toLong(q.get("id"));
            visible.add(qid);
            String skipWhen = str(q.get("skipWhenLabel")).toUpperCase(Locale.ROOT);
            Object skipToObj = q.get("skipToSort");
            if (!skipWhen.isBlank() && skipToObj != null) {
                String ans = str(ansMap.get(qid)).toUpperCase(Locale.ROOT);
                if (ans.contains(skipWhen)) {
                    int st = toInt(skipToObj, 0);
                    if (st < 0) {
                        ended = true;
                    } else {
                        jumpTo = st;
                    }
                }
            }
        }
        return visible;
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
                "SELECT COUNT(*) FROM survey_response WHERE username=? OR username LIKE ?",
                Integer.class, username, username + "#%");
        List<Map<String, Object>> list = db().query(
                "SELECT r.*, f.title AS form_title FROM survey_response r "
                        + "LEFT JOIN survey_form f ON f.id=r.form_id "
                        + "WHERE r.username=? OR r.username LIKE ? ORDER BY r.id DESC LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("formId", rs.getLong("form_id"));
                    m.put("formTitle", rs.getString("form_title"));
                    m.put("submittedAt", fmt(rs.getTimestamp("submitted_at")));
                    return m;
                },
                username, username + "#%", size, (page - 1) * size);
        return pageOut(list, total, page, size);
    }

    public static Map<String, Object> pageResponsesAdmin(long formId, int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        Map<String, Object> form = getForm(formId);
        boolean anon = form != null && Boolean.TRUE.equals(form.get("anonymous"));
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM survey_response WHERE form_id=?", Integer.class, formId);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM survey_response WHERE form_id=? ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("formId", rs.getLong("form_id"));
                    String u = rs.getString("username");
                    m.put("username", anon ? "匿名" : u);
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
            } else if ("matrix".equals(type)) {
                List<String> cols = parseOpts(str(q.get("optionsJson")));
                List<Map<String, Object>> counts = new ArrayList<>();
                for (int i = 0; i < cols.size(); i++) {
                    String letter = String.valueOf((char) ('A' + i));
                    Integer n = db().queryForObject(
                            "SELECT COUNT(*) FROM survey_answer WHERE question_id=? AND answer_text LIKE ?",
                            Integer.class, q.get("id"), "%" + letter + "%");
                    Map<String, Object> oc = new LinkedHashMap<>();
                    oc.put("key", letter);
                    oc.put("label", cols.get(i));
                    oc.put("count", n == null ? 0 : n);
                    counts.add(oc);
                }
                row.put("options", counts);
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

    public static List<Map<String, Object>> recycleCards() {
        if (!ready()) return List.of();
        List<Map<String, Object>> forms = listAdminForms();
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> f : forms) {
            long fid = toLong(f.get("id"));
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM survey_response WHERE form_id=?", Integer.class, fid);
            int count = n == null ? 0 : n;
            int goal = toInt(f.get("targetCount"), 0);
            if (goal <= 0) goal = Math.max(toInt(f.get("stock"), 0) * 20, 20);
            int pct = goal <= 0 ? 0 : Math.min(100, (int) Math.round(count * 100.0 / goal));
            Map<String, Object> card = new LinkedHashMap<>();
            card.put("formId", fid);
            card.put("title", f.get("title"));
            card.put("responseCount", count);
            card.put("targetCount", goal);
            card.put("ratePct", pct);
            out.add(card);
        }
        return out;
    }

    /** 按开放/截止时间自动上架/下架。 */
    public static int scheduleOpenCloseSweep() {
        if (!ready()) return 0;
        int n = 0;
        LocalDateTime now = LocalDateTime.now();
        List<Map<String, Object>> forms = db().query(
                "SELECT * FROM survey_form WHERE open_at IS NOT NULL OR close_at IS NOT NULL",
                (rs, i) -> mapForm(rs));
        for (Map<String, Object> f : forms) {
            long id = toLong(f.get("id"));
            boolean in = inOpenWindow(f);
            String status = str(f.get("status"));
            if (in && !"available".equals(status)) {
                db().update("UPDATE survey_form SET status='available' WHERE id=?", id);
                n++;
            } else if (!in && "available".equals(status)) {
                db().update("UPDATE survey_form SET status='offline' WHERE id=?", id);
                n++;
            }
        }
        return n;
    }

    /** 截止前提醒未填用户。 */
    public static int remindCloseSweep() {
        if (!ready()) return 0;
        int sent = 0;
        List<Map<String, Object>> forms = db().query(
                "SELECT * FROM survey_form WHERE close_at IS NOT NULL AND remind_before_hours>0 "
                        + "AND close_reminded_at IS NULL AND status='available'",
                (rs, i) -> mapForm(rs));
        LocalDateTime now = LocalDateTime.now();
        for (Map<String, Object> f : forms) {
            LocalDateTime close = parseDt(f.get("closeAt"));
            int hours = toInt(f.get("remindBeforeHours"), 0);
            if (close == null || hours <= 0) continue;
            if (now.isBefore(close.minusHours(hours))) continue;
            if (now.isAfter(close)) continue;
            long formId = toLong(f.get("id"));
            String title = "问卷即将截止：" + str(f.get("title"));
            String body = "问卷「" + str(f.get("title")) + "」将于 " + fmt(close) + " 截止，请尽快填写。";
            List<String> users = db().query(
                    "SELECT username FROM sys_user WHERE role='user' AND enabled=1",
                    (rs, i) -> rs.getString(1));
            for (String u : users) {
                Integer dup = db().queryForObject(
                        "SELECT COUNT(*) FROM survey_response WHERE form_id=? AND (username=? OR username LIKE ?)",
                        Integer.class, formId, u, u + "#%");
                if (dup != null && dup > 0) continue;
                try {
                    MessageStore.send(u, title, body, "survey", formId);
                    sent++;
                } catch (Exception ignored) {
                }
            }
            db().update("UPDATE survey_form SET close_reminded_at=NOW() WHERE id=?", formId);
        }
        return sent;
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
