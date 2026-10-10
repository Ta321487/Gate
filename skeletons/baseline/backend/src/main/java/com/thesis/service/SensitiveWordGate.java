package com.thesis.service;

import java.util.ArrayList;
import java.util.List;

/**
 * 本地敏感词闸（C-03）：毕设级词表拦截，≠云审核。
 */
public final class SensitiveWordGate {

    private static boolean enabled = false;
    private static List<String> words = List.of("违禁", "广告引流", "加微信", "代刷");

    private SensitiveWordGate() {}

    public static void configure(boolean on) {
        enabled = on;
    }

    public static void configureWords(List<String> list) {
        if (list == null || list.isEmpty()) return;
        List<String> out = new ArrayList<>();
        for (String w : list) {
            if (w == null) continue;
            String t = w.trim();
            if (!t.isBlank()) out.add(t);
        }
        if (!out.isEmpty()) words = List.copyOf(out);
    }

    public static boolean enabled() {
        return enabled;
    }

    /** 命中则抛 IllegalStateException，文案给学生可见。 */
    public static void assertClean(String text) {
        if (!enabled || text == null || text.isBlank()) return;
        String raw = text;
        for (String w : words) {
            if (w != null && !w.isBlank() && raw.contains(w)) {
                throw new IllegalStateException("内容含不宜发布的用语，请修改后再提交");
            }
        }
    }
}
