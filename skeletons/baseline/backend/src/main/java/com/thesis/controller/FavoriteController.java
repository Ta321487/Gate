package com.thesis.controller;

import com.thesis.capability.FavoriteStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
public class FavoriteController {

    private static void requireFav() {
        if (!FavoriteStore.enabled()) throw new BizException(ErrorCode.BAD_REQUEST, "收藏功能暂不可用");
    }

    private static void requireLike() {
        if (!FavoriteStore.likeEnabled()) throw new BizException(ErrorCode.BAD_REQUEST, "点赞功能暂不可用");
    }

    private static void requireReport() {
        if (!FavoriteStore.reportEnabled()) throw new BizException(ErrorCode.BAD_REQUEST, "举报功能暂不可用");
    }

    @GetMapping("/api/favorites")
    public R<?> page(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        requireFav();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(FavoriteStore.page(uid, page, size));
    }

    @GetMapping("/api/favorites/ids")
    public R<?> ids(HttpSession session) {
        requireFav();
        String uid = AdminAuth.requireLogin(session);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("ids", FavoriteStore.idsOf(uid));
        return R.ok(out);
    }

    @PostMapping("/api/favorites/{itemId}/toggle")
    public R<?> toggle(@PathVariable long itemId, HttpSession session) {
        requireFav();
        String uid = AdminAuth.requireLogin(session);
        try {
            boolean on = FavoriteStore.toggle(uid, itemId);
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("favorited", on);
            return R.ok(out);
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/api/likes/ids")
    public R<?> likeIds(HttpSession session) {
        requireLike();
        String uid = AdminAuth.requireLogin(session);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("ids", FavoriteStore.likedIdsOf(uid));
        return R.ok(out);
    }

    @PostMapping("/api/likes/{itemId}/toggle")
    public R<?> toggleLike(@PathVariable long itemId, HttpSession session) {
        requireLike();
        String uid = AdminAuth.requireLogin(session);
        try {
            boolean on = FavoriteStore.toggleLike(uid, itemId);
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("liked", on);
            return R.ok(out);
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/api/content-reports")
    public R<?> submitReport(@RequestBody Map<String, Object> body, HttpSession session) {
        requireReport();
        String uid = AdminAuth.requireLogin(session);
        try {
            String type = body.get("targetType") == null ? "archive" : String.valueOf(body.get("targetType"));
            long tid = 0;
            Object raw = body.get("targetId");
            if (raw instanceof Number n) tid = n.longValue();
            else if (raw != null && !String.valueOf(raw).isBlank()) tid = Long.parseLong(String.valueOf(raw).trim());
            String reason = body.get("reason") == null ? "" : String.valueOf(body.get("reason"));
            return R.ok(FavoriteStore.submitReport(uid, type, tid, reason));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/api/admin/content-reports")
    public R<?> adminPage(
            @RequestParam(required = false) String status,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        requireReport();
        AdminAuth.requireAdmin(session);
        return R.ok(FavoriteStore.pageReports(status, page, size));
    }

    @PostMapping("/api/admin/content-reports/{id}/resolve")
    public R<?> resolve(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        requireReport();
        AdminAuth.requireAdmin(session);
        String op = AdminAuth.requireLogin(session);
        try {
            String action = body.get("action") == null ? "" : String.valueOf(body.get("action"));
            String note = body.get("note") == null ? "" : String.valueOf(body.get("note"));
            return R.ok(FavoriteStore.resolveReport(id, action, op, note));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
