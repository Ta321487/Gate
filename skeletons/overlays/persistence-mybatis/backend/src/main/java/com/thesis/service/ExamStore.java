package com.thesis.service;

import com.thesis.config.MybatisSupport;
import com.thesis.mapper.ExamMapper;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;

/**
 * 在线考试（C-01 / MyBatis）：题库、组卷、作答、自动判分。
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

    private ExamStore() {}

    private static ExamMapper mapper() {
        return MybatisSupport.mapper(ExamMapper.class);
    }

    public static void configure(
            boolean on,
            boolean practice,
            boolean explain,
            boolean timer,
            boolean attemptLimit,
            boolean rank,
            boolean wrongbook) {
        enabled = on;
        practiceEnabled = practice;
        explainEnabled = explain;
        timerEnabled = timer;
        attemptLimitEnabled = attemptLimit;
        rankEnabled = rank;
        wrongbookEnabled = wrongbook;
        requireBeforeTicket = false;
        tableReady = null;
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
        configure(on, practice, explain, timer, attemptLimit, rank, wrongbook);
        requireBeforeTicket = requireBeforeTicketFlag;
    }

    public static void assertTicketGatePassed(String username) {
        if (!requireBeforeTicket || !ready()) return;
        Integer gates;
        try {
            gates = mapper().countGatePapers();
        } catch (Exception e) {
            return;
        }
        if (gates == null || gates == 0) return;
        List<Map<String, Object>> rows = mapper().listGateAttempts(username);
        for (Map<String, Object> r : rows) {
            int sc = toInt(col(r, "score"), 0);
            int tot = toInt(col(r, "total_score", "totalScore"), 0);
            int pass = toInt(col(r, "pass_score", "passScore"), 60);
            if (pass <= 0) pass = 60;
            if (tot > 0 && sc * 100 >= pass * tot) return;
        }
        throw new IllegalStateException("请先通过安全准入考试后再提交申请");
    }

    public static boolean enabled() { return enabled; }
    public static boolean practiceEnabled() { return practiceEnabled; }
    public static boolean explainEnabled() { return explainEnabled; }
    public static boolean rankEnabled() { return rankEnabled; }
    public static boolean wrongbookEnabled() { return wrongbookEnabled; }

    public static boolean ready() {
        if (!enabled) return false;
        if (tableReady != null) return tableReady;
        try {
            Integer n = mapper().countExamQuestionTable();
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static void require() {
        if (!ready()) throw new IllegalStateException("考试功能暂不可用");
    }

    private static Object col(Map<String, Object> m, String... keys) {
        for (String k : keys) {
            if (m.containsKey(k)) return m.get(k);
            for (String mk : m.keySet()) {
                if (mk != null && mk.equalsIgnoreCase(k)) return m.get(mk);
            }
        }
        return null;
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

    private static Map<String, Object> pageOut(List<Map<String, Object>> list, Integer total, int page, int size) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    private static Map<String, Object> mapQuestion(Map<String, Object> raw, boolean admin) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", toLong(col(raw, "id")));
        m.put("subjectId", col(raw, "subject_id", "subjectId"));
        m.put("type", str(col(raw, "type")));
        m.put("stem", str(col(raw, "stem")));
        m.put("optionsJson", str(col(raw, "options_json", "optionsJson")));
        m.put("score", toInt(col(raw, "score"), 0));
        m.put("createdAt", fmt(col(raw, "created_at", "createdAt")));
        if (admin) {
            m.put("answerKey", str(col(raw, "answer_key", "answerKey")));
            if (explainEnabled) m.put("explainText", str(col(raw, "explain_text", "explainText")));
        }
        return m;
    }

    private static Map<String, Object> mapPaper(Map<String, Object> raw) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", toLong(col(raw, "id")));
        m.put("title", str(col(raw, "title")));
        m.put("durationMin", toInt(col(raw, "duration_min", "durationMin"), 0));
        m.put("status", str(col(raw, "status")));
        m.put("subjectId", col(raw, "subject_id", "subjectId"));
        m.put("maxAttempts", toInt(col(raw, "max_attempts", "maxAttempts"), 0));
        m.put("createdAt", fmt(col(raw, "created_at", "createdAt")));
        return m;
    }

    private static Map<String, Object> mapAttempt(Map<String, Object> raw) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", toLong(col(raw, "id")));
        m.put("paperId", toLong(col(raw, "paper_id", "paperId")));
        m.put("username", str(col(raw, "username")));
        m.put("mode", str(col(raw, "mode")));
        m.put("status", str(col(raw, "status")));
        m.put("score", toInt(col(raw, "score"), 0));
        m.put("totalScore", toInt(col(raw, "total_score", "totalScore"), 0));
        m.put("startedAt", fmt(col(raw, "started_at", "startedAt")));
        m.put("submittedAt", fmt(col(raw, "submitted_at", "submittedAt")));
        m.put("timedOut", toInt(col(raw, "timed_out", "timedOut"), 0) == 1);
        return m;
    }

    private static String normalizeType(String type) {
        String t = type == null ? "" : type.trim().toLowerCase(Locale.ROOT);
        if (!Set.of("single", "multi", "judge", "subjective").contains(t)) {
            throw new IllegalArgumentException("题型须为 single/multi/judge/subjective");
        }
        return t;
    }

    public static Map<String, Object> getQuestion(long id) {
        if (!ready()) return null;
        List<Map<String, Object>> list = mapper().selectQuestion(id);
        return list.isEmpty() ? null : mapQuestion(list.get(0), true);
    }

    public static Map<String, Object> pageQuestionsAdmin(int page, int size, Long subjectId) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        int total = mapper().countQuestions(subjectId);
        List<Map<String, Object>> raw = mapper().pageQuestions(subjectId, size, (page - 1) * size);
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> r : raw) list.add(mapQuestion(r, true));
        return pageOut(list, total, page, size);
    }

    public static Map<String, Object> createQuestion(Map<String, Object> body) {
        require();
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("type", normalizeType(str(body.get("type"))));
        String stem = clip(str(body.get("stem")), 2000);
        if (stem.isBlank()) throw new IllegalArgumentException("题干不能为空");
        row.put("stem", stem);
        String optionsJson = str(body.get("optionsJson"));
        if (optionsJson.isBlank()) optionsJson = str(body.get("options_json"));
        row.put("optionsJson", optionsJson);
        String answerKey = clip(str(body.get("answerKey")), 500);
        if (answerKey.isBlank()) answerKey = clip(str(body.get("answer_key")), 500);
        row.put("answerKey", answerKey);
        row.put("score", toInt(body.get("score"), 5));
        Long subjectId = toLong(body.get("subjectId"));
        if (subjectId == null) subjectId = toLong(body.get("subject_id"));
        row.put("subjectId", subjectId);
        String explain = clip(str(body.get("explainText")), 2000);
        if (explain.isBlank()) explain = clip(str(body.get("explain_text")), 2000);
        row.put("explainText", explain.isBlank() ? null : explain);
        mapper().insertQuestion(row);
        return getQuestion(toLong(row.get("id")) == null ? 0L : toLong(row.get("id")));
    }

    public static Map<String, Object> updateQuestion(long id, Map<String, Object> body) {
        require();
        if (getQuestion(id) == null) throw new IllegalArgumentException("题目不存在");
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", id);
        if (body.containsKey("type")) row.put("type", normalizeType(str(body.get("type"))));
        if (body.containsKey("stem")) row.put("stem", clip(str(body.get("stem")), 2000));
        if (body.containsKey("optionsJson") || body.containsKey("options_json")) {
            String v = body.containsKey("optionsJson") ? str(body.get("optionsJson")) : str(body.get("options_json"));
            row.put("optionsJson", v);
        }
        if (body.containsKey("answerKey") || body.containsKey("answer_key")) {
            String v = body.containsKey("answerKey")
                    ? clip(str(body.get("answerKey")), 500)
                    : clip(str(body.get("answer_key")), 500);
            row.put("answerKey", v);
        }
        if (body.containsKey("score")) row.put("score", toInt(body.get("score"), 5));
        if (body.containsKey("subjectId") || body.containsKey("subject_id")) {
            Long sid = body.containsKey("subjectId") ? toLong(body.get("subjectId")) : toLong(body.get("subject_id"));
            row.put("subjectId", sid);
            row.put("clearSubject", sid == null);
        }
        if (body.containsKey("explainText") || body.containsKey("explain_text")) {
            String v = body.containsKey("explainText")
                    ? clip(str(body.get("explainText")), 2000)
                    : clip(str(body.get("explain_text")), 2000);
            row.put("explainText", v.isBlank() ? null : v);
        }
        if (row.size() > 1) mapper().updateQuestion(row);
        return getQuestion(id);
    }

    public static boolean deleteQuestion(long id) {
        require();
        Integer n = mapper().countPaperRefs(id);
        if (n != null && n > 0) throw new IllegalStateException("题目已被试卷引用，无法删除");
        return mapper().deleteQuestion(id) > 0;
    }

    public static Map<String, Object> getPaper(long id) {
        if (!ready()) return null;
        List<Map<String, Object>> list = mapper().selectPaper(id);
        return list.isEmpty() ? null : mapPaper(list.get(0));
    }

    public static Map<String, Object> pagePapersAdmin(int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        Integer total = mapper().countPapers();
        List<Map<String, Object>> raw = mapper().pagePapers(size, (page - 1) * size);
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> r : raw) list.add(mapPaper(r));
        return pageOut(list, total, page, size);
    }

    public static List<Map<String, Object>> listPublishedPapers() {
        require();
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> r : mapper().listPublishedPapers()) list.add(mapPaper(r));
        return list;
    }

    public static Map<String, Object> createPaper(Map<String, Object> body) {
        require();
        Map<String, Object> row = new LinkedHashMap<>();
        String title = clip(str(body.get("title")), 200);
        if (title.isBlank()) throw new IllegalArgumentException("试卷标题不能为空");
        row.put("title", title);
        row.put("durationMin", toInt(body.get("durationMin"), toInt(body.get("duration_min"), 0)));
        String status = str(body.get("status"));
        if (status.isBlank()) status = "draft";
        row.put("status", status);
        Long subjectId = toLong(body.get("subjectId"));
        if (subjectId == null) subjectId = toLong(body.get("subject_id"));
        row.put("subjectId", subjectId);
        row.put("maxAttempts", toInt(body.get("maxAttempts"), toInt(body.get("max_attempts"), 0)));
        mapper().insertPaper(row);
        return getPaper(toLong(row.get("id")) == null ? 0L : toLong(row.get("id")));
    }

    public static Map<String, Object> updatePaper(long id, Map<String, Object> body) {
        require();
        if (getPaper(id) == null) throw new IllegalArgumentException("试卷不存在");
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", id);
        if (body.containsKey("title")) row.put("title", clip(str(body.get("title")), 200));
        if (body.containsKey("durationMin") || body.containsKey("duration_min")) {
            row.put("durationMin", body.containsKey("durationMin")
                    ? toInt(body.get("durationMin"), 0)
                    : toInt(body.get("duration_min"), 0));
        }
        if (body.containsKey("status")) row.put("status", str(body.get("status")));
        if (body.containsKey("subjectId") || body.containsKey("subject_id")) {
            Long sid = body.containsKey("subjectId") ? toLong(body.get("subjectId")) : toLong(body.get("subject_id"));
            row.put("subjectId", sid);
            row.put("clearSubject", sid == null);
        }
        if (body.containsKey("maxAttempts") || body.containsKey("max_attempts")) {
            row.put("maxAttempts", body.containsKey("maxAttempts")
                    ? toInt(body.get("maxAttempts"), 0)
                    : toInt(body.get("max_attempts"), 0));
        }
        if (row.size() > 1) mapper().updatePaper(row);
        return getPaper(id);
    }

    public static boolean deletePaper(long id) {
        require();
        mapper().deletePaperQuestions(id);
        return mapper().deletePaper(id) > 0;
    }

    public static List<Map<String, Object>> listPaperQuestionsAdmin(long paperId) {
        require();
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> r : mapper().listPaperQuestions(paperId)) {
            Map<String, Object> q = mapQuestion(r, true);
            q.put("sortNo", toInt(col(r, "sort_no", "sortNo"), 0));
            list.add(q);
        }
        return list;
    }

    public static void setPaperQuestions(long paperId, List<Map<String, Object>> items) {
        require();
        if (getPaper(paperId) == null) throw new IllegalArgumentException("试卷不存在");
        mapper().deletePaperQuestions(paperId);
        if (items == null) return;
        int i = 0;
        for (Map<String, Object> it : items) {
            Long qid = toLong(it.get("questionId"));
            if (qid == null) qid = toLong(it.get("question_id"));
            if (qid == null) qid = toLong(it.get("id"));
            if (qid == null) continue;
            int sort = toInt(it.get("sortNo"), toInt(it.get("sort_no"), ++i));
            mapper().insertPaperQuestion(paperId, qid, sort);
        }
    }

    public static Map<String, Object> getAttempt(long id) {
        if (!ready()) return null;
        List<Map<String, Object>> list = mapper().selectAttempt(id);
        return list.isEmpty() ? null : mapAttempt(list.get(0));
    }

    public static Map<String, Object> startAttempt(String username, long paperId, String mode) {
        require();
        Map<String, Object> paper = getPaper(paperId);
        if (paper == null || !"published".equals(str(paper.get("status")))) {
            throw new IllegalStateException("试卷未发布");
        }
        String m = "practice".equalsIgnoreCase(str(mode)) ? "practice" : "exam";
        if ("practice".equals(m) && !practiceEnabled) {
            throw new IllegalStateException("未开通刷题练习");
        }
        List<Map<String, Object>> prog = mapper().findInProgress(username, paperId);
        if (!prog.isEmpty()) return mapAttempt(prog.get(0));
        if ("exam".equals(m) && attemptLimitEnabled) {
            int max = toInt(paper.get("maxAttempts"), 0);
            if (max > 0) {
                Integer n = mapper().countSubmittedExam(username, paperId);
                if (n != null && n >= max) throw new IllegalStateException("已达考试次数上限");
            }
        }
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("paperId", paperId);
        row.put("username", username);
        row.put("mode", m);
        mapper().insertAttempt(row);
        return getAttempt(toLong(row.get("id")) == null ? 0L : toLong(row.get("id")));
    }

    public static List<Map<String, Object>> listAttemptQuestions(long attemptId, String username, boolean afterSubmit) {
        require();
        Map<String, Object> attempt = getAttempt(attemptId);
        if (attempt == null) throw new IllegalArgumentException("答卷不存在");
        if (!username.equals(str(attempt.get("username")))) {
            throw new IllegalStateException("无权查看该答卷");
        }
        boolean adminView = afterSubmit;
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> r : mapper().listAttemptQuestions(attemptId)) {
            Map<String, Object> q = mapQuestion(r, adminView);
            q.put("paperId", attempt.get("paperId"));
            list.add(q);
        }
        return list;
    }

    private static int scoreAnswer(String type, String key, String answer) {
        String t = type == null ? "" : type.toLowerCase(Locale.ROOT);
        String k = str(key);
        String a = str(answer);
        if ("single".equals(t)) {
            return k.equalsIgnoreCase(a) ? 1 : 0;
        }
        if ("judge".equals(t)) {
            return k.equalsIgnoreCase(a) ? 1 : 0;
        }
        if ("multi".equals(t)) {
            Set<String> ks = new TreeSet<>();
            for (String p : k.split("[,，]")) {
                String x = p.trim().toUpperCase(Locale.ROOT);
                if (!x.isEmpty()) ks.add(x);
            }
            Set<String> as = new TreeSet<>();
            for (String p : a.split("[,，]")) {
                String x = p.trim().toUpperCase(Locale.ROOT);
                if (!x.isEmpty()) as.add(x);
            }
            return ks.equals(as) ? 1 : 0;
        }
        if ("subjective".equals(t)) {
            String ans = clip(a, SUBJECTIVE_ANSWER_MAX).toLowerCase(Locale.ROOT);
            if (k.toLowerCase(Locale.ROOT).startsWith("re:")) {
                String pat = k.substring(3).trim();
                if (pat.length() > REGEX_MAX) return 0;
                try {
                    return Pattern.compile(pat, Pattern.CASE_INSENSITIVE).matcher(ans).find() ? 1 : 0;
                } catch (PatternSyntaxException e) {
                    return 0;
                }
            }
            String norm = k.replace("|", ",");
            for (String p : norm.split("[,，]")) {
                String x = p.trim().toLowerCase(Locale.ROOT);
                if (x.isEmpty()) continue;
                if (!ans.contains(x)) return 0;
            }
            return 1;
        }
        return 0;
    }

    public static Map<String, Object> submitAttempt(
            long attemptId, String username, List<Map<String, Object>> answers) {
        require();
        Map<String, Object> attempt = getAttempt(attemptId);
        if (attempt == null) throw new IllegalArgumentException("答卷不存在");
        if (!username.equals(str(attempt.get("username")))) {
            throw new IllegalStateException("无权提交该答卷");
        }
        if (!"in_progress".equals(str(attempt.get("status")))) {
            throw new IllegalStateException("答卷已提交");
        }
        Map<String, Object> paper = getPaper(toLong(attempt.get("paperId")));
        int timedOut = 0;
        if (timerEnabled && paper != null) {
            int dur = toInt(paper.get("durationMin"), 0);
            if (dur > 0 && attempt.get("startedAt") != null) {
                try {
                    LocalDateTime start = LocalDateTime.parse(str(attempt.get("startedAt")), FMT);
                    if (LocalDateTime.now().isAfter(start.plusMinutes(dur + 2L))) timedOut = 1;
                } catch (Exception ignored) {
                }
            }
        }
        Map<Long, String> ansMap = new HashMap<>();
        if (answers != null) {
            for (Map<String, Object> a : answers) {
                Long qid = toLong(a.get("questionId"));
                if (qid == null) qid = toLong(a.get("question_id"));
                if (qid == null) continue;
                String text = str(a.get("answerText"));
                if (text.isBlank()) text = str(a.get("answer_text"));
                ansMap.put(qid, text);
            }
        }
        List<Map<String, Object>> qs = mapper().listAttemptQuestions(attemptId);
        mapper().deleteAnswers(attemptId);
        int total = 0;
        int got = 0;
        for (Map<String, Object> raw : qs) {
            Map<String, Object> q = mapQuestion(raw, true);
            long qid = toLong(q.get("id"));
            int full = toInt(q.get("score"), 0);
            total += full;
            String userAns = ansMap.getOrDefault(qid, "");
            int ok = scoreAnswer(str(q.get("type")), str(q.get("answerKey")), userAns);
            int sc = ok == 1 ? full : 0;
            got += sc;
            mapper().insertAnswer(attemptId, qid, clip(userAns, SUBJECTIVE_ANSWER_MAX), ok, sc);
            if (wrongbookEnabled && ok == 0) {
                Integer has = mapper().countWrongbookTable();
                if (has != null && has > 0) {
                    mapper().upsertWrongbook(username, qid, clip(userAns, SUBJECTIVE_ANSWER_MAX));
                }
            }
        }
        mapper().submitAttempt(attemptId, got, total, timedOut);
        Map<String, Object> out = getAttempt(attemptId);
        out.put("questions", listAttemptQuestions(attemptId, username, true));
        return out;
    }

    public static Map<String, Object> pageMyAttempts(String username, int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        int total = mapper().countMyAttempts(username);
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> r : mapper().pageMyAttempts(username, size, (page - 1) * size)) {
            list.add(mapAttempt(r));
        }
        return pageOut(list, total, page, size);
    }

    public static Map<String, Object> pageAttemptsAdmin(int page, int size, Long paperId) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        int total = mapper().countAttemptsAdmin(paperId);
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> r : mapper().pageAttemptsAdmin(paperId, size, (page - 1) * size)) {
            list.add(mapAttempt(r));
        }
        return pageOut(list, total, page, size);
    }

    public static Map<String, Object> pageRank(long paperId, int page, int size) {
        require();
        if (!rankEnabled) throw new IllegalStateException("未开通成绩排行");
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        int total = mapper().countRank(paperId);
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> r : mapper().pageRank(paperId, size, (page - 1) * size)) {
            list.add(mapAttempt(r));
        }
        return pageOut(list, total, page, size);
    }

    public static Map<String, Object> pageWrongbook(String username, int page, int size) {
        require();
        if (!wrongbookEnabled) throw new IllegalStateException("未开通错题本");
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        int total = mapper().countWrongbook(username);
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> r : mapper().pageWrongbook(username, size, (page - 1) * size)) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id", toLong(col(r, "id")));
            m.put("questionId", toLong(col(r, "question_id", "questionId")));
            m.put("lastAnswer", str(col(r, "last_answer", "lastAnswer")));
            m.put("stem", str(col(r, "stem")));
            m.put("type", str(col(r, "type")));
            m.put("score", toInt(col(r, "score"), 0));
            m.put("createdAt", fmt(col(r, "created_at", "createdAt")));
            list.add(m);
        }
        return pageOut(list, total, page, size);
    }

    public static boolean deleteWrongbook(String username, long id) {
        require();
        if (!wrongbookEnabled) throw new IllegalStateException("未开通错题本");
        return mapper().deleteWrongbook(username, id) > 0;
    }
}

