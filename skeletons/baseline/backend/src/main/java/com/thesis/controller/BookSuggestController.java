package com.thesis.controller;

import com.thesis.capability.BookSuggestStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
public class BookSuggestController {

    @PostMapping("/api/book-suggest")
    public R<?> submit(@RequestBody Map<String, Object> body, HttpSession session) {
        requireEnabled();
        String uid = AdminAuth.requireLogin(session);
        try {
            return R.ok(BookSuggestStore.submit(
                    uid,
                    str(body.get("title")),
                    str(body.get("isbn")),
                    str(body.get("author")),
                    str(body.get("reason"))));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/api/book-suggest/mine")
    public R<?> mine(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        requireEnabled();
        String uid = AdminAuth.requireLogin(session);
        try {
            return R.ok(BookSuggestStore.pageMine(uid, page, size));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/api/admin/book-suggest")
    public R<?> adminPage(
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String username,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            HttpSession session) {
        requireEnabled();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(BookSuggestStore.page(username, status, page, size));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/api/admin/book-suggest/{id}/resolve")
    public R<?> resolve(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        requireEnabled();
        AdminAuth.requireAdmin(session);
        String op = AdminAuth.requireLogin(session);
        try {
            String action = str(body.get("action"));
            String note = str(body.get("note"));
            return R.ok(BookSuggestStore.resolve(id, action, op, note));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    private static void requireEnabled() {
        if (!BookSuggestStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "荐购功能暂不可用");
        }
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }
}
