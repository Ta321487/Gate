package com.thesis.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.config.MybatisSupport;
import com.thesis.mapper.ChoiceOptionMapper;

import java.util.ArrayList;
import java.util.List;

final class ChoiceOptionMb {

    private static final ObjectMapper JSON = new ObjectMapper();

    private ChoiceOptionMb() {}

    static String loadExam(long questionId) {
        return toJson(mapper().listExamOptionContents(questionId));
    }

    static String loadSurvey(long questionId) {
        return toJson(mapper().listSurveyOptionContents(questionId));
    }

    static void replaceExam(long questionId, String optionsJson) {
        mapper().deleteExamOptions(questionId);
        insert("exam", questionId, parse(optionsJson));
    }

    static void replaceSurvey(long questionId, String optionsJson) {
        mapper().deleteSurveyOptions(questionId);
        insert("survey", questionId, parse(optionsJson));
    }

    private static void insert(String kind, long questionId, List<String> items) {
        int no = 1;
        for (String text : items) {
            String label = String.valueOf((char) ('A' + no - 1));
            if ("exam".equals(kind)) {
                mapper().insertExamOption(questionId, no, label, text);
            } else {
                mapper().insertSurveyOption(questionId, no, label, text);
            }
            no++;
        }
    }

    private static ChoiceOptionMapper mapper() {
        return MybatisSupport.mapper(ChoiceOptionMapper.class);
    }

    private static String toJson(List<String> texts) {
        try {
            return JSON.writeValueAsString(texts == null ? List.of() : texts);
        } catch (Exception e) {
            return "[]";
        }
    }

    private static List<String> parse(String raw) {
        if (raw == null || raw.isBlank()) return List.of();
        try {
            List<String> list = JSON.readValue(raw.trim(), new TypeReference<>() {});
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
