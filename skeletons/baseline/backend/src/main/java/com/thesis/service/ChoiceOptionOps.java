package com.thesis.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.JdbcTemplate;

import java.util.ArrayList;
import java.util.List;

/** 试卷/问卷选项：子表一行一项，API 仍收发 optionsJson 数组。 */
final class ChoiceOptionOps {

    private static final ObjectMapper JSON = new ObjectMapper();

    private ChoiceOptionOps() {}

    static String loadJson(JdbcTemplate db, String table, long questionId) {
        try {
            List<String> texts = db.query(
                    "SELECT content FROM " + table + " WHERE question_id=? ORDER BY sort_no",
                    (rs, i) -> rs.getString("content"),
                    questionId);
            return JSON.writeValueAsString(texts == null ? List.of() : texts);
        } catch (Exception e) {
            return "[]";
        }
    }

    static void replace(JdbcTemplate db, String table, long questionId, String optionsJson) {
        db.update("DELETE FROM " + table + " WHERE question_id=?", questionId);
        List<String> items = parse(optionsJson);
        int no = 1;
        for (String text : items) {
            String label = String.valueOf((char) ('A' + no - 1));
            db.update(
                    "INSERT INTO " + table + " (question_id,sort_no,label,content) VALUES (?,?,?,?)",
                    questionId, no, label, text);
            no++;
        }
    }

    private static List<String> parse(String raw) {
        if (raw == null || raw.isBlank()) return List.of();
        String s = raw.trim();
        try {
            List<String> list = JSON.readValue(s, new TypeReference<>() {});
            List<String> out = new ArrayList<>();
            if (list == null) return out;
            for (String t : list) {
                if (t == null) continue;
                String u = t.trim();
                if (!u.isBlank()) out.add(u.length() > 500 ? u.substring(0, 500) : u);
            }
            return out;
        } catch (Exception e) {
            return List.of();
        }
    }
}
