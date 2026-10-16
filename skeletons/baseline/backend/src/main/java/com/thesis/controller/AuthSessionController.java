package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.AccountCancelStore;
import com.thesis.service.AuthSessionStore;
import com.thesis.service.InviteCodeStore;
import com.thesis.service.LoginLogStore;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/** 在线会话、登录记录、邀请码与注销审核。 */
@RestController
public class AuthSessionController {

    @GetMapping("/api/admin/online-sessions")
    public R<List<Map<String, Object>>> onlineSessions(HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        return R.ok(AuthSessionStore.listOnline());
    }

    @PostMapping("/api/admin/online-sessions/{sessionId}/kick")
    public R<Void> adminKick(@PathVariable String sessionId, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        AuthSessionStore.kick(sessionId);
        return R.ok();
    }

    @GetMapping("/api/auth/my-sessions")
    public R<List<Map<String, Object>>> mySessions(HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        List<Map<String, Object>> list = AuthSessionStore.listByUser(uid);
        String cur = session.getId();
        for (Map<String, Object> row : list) {
            row.put("current", cur.equals(String.valueOf(row.get("sessionId"))));
        }
        return R.ok(list);
    }

    @PostMapping("/api/auth/my-sessions/{sessionId}/kick")
    public R<Void> myKick(@PathVariable String sessionId, HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        if (session.getId().equals(sessionId)) {
            throw new BizException(ErrorCode.BAD_REQUEST, "不能踢出当前登录");
        }
        if (!AuthSessionStore.belongsTo(sessionId, uid)) {
            throw new BizException(ErrorCode.FORBIDDEN, "无权操作该会话");
        }
        AuthSessionStore.kick(sessionId);
        return R.ok();
    }

    @GetMapping("/api/auth/login-logs")
    public R<List<Map<String, Object>>> loginLogs(HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        return R.ok(LoginLogStore.listMine(uid, 20));
    }

    @GetMapping("/api/admin/invite-codes")
    public R<List<Map<String, Object>>> inviteList(HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        return R.ok(InviteCodeStore.listAll());
    }

    @PostMapping("/api/admin/invite-codes")
    public R<Map<String, Object>> inviteCreate(@RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            String code = str(body.get("code"));
            String label = str(body.get("label"));
            int maxUses = 0;
            Object mu = body.get("maxUses");
            if (mu == null) mu = body.get("max_uses");
            if (mu != null) {
                try {
                    maxUses = Integer.parseInt(String.valueOf(mu));
                } catch (NumberFormatException ignored) {
                }
            }
            return R.ok(InviteCodeStore.create(code, label, maxUses));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/api/admin/invite-codes/{code}/enabled")
    public R<Void> inviteEnabled(
            @PathVariable String code, @RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            boolean enabled = Boolean.parseBoolean(String.valueOf(body.getOrDefault("enabled", "true")));
            InviteCodeStore.setEnabled(code, enabled);
            return R.ok();
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/api/admin/cancel-requests")
    public R<List<Map<String, Object>>> cancelList(
            @RequestParam(required = false, defaultValue = "pending") String status, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        return R.ok(AccountCancelStore.list(status));
    }

    @PostMapping("/api/admin/cancel-requests/{id}/review")
    public R<Map<String, Object>> cancelReview(
            @PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            boolean approve = Boolean.parseBoolean(String.valueOf(body.getOrDefault("approve", "false")));
            String note = str(body.get("adminNote"));
            if (note.isBlank()) note = str(body.get("note"));
            return R.ok(AccountCancelStore.review(id, approve, note));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    static String clientIp(HttpServletRequest request) {
        String xff = request.getHeader("X-Forwarded-For");
        if (xff != null && !xff.isBlank()) {
            int comma = xff.indexOf(',');
            return (comma > 0 ? xff.substring(0, comma) : xff).trim();
        }
        return request.getRemoteAddr() == null ? "" : request.getRemoteAddr();
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }
}
