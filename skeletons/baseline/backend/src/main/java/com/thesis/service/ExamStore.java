package com.thesis.service;

import com.thesis.config.JdbcSupport;
import com.thesis.service.UserStore;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;

/**
 * 在线考试（C-01）：题库、组卷、作答、自动判分。
 */
public class ExamStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final int REGEX_MAX = 200;
    private static final int SUBJECTIVE_ANSWER_MAX = 2000;

    private static boolean enabled;
    private static boolean practiceEnabled;
    private static boolean explainEnabled;
    private static boolean timerEnabled;
    private static boolean attemptLimitEnabled;
    private static boolean rankEnabled;
    private static boolean wrongbookEnabled;
    private static boolean requireBeforeTicket;
    private static Boolean tableReady;
    private static Boolean gateColReady;

    private ExamStore() {}

    public static void configure(
            boolean on,
            boolean practice,
            boolean explain,
            boolean timer,
            boolean attemptLimit,
            boolean rank,
            boolean wrongbook) {
        configure(on, practice, explain, timer, attemptLimit, rank, wrongbook, false);
    }

    public static void configure(
            boolean on,
            boolean practice,
            boolean explain,
            boolean timer,
            boolean attemptLimit,
            boolean rank,
            boolean wrongbook,
            boolean requireBeforeTicketFlag) {
        enabled = on;
        practiceEnabled = practice;
        explainEnabled = explain;
        timerEnabled = timer;
        attemptLimitEnabled = attemptLimit;
        rankEnabled = rank;
        wrongbookEnabled = wrongbook;
        requireBeforeTicket = requireBeforeTicketFlag;
        tableReady = null;
        gateColReady = null;
    }

    public static boolean enabled() {
        return enabled;
    }

    public static boolean practiceEnabled() {
        return practiceEnabled;
    }

    public static boolean explainEnabled() {
        return explainEnabled;
    }

    public static boolean rankEnabled() {
        return rankEnabled;
    }

    public static boolean wrongbookEnabled() {
        return wrongbookEnabled;
    }

    public static boolean requireBeforeTicket() {
        return requireBeforeTicket;
    }

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    private static boolean hasGateCols() {
        if (gateColReady != null) return gateColReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.columns "
                            + "WHERE table_schema=DATABASE() AND table_name='exam_paper' AND column_name='gate_ticket'",
                    Integer.class);
            gateColReady = n != null && n > 0;
        } catch (Exception e) {
            gateColReady = false;
        }
        return gateColReady;
    }

    /** C-02：申请前须通过 gate_ticket=1 的已发布试卷（pass_score 为百分制，默认 60）。 */
    public static void assertTicketGatePassed(String username) {
        if (!requireBeforeTicket || !ready()) return;
        if (!hasGateCols()) return;
        Integer gates = db().queryForObject(
                "SELECT COUNT(*) FROM exam_paper WHERE status='published' AND gate_ticket=1",
                Integer.class);
        if (gates == null || gates == 0) return;
        List<Map<String, Object>> rows = db().query(
                "SELECT a.score, a.total_score, p.pass_score FROM exam_attempt a "
                        + "JOIN exam_paper p ON p.id=a.paper_id "
                        + "WHERE a.username=? AND a.mode='exam' AND a.status='submitted' "
                        + "AND p.gate_ticket=1 AND p.status='published'",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("score", rs.getInt("score"));
                    m.put("total", rs.getInt("total_score"));
                    m.put("pass", rs.getInt("pass_score"));
                    return m;
                },
                username);
        for (Map<String, Object> r : rows) {
            int sc = (Integer) r.get("score");
            int tot = (Integer) r.get("total");
            int pass = (Integer) r.get("pass");
            if (pass <= 0) pass = 60;
            if (tot > 0 && sc * 100 >= pass * tot) return;
        }
        throw new IllegalStateException("请先通过安全准入考试后再提交申请");
    }

    public static boolean ready() {
        if (!enabled) return false;
        if (tableReady != null) return tableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='exam_question'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static void require() {
        if (!ready()) throw new IllegalStateException("考试功能暂不可用");
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

    // --- question ---

    private static Map<String, Object> mapQuestion(ResultSet rs, boolean admin) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("subjectId", rs.getObject("subject_id"));
        m.put("type", rs.getString("type"));
        m.put("stem", rs.getString("stem"));
        m.put("optionsJson", rs.getString("options_json"));
        m.put("score", rs.getInt("score"));
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        if (admin) {
            m.put("answerKey", rs.getString("answer_key"));
            if (explainEnabled) {
                m.put("explainText", rs.getString("explain_text"));
            }
        }
        return m;
    }

    public static Map<String, Object> getQuestion(long id) {
        if (!ready()) return null;
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM exam_question WHERE id=?", (rs, i) -> mapQuestion(rs, true), id);
        return list.isEmpty() ? null : list.get(0);
    }

    public static Map<String, Object> pageQuestionsAdmin(int page, int size, Long subjectId) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        String where = subjectId == null ? "" : " WHERE subject_id=?";
        Object[] countArgs = subjectId == null ? new Object[] {} : new Object[] {subjectId};
        Integer total = db().queryForObject("SELECT COUNT(*) FROM exam_question" + where, Integer.class, countArgs);
        List<Object> args = new ArrayList<>();
        if (subjectId != null) args.add(subjectId);
        args.add(size);
        args.add((page - 1) * size);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM exam_question" + where + " ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> mapQuestion(rs, true),
                args.toArray());
        return pageOut(list, total, page, size);
    }

    public static Map<String, Object> createQuestion(Map<String, Object> body) {
        require();
        String type = normalizeType(str(body.get("type")));
        String stem = clip(str(body.get("stem")), 2000);
        if (stem.isBlank()) throw new IllegalArgumentException("题干不能为空");
        String optionsJson = str(body.get("optionsJson"));
        if (optionsJson.isBlank()) optionsJson = str(body.get("options_json"));
        String answerKey = clip(str(body.get("answerKey")), 500);
        if (answerKey.isBlank()) answerKey = clip(str(body.get("answer_key")), 500);
        int score = toInt(body.get("score"), 5);
        Long subjectId = toLong(body.get("subjectId"));
        if (subjectId == null) subjectId = toLong(body.get("subject_id"));
        String explain = clip(str(body.get("explainText")), 2000);
        if (explain.isBlank()) explain = clip(str(body.get("explain_text")), 2000);
        KeyHolder kh = new GeneratedKeyHolder();
        Long finalSubjectId = subjectId;
        String finalAnswerKey = answerKey;
        String finalOptionsJson = optionsJson;
        String finalExplain = explain;
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO exam_question (subject_id,type,stem,options_json,answer_key,score,explain_text) "
                            + "VALUES (?,?,?,?,?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            if (finalSubjectId == null) ps.setNull(1, java.sql.Types.BIGINT);
            else ps.setLong(1, finalSubjectId);
            ps.setString(2, type);
            ps.setString(3, stem);
            ps.setString(4, finalOptionsJson);
            ps.setString(5, finalAnswerKey);
            ps.setInt(6, score);
            ps.setString(7, finalExplain.isBlank() ? null : finalExplain);
            return ps;
        }, kh);
        Number key = kh.getKey();
        return getQuestion(key == null ? 0L : key.longValue());
    }

    public static Map<String, Object> updateQuestion(long id, Map<String, Object> body) {
        require();
        if (getQuestion(id) == null) throw new IllegalArgumentException("题目不存在");
        String type = body.containsKey("type") ? normalizeType(str(body.get("type"))) : null;
        String stem = body.containsKey("stem") ? clip(str(body.get("stem")), 2000) : null;
        String optionsJson = body.containsKey("optionsJson")
                ? str(body.get("optionsJson"))
                : (body.containsKey("options_json") ? str(body.get("options_json")) : null);
        String answerKey = body.containsKey("answerKey")
                ? clip(str(body.get("answerKey")), 500)
                : (body.containsKey("answer_key") ? clip(str(body.get("answer_key")), 500) : null);
        Integer score = body.containsKey("score") ? toInt(body.get("score"), 5) : null;
        Long subjectId = body.containsKey("subjectId")
                ? toLong(body.get("subjectId"))
                : (body.containsKey("subject_id") ? toLong(body.get("subject_id")) : null);
        String explain = body.containsKey("explainText")
                ? clip(str(body.get("explainText")), 2000)
                : (body.containsKey("explain_text") ? clip(str(body.get("explain_text")), 2000) : null);
        List<String> sets = new ArrayList<>();
        List<Object> args = new ArrayList<>();
        if (type != null) {
            sets.add("type=?");
            args.add(type);
        }
        if (stem != null) {
            sets.add("stem=?");
            args.add(stem);
        }
        if (optionsJson != null) {
            sets.add("options_json=?");
            args.add(optionsJson);
        }
        if (answerKey != null) {
            sets.add("answer_key=?");
            args.add(answerKey);
        }
        if (score != null) {
            sets.add("score=?");
            args.add(score);
        }
        if (subjectId != null || body.containsKey("subjectId") || body.containsKey("subject_id")) {
            sets.add("subject_id=?");
            args.add(subjectId);
        }
        if (explain != null) {
            sets.add("explain_text=?");
            args.add(explain.isBlank() ? null : explain);
        }
        if (sets.isEmpty()) return getQuestion(id);
        args.add(id);
        db().update(
                "UPDATE exam_question SET " + String.join(",", sets) + " WHERE id=?",
                args.toArray());
        return getQuestion(id);
    }

    public static boolean deleteQuestion(long id) {
        require();
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM exam_paper_question WHERE question_id=?", Integer.class, id);
        if (n != null && n > 0) throw new IllegalStateException("题目已被试卷引用，无法删除");
        return db().update("DELETE FROM exam_question WHERE id=?", id) > 0;
    }

    private static String normalizeType(String type) {
        String t = type == null ? "" : type.trim().toLowerCase(Locale.ROOT);
        if (!Set.of("single", "multi", "judge", "subjective").contains(t)) {
            throw new IllegalArgumentException("题型须为 single/multi/judge/subjective");
        }
        return t;
    }

    // --- paper ---

    private static Map<String, Object> mapPaper(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("title", rs.getString("title"));
        m.put("durationMin", rs.getInt("duration_min"));
        m.put("status", rs.getString("status"));
        m.put("subjectId", rs.getObject("subject_id"));
        m.put("maxAttempts", rs.getInt("max_attempts"));
        if (hasGateCols()) {
            m.put("gateTicket", rs.getInt("gate_ticket") == 1);
            m.put("passScore", rs.getInt("pass_score"));
        } else {
            m.put("gateTicket", false);
            m.put("passScore", 60);
        }
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        return m;
    }

    public static Map<String, Object> getPaper(long id) {
        if (!ready()) return null;
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM exam_paper WHERE id=?", (rs, i) -> mapPaper(rs), id);
        return list.isEmpty() ? null : list.get(0);
    }

    public static Map<String, Object> pagePapersAdmin(int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        Integer total = db().queryForObject("SELECT COUNT(*) FROM exam_paper", Integer.class);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM exam_paper ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> mapPaper(rs),
                size, (page - 1) * size);
        return pageOut(list, total, page, size);
    }

    public static List<Map<String, Object>> listPublishedPapers() {
        require();
        return db().query(
                "SELECT * FROM exam_paper WHERE status='published' ORDER BY id DESC",
                (rs, i) -> mapPaper(rs));
    }

    public static Map<String, Object> createPaper(Map<String, Object> body) {
        require();
        String title = clip(str(body.get("title")), 200);
        if (title.isBlank()) throw new IllegalArgumentException("试卷标题不能为空");
        int durationMin = toInt(body.get("durationMin"), toInt(body.get("duration_min"), 0));
        String status = normalizePaperStatus(str(body.get("status")));
        if (status.isBlank()) status = "draft";
        Long subjectId = toLong(body.get("subjectId"));
        if (subjectId == null) subjectId = toLong(body.get("subject_id"));
        int maxAttempts = toInt(body.get("maxAttempts"), toInt(body.get("max_attempts"), 0));
        boolean gateTicket = boolFlag(body.get("gateTicket"), boolFlag(body.get("gate_ticket"), false));
        int passScore = toInt(body.get("passScore"), toInt(body.get("pass_score"), 60));
        KeyHolder kh = new GeneratedKeyHolder();
        Long finalSubjectId = subjectId;
        String finalStatus = status;
        boolean withGate = hasGateCols();
        db().update(con -> {
            if (withGate) {
                PreparedStatement ps = con.prepareStatement(
                        "INSERT INTO exam_paper (title,duration_min,status,subject_id,max_attempts,gate_ticket,pass_score) "
                                + "VALUES (?,?,?,?,?,?,?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setString(1, title);
                ps.setInt(2, durationMin);
                ps.setString(3, finalStatus);
                if (finalSubjectId == null) ps.setNull(4, java.sql.Types.BIGINT);
                else ps.setLong(4, finalSubjectId);
                ps.setInt(5, maxAttempts);
                ps.setInt(6, gateTicket ? 1 : 0);
                ps.setInt(7, passScore);
                return ps;
            }
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO exam_paper (title,duration_min,status,subject_id,max_attempts) VALUES (?,?,?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, title);
            ps.setInt(2, durationMin);
            ps.setString(3, finalStatus);
            if (finalSubjectId == null) ps.setNull(4, java.sql.Types.BIGINT);
            else ps.setLong(4, finalSubjectId);
            ps.setInt(5, maxAttempts);
            return ps;
        }, kh);
        Number key = kh.getKey();
        return getPaper(key == null ? 0L : key.longValue());
    }

    private static boolean boolFlag(Object o, boolean def) {
        if (o == null) return def;
        if (o instanceof Boolean b) return b;
        String s = String.valueOf(o).trim().toLowerCase(Locale.ROOT);
        if (s.isBlank()) return def;
        return s.equals("1") || s.equals("true") || s.equals("yes");
    }

    public static Map<String, Object> updatePaper(long id, Map<String, Object> body) {
        require();
        if (getPaper(id) == null) throw new IllegalArgumentException("试卷不存在");
        List<String> sets = new ArrayList<>();
        List<Object> args = new ArrayList<>();
        if (body.containsKey("title")) {
            sets.add("title=?");
            args.add(clip(str(body.get("title")), 200));
        }
        if (body.containsKey("durationMin") || body.containsKey("duration_min")) {
            sets.add("duration_min=?");
            args.add(toInt(body.get("durationMin"), toInt(body.get("duration_min"), 0)));
        }
        if (body.containsKey("status")) {
            sets.add("status=?");
            args.add(normalizePaperStatus(str(body.get("status"))));
        }
        if (body.containsKey("subjectId") || body.containsKey("subject_id")) {
            sets.add("subject_id=?");
            args.add(toLong(body.get("subjectId")) != null ? toLong(body.get("subjectId")) : toLong(body.get("subject_id")));
        }
        if (body.containsKey("maxAttempts") || body.containsKey("max_attempts")) {
            sets.add("max_attempts=?");
            args.add(toInt(body.get("maxAttempts"), toInt(body.get("max_attempts"), 0)));
        }
        if (hasGateCols()) {
            if (body.containsKey("gateTicket") || body.containsKey("gate_ticket")) {
                sets.add("gate_ticket=?");
                args.add(boolFlag(body.get("gateTicket"), boolFlag(body.get("gate_ticket"), false)) ? 1 : 0);
            }
            if (body.containsKey("passScore") || body.containsKey("pass_score")) {
                sets.add("pass_score=?");
                args.add(toInt(body.get("passScore"), toInt(body.get("pass_score"), 60)));
            }
        }
        if (sets.isEmpty()) return getPaper(id);
        args.add(id);
        db().update("UPDATE exam_paper SET " + String.join(",", sets) + " WHERE id=?", args.toArray());
        return getPaper(id);
    }

    public static boolean deletePaper(long id) {
        require();
        db().update("DELETE FROM exam_paper_question WHERE paper_id=?", id);
        db().update(
                "DELETE ea FROM exam_answer ea INNER JOIN exam_attempt a ON ea.attempt_id=a.id WHERE a.paper_id=?",
                id);
        db().update("DELETE FROM exam_attempt WHERE paper_id=?", id);
        return db().update("DELETE FROM exam_paper WHERE id=?", id) > 0;
    }

    private static String normalizePaperStatus(String status) {
        String s = status == null ? "" : status.trim().toLowerCase(Locale.ROOT);
        if (s.isBlank()) return "draft";
        if (!Set.of("draft", "published").contains(s)) {
            throw new IllegalArgumentException("状态须为 draft 或 published");
        }
        return s;
    }

    public static List<Map<String, Object>> listPaperQuestionsAdmin(long paperId) {
        require();
        return db().query(
                "SELECT q.*, pq.sort_no FROM exam_paper_question pq "
                        + "JOIN exam_question q ON q.id=pq.question_id "
                        + "WHERE pq.paper_id=? ORDER BY pq.sort_no, pq.id",
                (rs, i) -> {
                    Map<String, Object> m = mapQuestion(rs, true);
                    m.put("sortNo", rs.getInt("sort_no"));
                    return m;
                },
                paperId);
    }

    public static void setPaperQuestions(long paperId, List<Map<String, Object>> items) {
        require();
        if (getPaper(paperId) == null) throw new IllegalArgumentException("试卷不存在");
        db().update("DELETE FROM exam_paper_question WHERE paper_id=?", paperId);
        if (items == null || items.isEmpty()) return;
        int sort = 1;
        for (Map<String, Object> item : items) {
            long qid = Long.parseLong(String.valueOf(item.get("questionId") != null ? item.get("questionId") : item.get("question_id")));
            int sortNo = item.containsKey("sortNo") ? toInt(item.get("sortNo"), sort) : toInt(item.get("sort_no"), sort);
            if (getQuestion(qid) == null) throw new IllegalArgumentException("题目不存在: " + qid);
            db().update(
                    "INSERT INTO exam_paper_question (paper_id,question_id,sort_no) VALUES (?,?,?)",
                    paperId, qid, sortNo);
            sort++;
        }
    }

    // --- attempt ---

    private static Map<String, Object> mapAttempt(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("paperId", rs.getLong("paper_id"));
        m.put("username", rs.getString("username"));
        m.put("mode", rs.getString("mode"));
        m.put("status", rs.getString("status"));
        m.put("score", rs.getObject("score"));
        m.put("startedAt", fmt(rs.getTimestamp("started_at")));
        m.put("submittedAt", fmt(rs.getTimestamp("submitted_at")));
        return m;
    }

    public static Map<String, Object> getAttempt(long id) {
        if (!ready()) return null;
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM exam_attempt WHERE id=?", (rs, i) -> mapAttempt(rs), id);
        return list.isEmpty() ? null : list.get(0);
    }

    public static Map<String, Object> startAttempt(String username, long paperId, String mode) {
        require();
        Map<String, Object> paper = getPaper(paperId);
        if (paper == null) throw new IllegalArgumentException("试卷不存在");
        if (!"published".equals(String.valueOf(paper.get("status")))) {
            throw new IllegalStateException("试卷未发布");
        }
        String m = normalizeMode(mode);
        if ("practice".equals(m) && !practiceEnabled) {
            throw new IllegalStateException("练习模式未开通");
        }
        Map<String, Object> existing = findInProgress(username, paperId);
        if (existing != null) return existing;
        if ("exam".equals(m) && attemptLimitEnabled) {
            int max = ((Number) paper.get("maxAttempts")).intValue();
            if (max > 0) {
                Integer cnt = db().queryForObject(
                        "SELECT COUNT(*) FROM exam_attempt WHERE paper_id=? AND username=? "
                                + "AND mode='exam' AND status='submitted'",
                        Integer.class, paperId, username);
                if (cnt != null && cnt >= max) {
                    throw new IllegalStateException("已达限考次数");
                }
            }
        }
        Integer qn = db().queryForObject(
                "SELECT COUNT(*) FROM exam_paper_question WHERE paper_id=?", Integer.class, paperId);
        if (qn == null || qn == 0) throw new IllegalStateException("试卷未组题");
        KeyHolder kh = new GeneratedKeyHolder();
        String finalMode = m;
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO exam_attempt (paper_id,username,mode,status,started_at) VALUES (?,?,?,'in_progress',?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, paperId);
            ps.setString(2, username);
            ps.setString(3, finalMode);
            ps.setTimestamp(4, Timestamp.valueOf(LocalDateTime.now()));
            return ps;
        }, kh);
        Number key = kh.getKey();
        return getAttempt(key == null ? 0L : key.longValue());
    }

    private static Map<String, Object> findInProgress(String username, long paperId) {
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM exam_attempt WHERE paper_id=? AND username=? AND status='in_progress' "
                        + "ORDER BY id DESC LIMIT 1",
                (rs, i) -> mapAttempt(rs), paperId, username);
        return list.isEmpty() ? null : list.get(0);
    }

    private static String normalizeMode(String mode) {
        String m = mode == null ? "" : mode.trim().toLowerCase(Locale.ROOT);
        if (m.isBlank()) return "exam";
        if (!Set.of("exam", "practice").contains(m)) {
            throw new IllegalArgumentException("模式须为 exam 或 practice");
        }
        return m;
    }

    public static List<Map<String, Object>> listAttemptQuestions(long attemptId, String username, boolean afterSubmit) {
        require();
        Map<String, Object> attempt = getAttempt(attemptId);
        if (attempt == null) throw new IllegalArgumentException("答卷不存在");
        if (!username.equals(attempt.get("username"))) throw new IllegalStateException("无权访问");
        boolean submitted = "submitted".equals(String.valueOf(attempt.get("status")));
        if (!submitted && !afterSubmit) {
            // take: no answer key / explain
            return db().query(
                    "SELECT q.id, q.subject_id, q.type, q.stem, q.options_json, q.score, pq.sort_no "
                            + "FROM exam_paper_question pq "
                            + "JOIN exam_question q ON q.id=pq.question_id "
                            + "JOIN exam_attempt a ON a.paper_id=pq.paper_id "
                            + "WHERE a.id=? ORDER BY pq.sort_no, pq.id",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("id", rs.getLong("id"));
                        m.put("subjectId", rs.getObject("subject_id"));
                        m.put("type", rs.getString("type"));
                        m.put("stem", rs.getString("stem"));
                        m.put("optionsJson", rs.getString("options_json"));
                        m.put("score", rs.getInt("score"));
                        m.put("sortNo", rs.getInt("sort_no"));
                        return m;
                    },
                    attemptId);
        }
        // after submit: include scoring detail
        return db().query(
                "SELECT q.*, pq.sort_no, ea.answer_text, ea.is_correct, ea.score AS earned_score "
                        + "FROM exam_paper_question pq "
                        + "JOIN exam_question q ON q.id=pq.question_id "
                        + "JOIN exam_attempt a ON a.paper_id=pq.paper_id "
                        + "LEFT JOIN exam_answer ea ON ea.attempt_id=a.id AND ea.question_id=q.id "
                        + "WHERE a.id=? ORDER BY pq.sort_no, pq.id",
                (rs, i) -> {
                    Map<String, Object> m = mapQuestion(rs, true);
                    m.put("sortNo", rs.getInt("sort_no"));
                    m.put("userAnswer", rs.getString("answer_text"));
                    m.put("correct", rs.getObject("is_correct"));
                    m.put("earnedScore", rs.getObject("earned_score"));
                    if (explainEnabled && submitted) {
                        m.put("explainText", rs.getString("explain_text"));
                    }
                    return m;
                },
                attemptId);
    }

    public static Map<String, Object> submitAttempt(long attemptId, String username, List<Map<String, Object>> answers) {
        require();
        Map<String, Object> attempt = getAttempt(attemptId);
        if (attempt == null) throw new IllegalArgumentException("答卷不存在");
        if (!username.equals(attempt.get("username"))) throw new IllegalStateException("无权提交");
        if (!"in_progress".equals(String.valueOf(attempt.get("status")))) {
            throw new IllegalStateException("答卷已提交");
        }
        long paperId = ((Number) attempt.get("paperId")).longValue();
        Map<String, Object> paper = getPaper(paperId);
        if (paper == null) throw new IllegalArgumentException("试卷不存在");

        boolean timedOut = false;
        if (timerEnabled) {
            int durationMin = ((Number) paper.get("durationMin")).intValue();
            if (durationMin > 0) {
                List<Timestamp> starts = db().query(
                        "SELECT started_at FROM exam_attempt WHERE id=?",
                        (rs, i) -> rs.getTimestamp("started_at"), attemptId);
                if (!starts.isEmpty() && starts.get(0) != null) {
                    LocalDateTime deadline = starts.get(0).toLocalDateTime().plusMinutes(durationMin + 2L);
                    timedOut = LocalDateTime.now().isAfter(deadline);
                }
            }
        }

        Map<Long, String> answerMap = new HashMap<>();
        if (answers != null) {
            for (Map<String, Object> a : answers) {
                long qid = Long.parseLong(String.valueOf(
                        a.get("questionId") != null ? a.get("questionId") : a.get("question_id")));
                String ans = str(a.get("answer"));
                if (ans.isBlank()) ans = str(a.get("answerText"));
                if (ans.isBlank()) ans = str(a.get("answer_text"));
                answerMap.put(qid, ans);
            }
        }

        List<Map<String, Object>> questions = db().query(
                "SELECT q.* FROM exam_paper_question pq "
                        + "JOIN exam_question q ON q.id=pq.question_id WHERE pq.paper_id=?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("type", rs.getString("type"));
                    m.put("answerKey", rs.getString("answer_key"));
                    m.put("score", rs.getInt("score"));
                    return m;
                },
                paperId);

        int totalScore = 0;
        db().update("DELETE FROM exam_answer WHERE attempt_id=?", attemptId);
        for (Map<String, Object> q : questions) {
            long qid = ((Number) q.get("id")).longValue();
            String userAns = answerMap.getOrDefault(qid, "");
            int maxScore = ((Number) q.get("score")).intValue();
            int earned = scoreAnswer(String.valueOf(q.get("type")), String.valueOf(q.get("answerKey")), userAns, maxScore);
            boolean correct = earned == maxScore && maxScore > 0;
            totalScore += earned;
            db().update(
                    "INSERT INTO exam_answer (attempt_id,question_id,answer_text,is_correct,score) VALUES (?,?,?,?,?)",
                    attemptId, qid, clip(userAns, SUBJECTIVE_ANSWER_MAX), correct ? 1 : 0, earned);
            if (wrongbookEnabled && !correct) {
                upsertWrongbook(username, qid, paperId, attemptId);
            }
        }

        db().update(
                "UPDATE exam_attempt SET status='submitted', score=?, submitted_at=? WHERE id=?",
                totalScore, Timestamp.valueOf(LocalDateTime.now()), attemptId);

        Map<String, Object> out = new LinkedHashMap<>(getAttempt(attemptId));
        out.put("timedOut", timedOut);
        out.put("questions", listAttemptQuestions(attemptId, username, true));
        return out;
    }

    static int scoreAnswer(String type, String answerKey, String userAnswer, int maxScore) {
        if (answerKey == null || answerKey.isBlank()) return 0;
        String ua = userAnswer == null ? "" : userAnswer.trim();
        String key = answerKey.trim();
        switch (type) {
            case "single" -> {
                return ua.equals(key) ? maxScore : 0;
            }
            case "judge" -> {
                return ua.equalsIgnoreCase(key) ? maxScore : 0;
            }
            case "multi" -> {
                Set<String> expected = splitMulti(key);
                Set<String> actual = splitMulti(ua);
                return expected.equals(actual) ? maxScore : 0;
            }
            case "subjective" -> {
                String clipped = clip(ua, SUBJECTIVE_ANSWER_MAX);
                if (key.startsWith("re:")) {
                    String pattern = key.substring(3);
                    if (pattern.length() > REGEX_MAX) pattern = pattern.substring(0, REGEX_MAX);
                    try {
                        Pattern p = Pattern.compile(pattern, Pattern.CASE_INSENSITIVE);
                        return p.matcher(clipped).find() ? maxScore : 0;
                    } catch (PatternSyntaxException e) {
                        return 0;
                    }
                }
                String lower = clipped.toLowerCase(Locale.ROOT);
                String[] kws = key.split("[|,]");
                boolean any = false;
                for (String kw : kws) {
                    String k = kw.trim().toLowerCase(Locale.ROOT);
                    if (k.isEmpty()) continue;
                    any = true;
                    if (!lower.contains(k)) return 0;
                }
                return any ? maxScore : 0;
            }
            default -> {
                return 0;
            }
        }
    }

    private static Set<String> splitMulti(String s) {
        if (s == null || s.isBlank()) return Set.of();
        String[] parts = s.split(",");
        TreeSet<String> set = new TreeSet<>();
        for (String p : parts) {
            String t = p.trim();
            if (!t.isEmpty()) set.add(t);
        }
        return set;
    }

    public static Map<String, Object> pageMyAttempts(String username, int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM exam_attempt WHERE username=?", Integer.class, username);
        List<Map<String, Object>> list = db().query(
                "SELECT a.*, p.title AS paper_title FROM exam_attempt a "
                        + "JOIN exam_paper p ON p.id=a.paper_id "
                        + "WHERE a.username=? ORDER BY a.id DESC LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = mapAttempt(rs);
                    m.put("paperTitle", rs.getString("paper_title"));
                    return m;
                },
                username, size, (page - 1) * size);
        return pageOut(list, total, page, size);
    }

    public static Map<String, Object> pageAttemptsAdmin(int page, int size, Long paperId) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        String where = paperId == null ? "" : " WHERE a.paper_id=?";
        Object[] countArgs = paperId == null ? new Object[] {} : new Object[] {paperId};
        Integer total = db().queryForObject("SELECT COUNT(*) FROM exam_attempt a" + where, Integer.class, countArgs);
        List<Object> args = new ArrayList<>();
        if (paperId != null) args.add(paperId);
        args.add(size);
        args.add((page - 1) * size);
        List<Map<String, Object>> list = db().query(
                "SELECT a.*, p.title AS paper_title FROM exam_attempt a "
                        + "JOIN exam_paper p ON p.id=a.paper_id" + where
                        + " ORDER BY a.id DESC LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = mapAttempt(rs);
                    m.put("paperTitle", rs.getString("paper_title"));
                    return m;
                },
                args.toArray());
        return pageOut(list, total, page, size);
    }

    public static Map<String, Object> pageRank(long paperId, int page, int size) {
        require();
        if (!rankEnabled) throw new IllegalStateException("排行榜未开通");
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM exam_attempt WHERE paper_id=? AND mode='exam' AND status='submitted'",
                Integer.class, paperId);
        List<Map<String, Object>> list = db().query(
                "SELECT username, score, submitted_at FROM exam_attempt "
                        + "WHERE paper_id=? AND mode='exam' AND status='submitted' "
                        + "ORDER BY score DESC, submitted_at ASC LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("rank", (page - 1) * size + i + 1);
                    m.put("username", rs.getString("username"));
                    m.put("score", rs.getObject("score"));
                    m.put("submittedAt", fmt(rs.getTimestamp("submitted_at")));
                    try {
                        m.put("displayName", UserStore.displayName(rs.getString("username")));
                    } catch (Exception ignored) {
                    }
                    return m;
                },
                paperId, size, (page - 1) * size);
        Map<String, Object> out = pageOut(list, total, page, size);
        out.put("paperId", paperId);
        return out;
    }

    // --- wrongbook ---

    private static void upsertWrongbook(String username, long questionId, long paperId, long attemptId) {
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='exam_wrongbook'",
                    Integer.class);
            if (n == null || n == 0) return;
            Integer exists = db().queryForObject(
                    "SELECT COUNT(*) FROM exam_wrongbook WHERE username=? AND question_id=?",
                    Integer.class, username, questionId);
            if (exists != null && exists > 0) {
                db().update(
                        "UPDATE exam_wrongbook SET paper_id=?, attempt_id=? "
                                + "WHERE username=? AND question_id=?",
                        paperId, attemptId, username, questionId);
            } else {
                db().update(
                        "INSERT INTO exam_wrongbook (username,question_id,paper_id,attempt_id) VALUES (?,?,?,?)",
                        username, questionId, paperId, attemptId);
            }
        } catch (Exception ignored) {
        }
    }

    public static Map<String, Object> pageWrongbook(String username, int page, int size) {
        require();
        if (!wrongbookEnabled) throw new IllegalStateException("错题本未开通");
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM exam_wrongbook WHERE username=?", Integer.class, username);
        List<Map<String, Object>> list = db().query(
                "SELECT w.*, q.stem, q.type FROM exam_wrongbook w "
                        + "JOIN exam_question q ON q.id=w.question_id "
                        + "WHERE w.username=? ORDER BY w.id DESC LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("questionId", rs.getLong("question_id"));
                    m.put("paperId", rs.getObject("paper_id"));
                    m.put("attemptId", rs.getObject("attempt_id"));
                    m.put("stem", rs.getString("stem"));
                    m.put("type", rs.getString("type"));
                    m.put("createdAt", fmt(rs.getTimestamp("created_at")));
                    return m;
                },
                username, size, (page - 1) * size);
        return pageOut(list, total, page, size);
    }

    public static boolean deleteWrongbook(String username, long id) {
        require();
        if (!wrongbookEnabled) throw new IllegalStateException("错题本未开通");
        return db().update("DELETE FROM exam_wrongbook WHERE id=? AND username=?", id, username) > 0;
    }

    private static Map<String, Object> pageOut(List<Map<String, Object>> list, Integer total, int page, int size) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list == null ? List.of() : list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }
}
