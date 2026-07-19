package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.UserStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/** 业务用户 + 子管任命：仅总管理员（super_admin） */
@RestController
@RequestMapping("/api/admin/users")
public class UsersAdminController {

    @Value("${thesis.register-role:user}")
    private String userRole;

    @GetMapping
    public R<List<Map<String, Object>>> list(
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false, defaultValue = "users") String scope,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        return R.ok(UserStore.listManaged(userRole, scope, keyword));
    }

    @PutMapping("/{username}")
    public R<Map<String, Object>> update(
            @PathVariable String username,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            Boolean enabled = null;
            if (body.get("enabled") != null) {
                enabled = Boolean.parseBoolean(String.valueOf(body.get("enabled")));
            }
            String nick = body.containsKey("nickname") ? String.valueOf(body.get("nickname")) : null;
            String phone = body.containsKey("phone") ? String.valueOf(body.get("phone")) : null;
            Map<String, String> extras = AuthController.extractExtras(body);
            if (extras.isEmpty() && !body.containsKey("extras")) extras = null;
            return R.ok(UserStore.adminUpdate(username, nick, phone, enabled, extras).toMap());
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{username}/reset-password")
    public R<Void> resetPassword(
            @PathVariable String username,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            UserStore.adminResetPassword(username, String.valueOf(body.getOrDefault("password", "")));
            return R.ok(null);
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 任命子管（楼管 / 维修员 / 馆员等，由前端文案区分） */
    @PostMapping("/{username}/appoint")
    public R<Map<String, Object>> appoint(@PathVariable String username, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            return R.ok(UserStore.appointSubAdmin(username).toMap());
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 撤销子管，恢复为业务用户角色 */
    @PostMapping("/{username}/revoke")
    public R<Map<String, Object>> revoke(@PathVariable String username, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            return R.ok(UserStore.revokeSubAdmin(username, userRole).toMap());
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
