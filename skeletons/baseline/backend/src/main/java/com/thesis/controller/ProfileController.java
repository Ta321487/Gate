package com.thesis.controller;

import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.PasswordHashes;
import com.thesis.common.R;
import com.thesis.service.ProfileFields;
import com.thesis.service.UserStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.*;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;

@RestController
@RequestMapping("/api/profile")
public class ProfileController {

    private UserStore.Profile requireUser(HttpSession session) {
        Object uid = session.getAttribute("uid");
        if (uid == null) throw new BizException(ErrorCode.UNAUTHORIZED, "未登录");
        UserStore.Profile p = UserStore.get(uid.toString());
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
        if (body.containsKey("phone")) p.phone = str(body.get("phone"));
        if (body.containsKey("extras") || hasExtraKeys(body)) {
            Map<String, String> merged = new LinkedHashMap<>(p.extras == null ? Map.of() : p.extras);
            merged.putAll(AuthController.extractExtras(body));
            p.extras = ProfileFields.filterExtras(merged);
        }

        boolean passwordChanged = false;
        String newPassword = str(body.get("newPassword"));
        if (newPassword.isBlank()) newPassword = str(body.get("password"));
        if (!newPassword.isBlank()) {
            String oldPassword = str(body.get("oldPassword"));
            String confirmPassword = str(body.get("confirmPassword"));
            if (oldPassword.isBlank()) {
                throw new BizException(ErrorCode.BAD_REQUEST, "请填写原密码");
            }
            if (!PasswordHashes.matches(oldPassword, p.password)) {
                throw new BizException(ErrorCode.BAD_REQUEST, "原密码不正确");
            }
            if (!newPassword.equals(confirmPassword)) {
                throw new BizException(ErrorCode.BAD_REQUEST, "两次输入的新密码不一致");
            }
            if (newPassword.equals(oldPassword)) {
                throw new BizException(ErrorCode.BAD_REQUEST, "新密码不能与原密码相同");
            }
            if (newPassword.length() < 6) {
                throw new BizException(ErrorCode.BAD_REQUEST, "新密码至少 6 位");
            }
            p.password = PasswordHashes.encode(newPassword);
            passwordChanged = true;
        }
        try {
            UserStore.saveProfile(p);
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
        Map<String, Object> out = new LinkedHashMap<>(p.toMap());
        if (passwordChanged) {
            // 改密后作废当前会话，须用新密码重新登录
            try {
                session.invalidate();
            } catch (IllegalStateException ignored) {
            }
            out.put("requireRelogin", true);
        }
        return R.ok(out);
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
        Path dir = Paths.get("uploads", "avatars");
        Files.createDirectories(dir);
        String name = p.username + "_" + System.currentTimeMillis() + "_" + Objects.requireNonNull(file.getOriginalFilename());
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
