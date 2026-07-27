package com.thesis.service;

import com.thesis.config.MybatisSupport;
import com.thesis.mapper.SurveyMapper;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

public class SurveyStore {
    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static boolean enabled;
    private static Boolean tableReady;

    private SurveyStore() {}
    private static SurveyMapper mapper() { return MybatisSupport.mapper(SurveyMapper.class); }

    public static void configure(boolean on) { enabled = on; tableReady = null; }
    public static boolean enabled() { return enabled; }

    public static boolean ready() {
        if (!enabled) return false;
        if (tableReady != null) return tableReady;
        try {
            Integer n = mapper().countTable();
            tableReady = n != null && n > 0;
        } catch (Exception e) { tableReady = false; }
        return tableReady;
    }

    private static void require() { if (!ready()) throw new IllegalStateException("问卷功能暂不可用"); }
    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        String s = String.valueOf(o); return s.isBlank() ? null : s;
    }
    private static String clip(String s, int max) {
        if (s == null) return "";
        String t = s.trim(); return t.length() <= max ? t : t.substring(0, max);
    }
    private static String str(Object o) { return o == null ? "" : String.valueOf(o).trim(); }
    private static Long toLong(Object o) {
        if (o == null || String.valueOf(o).isBlank()) return null;
        return Long.parseLong(String.valueOf(o));
    }
    private static int toInt(Object o, int def) {
        if (o == null || String.valueOf(o).isBlank()) return def;
        return Integer.parseInt(String.valueOf(o));
    }
    private static Object col(Map<String, Object> m, String... keys) {
        for (String k : keys) {
            if (m.containsKey(k)) return m.get(k);
            for (String mk : m.keySet()) if (mk != null && mk.equalsIgnoreCase(k)) return m.get(mk);
        }
        return null;
    }
    private static Map<String, Object> pageOut(List<?> list, Integer total, int page, int size) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list); out.put("total", total == null ? 0 : total);
        out.put("page", page); out.put("size", size); return out;
    }
    private static String normalizeType(String type) {
        String t = type == null ? "" : type.trim().toLowerCase(Locale.ROOT);
        if (!Set.of("single", "multi", "text").contains(t)) throw new IllegalArgumentException("题型须为 single/multi/text");
        return t;
    }
    private static Map<String, Object> mapForm(Map<String, Object> raw) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", toLong(col(raw, "id"))); m.put("title", str(col(raw, "title")));
        m.put("author", str(col(raw, "author"))); m.put("isbn", str(col(raw, "isbn")));
        m.put("categoryId", col(raw, "category_id", "categoryId"));
        m.put("stock", toInt(col(raw, "stock"), 0)); m.put("status", str(col(raw, "status")));
        return m;
    }
    private static Map<String, Object> mapQuestion(Map<String, Object> raw) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", toLong(col(raw, "id"))); m.put("formId", toLong(col(raw, "form_id", "formId")));
        m.put("type", str(col(raw, "type"))); m.put("stem", str(col(raw, "stem")));
        m.put("optionsJson", str(col(raw, "options_json", "optionsJson")));
        m.put("sortNo", toInt(col(raw, "sort_no", "sortNo"), 0));
        m.put("required", toInt(col(raw, "required"), 1) == 1);
        return m;
    }

    public static List<Map<String, Object>> listOpenForms() {
        require();
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> r : mapper().listOpenForms()) out.add(mapForm(r));
        return out;
    }
    public static Map<String, Object> getForm(long id) {
        if (!ready()) return null;
        List<Map<String, Object>> list = mapper().getForm(id);
        return list.isEmpty() ? null : mapForm(list.get(0));
    }
    public static List<Map<String, Object>> listQuestions(long formId) {
        require();
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> r : mapper().listQuestions(formId)) out.add(mapQuestion(r));
        return out;
    }
    public static Map<String, Object> pageQuestionsAdmin(long formId, int page, int size) {
        require(); if (page < 1) page = 1; if (size < 1) size = 20;
        int total = mapper().countQuestions(formId);
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> r : mapper().pageQuestions(formId, size, (page - 1) * size)) out.add(mapQuestion(r));
        return pageOut(out, total, page, size);
    }
    public static Map<String, Object> createQuestion(Map<String, Object> body) {
        require();
        long formId = toLong(body.get("formId")) != null ? toLong(body.get("formId")) : toLong(body.get("form_id"));
        if (formId <= 0 || getForm(formId) == null) throw new IllegalArgumentException("问卷不存在");
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("formId", formId);
        row.put("type", normalizeType(str(body.get("type"))));
        String stem = clip(str(body.get("stem")), 2000);
        if (stem.isBlank()) throw new IllegalArgumentException("题干不能为空");
        row.put("stem", stem);
        String options = str(body.get("optionsJson")); if (options.isBlank()) options = str(body.get("options_json"));
        row.put("optionsJson", options);
        row.put("sortNo", toInt(body.get("sortNo"), toInt(body.get("sort_no"), 0)));
        boolean required = !"0".equals(str(body.get("required"))) && !"false".equalsIgnoreCase(str(body.get("required")));
        row.put("required", required ? 1 : 0);
        mapper().insertQuestion(row);
        long id = toLong(row.get("id")) == null ? 0L : toLong(row.get("id"));
        List<Map<String, Object>> one = mapper().getQuestion(id);
        return one.isEmpty() ? Map.of() : mapQuestion(one.get(0));
    }
    public static boolean deleteQuestion(long id) { require(); return mapper().deleteQuestion(id) > 0; }

    public static Map<String, Object> submit(String username, long formId, List<Map<String, Object>> answers) {
        require();
        Map<String, Object> form = getForm(formId);
        if (form == null || !"available".equals(str(form.get("status")))) throw new IllegalStateException("问卷未开放");
        Integer dup = mapper().countUserResponse(formId, username);
        if (dup != null && dup > 0) throw new IllegalStateException("您已填写过该问卷");
        List<Map<String, Object>> qs = listQuestions(formId);
        Map<Long, String> ansMap = new HashMap<>();
        if (answers != null) {
            for (Map<String, Object> a : answers) {
                Long qid = toLong(a.get("questionId")); if (qid == null) qid = toLong(a.get("question_id"));
                if (qid == null) continue;
                String text = str(a.get("answerText")); if (text.isBlank()) text = str(a.get("answer_text"));
                ansMap.put(qid, clip(text, 2000));
            }
        }
        for (Map<String, Object> q : qs) {
            if (Boolean.TRUE.equals(q.get("required"))) {
                String v = ansMap.getOrDefault(toLong(q.get("id")), "");
                if (v.isBlank()) throw new IllegalArgumentException("请完成必填题：" + q.get("stem"));
            }
        }
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("formId", formId); row.put("username", username);
        mapper().insertResponse(row);
        long responseId = toLong(row.get("id")) == null ? 0L : toLong(row.get("id"));
        for (Map<String, Object> q : qs) {
            long qid = toLong(q.get("id"));
            mapper().insertAnswer(responseId, qid, ansMap.getOrDefault(qid, ""));
        }
        return getResponse(responseId);
    }
    public static Map<String, Object> getResponse(long id) {
        List<Map<String, Object>> list = mapper().getResponse(id);
        if (list.isEmpty()) return null;
        Map<String, Object> raw = list.get(0);
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", toLong(col(raw, "id"))); m.put("formId", toLong(col(raw, "form_id", "formId")));
        m.put("username", str(col(raw, "username"))); m.put("submittedAt", fmt(col(raw, "submitted_at", "submittedAt")));
        return m;
    }
    public static Map<String, Object> pageMine(String username, int page, int size) {
        require(); if (page < 1) page = 1; if (size < 1) size = 10;
        int total = mapper().countMine(username);
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> r : mapper().pageMine(username, size, (page - 1) * size)) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id", toLong(col(r, "id"))); m.put("formId", toLong(col(r, "form_id", "formId")));
            m.put("formTitle", str(col(r, "form_title", "formTitle")));
            m.put("submittedAt", fmt(col(r, "submitted_at", "submittedAt")));
            out.add(m);
        }
        return pageOut(out, total, page, size);
    }
    public static Map<String, Object> pageResponsesAdmin(long formId, int page, int size) {
        require(); if (page < 1) page = 1; if (size < 1) size = 10;
        int total = mapper().countResponses(formId);
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> r : mapper().pageResponses(formId, size, (page - 1) * size)) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id", toLong(col(r, "id"))); m.put("formId", toLong(col(r, "form_id", "formId")));
            m.put("username", str(col(r, "username"))); m.put("submittedAt", fmt(col(r, "submitted_at", "submittedAt")));
            out.add(m);
        }
        return pageOut(out, total, page, size);
    }
    public static List<Map<String, Object>> stats(long formId) {
        require();
        List<Map<String, Object>> qs = listQuestions(formId);
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> q : qs) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("questionId", q.get("id")); row.put("stem", q.get("stem")); row.put("type", q.get("type"));
            String type = str(q.get("type"));
            if ("text".equals(type)) {
                Integer n = mapper().countFilled(toLong(q.get("id")));
                row.put("filledCount", n == null ? 0 : n); row.put("options", List.of());
            } else {
                List<String> opts = parseOpts(str(q.get("optionsJson")));
                List<Map<String, Object>> counts = new ArrayList<>();
                long qid = toLong(q.get("id"));
                for (int i = 0; i < opts.size(); i++) {
                    String letter = String.valueOf((char) ('A' + i));
                    String label = opts.get(i);
                    Integer n = mapper().countOpt(qid, letter, letter + ",%", "%," + letter, "%," + letter + ",%");
                    Integer n2 = mapper().countOpt(qid, label, label + ",%", "%," + label, "%," + label + ",%");
                    Map<String, Object> oc = new LinkedHashMap<>();
                    oc.put("key", letter); oc.put("label", label);
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
        } catch (Exception e) { return List.of(); }
    }
}
