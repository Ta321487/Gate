package com.thesis.common;

import com.thesis.service.UserStore;
import jakarta.servlet.http.HttpSession;

/**
 * 管理端鉴权：role=admin 可办业务；super_admin=1 才可管账号/公告等配置。
 * 登录校验同时检查账号是否仍启用：停用则废会话并返回 ACCOUNT_DISABLED。
 */
public final class AdminAuth {

    public static final String DISABLED_MSG = "账号已停用，请联系管理员";

    private AdminAuth() {}

    public static String requireLogin(HttpSession session) {
        Object uid = session.getAttribute("uid");
        if (uid == null) throw new BizException(ErrorCode.UNAUTHORIZED, "未登录");
        String username = uid.toString();
        UserStore.Profile p = UserStore.get(username);
        if (p == null) {
            invalidateQuietly(session);
            throw new BizException(ErrorCode.UNAUTHORIZED, "未登录");
        }
        if (!p.enabled) {
            invalidateQuietly(session);
            throw new BizException(ErrorCode.ACCOUNT_DISABLED, DISABLED_MSG);
        }
        return username;
    }

    public static void requireAdmin(HttpSession session) {
        requireLogin(session);
        if (!"admin".equals(String.valueOf(session.getAttribute("role")))) {
            throw new BizException(ErrorCode.FORBIDDEN, "需要管理员权限");
        }
    }

    /** 总管：学生/读者管理、公告发布等 */
    public static void requireSuperAdmin(HttpSession session) {
        requireAdmin(session);
        if (!isSuperAdmin(session)) {
            throw new BizException(ErrorCode.FORBIDDEN, "需要总管理员权限");
        }
    }

    public static boolean isSuperAdmin(HttpSession session) {
        Object cached = session.getAttribute("superAdmin");
        if (cached instanceof Boolean b) return b;
        Object uid = session.getAttribute("uid");
        if (uid == null) return false;
        UserStore.Profile p = UserStore.get(uid.toString());
        boolean ok = p != null && p.superAdmin && p.enabled;
        session.setAttribute("superAdmin", ok);
        return ok;
    }

    private static void invalidateQuietly(HttpSession session) {
        try {
            session.invalidate();
        } catch (IllegalStateException ignored) {
            // already invalidated
        }
    }
}
