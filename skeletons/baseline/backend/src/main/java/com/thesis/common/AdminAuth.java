package com.thesis.common;

import com.thesis.service.UserStore;
import jakarta.servlet.http.HttpSession;

/**
 * 管理端鉴权：role=admin 可办业务；super_admin=1 才可管账号/公告等配置。
 */
public final class AdminAuth {

    private AdminAuth() {}

    public static String requireLogin(HttpSession session) {
        Object uid = session.getAttribute("uid");
        if (uid == null) throw new BizException(ErrorCode.UNAUTHORIZED, "未登录");
        return uid.toString();
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
        boolean ok = p != null && p.superAdmin;
        session.setAttribute("superAdmin", ok);
        return ok;
    }
}
