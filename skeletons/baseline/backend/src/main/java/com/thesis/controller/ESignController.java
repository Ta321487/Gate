package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.ESignStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/e-sign")
public class ESignController {

    private static void requireSign() {
        if (!ESignStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通签章功能");
        }
    }

    @GetMapping("/mine")
    public R<Map<String, Object>> mine(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        requireSign();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(ESignStore.pageMine(uid, page, size));
    }

    @PostMapping("/submit")
    public R<Map<String, Object>> submit(@RequestBody Map<String, Object> body, HttpSession session) {
        requireSign();
        String uid = AdminAuth.requireLogin(session);
        try {
            return R.ok(ESignStore.submitFromBody(uid, body == null ? Map.of() : body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/admin")
    public R<Map<String, Object>> admin(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String username,
            HttpSession session) {
        requireSign();
        AdminAuth.requireAdmin(session);
        return R.ok(ESignStore.pageAdmin(page, size, username));
    }
}
