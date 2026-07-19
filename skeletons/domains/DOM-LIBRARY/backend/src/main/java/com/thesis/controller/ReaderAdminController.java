package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.UserStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/** 读者账号管理：仅总管理员 */
@RestController
@RequestMapping("/api/admin/readers")
public class ReaderAdminController {

    @GetMapping
    public R<List<Map<String, Object>>> list(
            @RequestParam(required = false) String keyword,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        return R.ok(UserStore.listByRole("reader", keyword));
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
            Map<String, String> extras = com.thesis.controller.AuthController.extractExtras(body);
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
}
