package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.PasswordHashes;
import com.thesis.common.R;
import com.thesis.config.UploadStorage;
import com.thesis.service.AccountCancelStore;
import com.thesis.service.AuthSessionStore;
import com.thesis.service.ProfileFields;
import com.thesis.service.UserStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.LinkedHashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/profile")
public class ProfileController {

    private UserStore.Profile requireUser(HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        UserStore.Profile p = UserStore.get(uid);
        if (p == null) throw new BizException(ErrorCode.UNAUTHORIZED, "用户不存在");
        return p;
    }

    @GetMapping
    public R<Map<String, Object>> get(HttpSession session) {
        return R.ok(requireUser(session).toMap());
    }

    @PutMapping
    public R<Map<String, Object>> update(@RequestBody Map<String, Object> body, HttpSession session) {
        UserStore.Profile p = requireUser(session);
        if (!p.profileEditable) {
            throw new BizException(ErrorCode.FORBIDDEN, "顶级管理员不提供个人资料修改");
        }
        if (body.containsKey("nickname")) p.nickname = str(body.get("nickname"));
        // 手机号/邮箱改绑走 /change-contact；此处禁止静默改 phone
        if (body.containsKey("phone")) {
            String next = str(body.get("phone"));
            String cur = p.phone == null ? "" : p.phone.trim();
            if (!next.equals(cur)) {
                throw new BizException(ErrorCode.BAD_REQUEST, "修改手机号请使用改绑入口并填写验证码");
            }
        }
        if (body.containsKey("extras") || hasExtraKeys(body)) {
            Map<String, String> merged = new LinkedHashMap<>(p.extras == null ? Map.of() : p.extras);
            Map<String, String> incoming = AuthController.extractExtras(body);
            String oldEmail = p.extras == null ? "" : String.valueOf(p.extras.getOrDefault("email", "")).trim();
            String newEmail = incoming.getOrDefault("email", oldEmail);
            if (newEmail == null) newEmail = "";
            if (!oldEmail.equals(newEmail.trim()) && body.containsKey("extras")) {
                // 扁平/extras 里改邮箱：拒，走改绑
                if (incoming.containsKey("email") && !oldEmail.equals(incoming.get("email").trim())) {
                    throw new BizException(ErrorCode.BAD_REQUEST, "修改邮箱请使用改绑入口并填写验证码");
                }
            }
            merged.putAll(incoming);
            if (incoming.containsKey("email") && !oldEmail.equals(String.valueOf(incoming.get("email")).trim())) {
                throw new BizException(ErrorCode.BAD_REQUEST, "修改邮箱请使用改绑入口并填写验证码");
            }
            p.extras = ProfileFields.filterExtras(merged);
        }
        if (body.containsKey("realNameAcked") || body.containsKey("real_name_acked")) {
            Object raw = body.containsKey("realNameAcked") ? body.get("realNameAcked") : body.get("real_name_acked");
            p.realNameAcked = Boolean.parseBoolean(String.valueOf(raw));
        }

        boolean passwordChanged = false;
        String newPassword = str(body.get("newPassword"));
        if (newPassword.isBlank()) newPassword = str(body.get("password"));
        String oldPassword = str(body.get("oldPassword"));
        String confirmPassword = str(body.get("confirmPassword"));
        if (!newPassword.isBlank()) {
            boolean forced = UserStore.effectiveMustChange(p);
            if (!forced && oldPassword.isBlank()) {
                throw new BizException(ErrorCode.BAD_REQUEST, "请填写原密码");
            }
            if (!forced && !PasswordHashes.matches(oldPassword, p.password)) {
                throw new BizException(ErrorCode.BAD_REQUEST, "原密码不正确");
            }
            if (!newPassword.equals(confirmPassword)) {
                throw new BizException(ErrorCode.BAD_REQUEST, "两次输入的新密码不一致");
            }
            if (!oldPassword.isBlank() && newPassword.equals(oldPassword)) {
                throw new BizException(ErrorCode.BAD_REQUEST, "新密码不能与原密码相同");
            }
        }
        try {
            UserStore.saveProfile(p);
            if (body.containsKey("orgId")) {
                Object rawOrg = body.get("orgId");
                Long orgId = rawOrg == null || String.valueOf(rawOrg).isBlank()
                        || "null".equals(String.valueOf(rawOrg))
                        ? null
                        : Long.parseLong(String.valueOf(rawOrg).trim());
                UserStore.updateOrgId(p.username, orgId);
            }
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
        if (!newPassword.isBlank()) {
            try {
                UserStore.forceChangePassword(p.username, newPassword);
            } catch (IllegalArgumentException e) {
                throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
            }
            passwordChanged = true;
        }
        String sq = str(body.get("securityQuestion"));
        String sa = str(body.get("securityAnswer"));
        if (!sq.isBlank() && !sa.isBlank()) {
            try {
                UserStore.setSecurityQuestion(p.username, sq, sa);
            } catch (IllegalArgumentException | IllegalStateException e) {
                throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
            }
        }
        p = UserStore.get(p.username);
        Map<String, Object> out = new LinkedHashMap<>(p == null ? Map.of() : p.toMap());
        if (passwordChanged) {
            try {
                AuthSessionStore.invalidate(session.getId());
            } catch (Exception ignored) {
            }
            try {
                session.invalidate();
            } catch (IllegalStateException ignored) {
            }
            out.put("requireRelogin", true);
        }
        return R.ok(out);
    }

    @PostMapping("/change-contact")
    public R<Map<String, Object>> changeContact(@RequestBody Map<String, Object> body, HttpSession session) {
        UserStore.Profile p = requireUser(session);
        if (!p.profileEditable) {
            throw new BizException(ErrorCode.FORBIDDEN, "顶级管理员不提供资料修改");
        }
        AuthController.verifyCaptchaForProfile(body, session);
        String field = str(body.get("field"));
        String value = str(body.get("value"));
        if (value.isBlank()) value = str(body.get("newValue"));
        try {
            UserStore.changeContact(p.username, field, value);
            return R.ok(UserStore.get(p.username).toMap());
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/cancel-request")
    public R<Map<String, Object>> cancelRequest(@RequestBody Map<String, Object> body, HttpSession session) {
        UserStore.Profile p = requireUser(session);
        try {
            return R.ok(AccountCancelStore.submit(p.username, str(body.get("reason"))));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/real-name-ack")
    public R<Map<String, Object>> realNameAck(@RequestBody Map<String, Object> body, HttpSession session) {
        UserStore.Profile p = requireUser(session);
        boolean acked = Boolean.parseBoolean(String.valueOf(body.getOrDefault("acked", body.getOrDefault("realNameAcked", "true"))));
        try {
            UserStore.setRealNameAcked(p.username, acked);
            return R.ok(UserStore.get(p.username).toMap());
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/avatar")
    public R<Map<String, Object>> avatar(@RequestParam("file") MultipartFile file, HttpSession session) throws IOException {
        UserStore.Profile p = requireUser(session);
        if (!p.profileEditable) {
            throw new BizException(ErrorCode.FORBIDDEN, "顶级管理员不提供头像修改");
        }
        if (file.isEmpty()) throw new BizException(ErrorCode.BAD_REQUEST, "文件为空");
        String contentType = file.getContentType() == null ? "" : file.getContentType();
        if (!contentType.startsWith("image/")) {
            throw new BizException(ErrorCode.BAD_REQUEST, "仅支持图片");
        }
        Path dir = UploadStorage.avatars();
        String name = UploadStorage.safeStoredName(file.getOriginalFilename());
        Path dest = dir.resolve(name);
        Files.copy(file.getInputStream(), dest, StandardCopyOption.REPLACE_EXISTING);
        p.avatarUrl = "/uploads/avatars/" + name;
        UserStore.saveProfile(p);
        return R.ok(p.toMap());
    }

    private static boolean hasExtraKeys(Map<String, Object> body) {
        for (Map<String, Object> f : ProfileFields.all()) {
            String storage = f.get("storage") == null ? "json" : String.valueOf(f.get("storage"));
            if ("phone".equals(storage)) continue;
            String key = String.valueOf(f.get("key"));
            if (body.containsKey(key)) return true;
        }
        return false;
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }
}
