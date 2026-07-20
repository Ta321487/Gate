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

    /** 门户业务用户可否任命为岗位；缺省 false，须 yml/bake 显式打开 */
    @Value("${thesis.allow-appoint-from-users:false}")
    private boolean allowAppointFromUsers;

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
            boolean protectLast = !allowAppointFromUsers;
            return R.ok(UserStore.adminUpdate(username, nick, phone, enabled, extras, protectLast).toMap());
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

    /** 任命岗位（子管理 clerk / 业务员工 worker）；仅总管 */
    @PostMapping("/{username}/appoint")
    public R<Map<String, Object>> appoint(
            @PathVariable String username,
            @RequestBody(required = false) Map<String, Object> body,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        if (!allowAppointFromUsers) {
            throw new BizException(ErrorCode.BAD_REQUEST, "本系统不支持将业务用户任命为岗位，请使用预置岗位账号");
        }
        try {
            Map<String, Object> b = body == null ? Map.of() : body;
            String staffPost = String.valueOf(b.getOrDefault("staffPost", b.getOrDefault("staff_post", "")));
            String staffKind = String.valueOf(b.getOrDefault("staffKind", b.getOrDefault("staff_kind", "")));
            if ("null".equals(staffPost)) staffPost = "";
            if ("null".equals(staffKind)) staffKind = "";
            if (staffPost.isBlank() && staffKind.isBlank()) {
                return R.ok(UserStore.appointSubAdmin(username).toMap());
            }
            return R.ok(UserStore.appointSubAdmin(username, staffPost, staffKind).toMap());
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 撤销子管，恢复为业务用户角色 */
    @PostMapping("/{username}/revoke")
    public R<Map<String, Object>> revoke(@PathVariable String username, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            // 禁任命域：保护该岗最后一个账号，避免撤光后无法补岗
            boolean protectLast = !allowAppointFromUsers;
            return R.ok(UserStore.revokeSubAdmin(username, userRole, protectLast).toMap());
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
