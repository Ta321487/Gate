package com.thesis.common;

import jakarta.servlet.http.HttpSession;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * 门户游客：未登录时列表截断条数（有 session uid 则不截断）。
 */
@Component
public class GuestTeaser {

    private static int limit = 3;
    private static boolean enabled = false;

    @Value("${thesis.guest-teaser-limit:3}")
    public void setLimit(int n) {
        limit = Math.max(1, n);
    }

    @Value("${thesis.portal-guest-browse:false}")
    public void setEnabled(boolean on) {
        enabled = on;
    }

    public static boolean guestBrowseEnabled() {
        return enabled;
    }

    public static int teaserLimit() {
        return limit;
    }

    public static boolean loggedIn(HttpSession session) {
        return session != null && session.getAttribute("uid") != null;
    }

    /** 未登录且开启游客逛时，把请求 size 压到 teaserLimit，page 固定 1。 */
    public static int clampSize(HttpSession session, int size) {
        if (loggedIn(session) || !enabled) {
            return Math.max(1, Math.min(size, 100));
        }
        return Math.min(Math.max(1, size), limit);
    }

    public static int clampPage(HttpSession session, int page) {
        if (loggedIn(session) || !enabled) {
            return Math.max(1, page);
        }
        return 1;
    }
}
