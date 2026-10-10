package com.thesis.service;

import java.util.LinkedHashSet;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 跟帖/评论 @提醒（C-03）：解析 @登录名 发站内信，浅一层。
 */
public final class MentionNotify {

    private static final Pattern AT = Pattern.compile("@([A-Za-z0-9_\\u4e00-\\u9fff]{2,32})");
    private static boolean enabled = false;

    private MentionNotify() {}

    public static void configure(boolean on) {
        enabled = on;
    }

    public static boolean enabled() {
        return enabled;
    }

    public static void notifyFromText(String fromUser, String text, String refType, long refId, String subjectHint) {
        if (!enabled || text == null || text.isBlank()) return;
        String from = fromUser == null ? "" : fromUser.trim();
        Set<String> names = new LinkedHashSet<>();
        Matcher m = AT.matcher(text);
        while (m.find()) {
            String u = m.group(1);
            if (u != null && !u.isBlank() && !u.equals(from)) names.add(u.trim());
        }
        if (names.isEmpty()) return;
        String title = "有人提到了你";
        String body = (from.isBlank() ? "有用户" : from) + "在"
                + (subjectHint == null || subjectHint.isBlank() ? "讨论" : subjectHint)
                + "中提到了你。";
        for (String u : names) {
            try {
                if (UserStore.get(u) == null) continue;
                MessageStore.send(u, title, body, refType == null ? "ticket" : refType, Long.valueOf(refId));
            } catch (Exception ignored) {
            }
        }
    }
}
