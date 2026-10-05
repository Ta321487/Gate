package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.ApplyBlacklistStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/apply/blacklist")
public class ApplyBlacklistController {

    private static void requireReady() {
        if (!ApplyBlacklistStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通报名黑名单");
        }
    }

    @GetMapping
    public R<List<Map<String, Object>>> list(HttpSession session) {
        requireReady();
        AdminAuth.requireSuperAdmin(session);
        return R.ok(ApplyBlacklistStore.listAll());
    }

    @PostMapping
    public R<Map<String, Object>> add(@RequestBody Map<String, Object> body, HttpSession session) {
        requireReady();
        AdminAuth.requireSuperAdmin(session);
        String username = body == null || body.get("username") == null
                ? ""
                : String.valueOf(body.get("username"));
        String reason = body == null || body.get("reason") == null
                ? ""
                : String.valueOf(body.get("reason"));
        try {
            long id = ApplyBlacklistStore.add(username, reason);
            return R.ok(Map.of("id", id));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{id}/clear")
    public R<Void> clear(@PathVariable long id, HttpSession session) {
        requireReady();
        AdminAuth.requireSuperAdmin(session);
        ApplyBlacklistStore.remove(id);
        return R.ok(null);
    }
}
