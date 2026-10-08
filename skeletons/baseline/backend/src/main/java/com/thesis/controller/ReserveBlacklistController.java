package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.ReserveBlacklistStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/reserve/blacklist")
public class ReserveBlacklistController {

    private static void requireReady() {
        if (!ReserveBlacklistStore.ready()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "预约黑名单功能暂不可用");
        }
    }

    @GetMapping
    public R<?> list(HttpSession session) {
        requireReady();
        AdminAuth.requireAdmin(session);
        return R.ok(ReserveBlacklistStore.listAll());
    }

    @PostMapping
    public R<?> add(@RequestBody Map<String, Object> body, HttpSession session) {
        requireReady();
        AdminAuth.requireAdmin(session);
        try {
            long id = ReserveBlacklistStore.add(
                    String.valueOf(body.getOrDefault("username", "")),
                    String.valueOf(body.getOrDefault("reason", "")));
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("id", id);
            return R.ok(out);
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{id}/clear")
    public R<?> clear(@PathVariable long id, HttpSession session) {
        requireReady();
        AdminAuth.requireAdmin(session);
        ReserveBlacklistStore.remove(id);
        return R.ok(Map.of("ok", true));
    }

    @GetMapping("/appeals")
    public R<?> appeals(HttpSession session) {
        requireReady();
        String uid = AdminAuth.requireLogin(session);
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")))
                || "super_admin".equals(String.valueOf(session.getAttribute("role")));
        return R.ok(ReserveBlacklistStore.listAppeals(admin ? null : uid));
    }

    @PostMapping("/appeals")
    public R<?> submitAppeal(@RequestBody Map<String, Object> body, HttpSession session) {
        requireReady();
        String uid = AdminAuth.requireLogin(session);
        try {
            long id = ReserveBlacklistStore.submitAppeal(
                    uid, String.valueOf(body.getOrDefault("reason", "")));
            return R.ok(Map.of("id", id));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/appeals/{id}/resolve")
    public R<?> resolve(
            @PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        requireReady();
        AdminAuth.requireAdmin(session);
        boolean approve = Boolean.parseBoolean(String.valueOf(body.getOrDefault("approve", "true")));
        try {
            ReserveBlacklistStore.resolveAppeal(id, approve);
            return R.ok(Map.of("ok", true));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
