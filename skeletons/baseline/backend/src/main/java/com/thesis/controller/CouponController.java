package com.thesis.controller;

import com.thesis.capability.CouponStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/coupons")
public class CouponController {

    private static void require() {
        if (!CouponStore.enabled()) throw new BizException(ErrorCode.BAD_REQUEST, "优惠券功能暂不可用");
    }

    @GetMapping("/templates")
    public R<?> templates() {
        require();
        return R.ok(CouponStore.listActiveTemplates());
    }

    @GetMapping("/mine")
    public R<?> mine(
            @RequestParam(required = false) String status,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        require();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(CouponStore.pageMine(uid, status, page, size));
    }

    @PostMapping("/{id}/claim")
    public R<?> claim(@PathVariable long id, HttpSession session) {
        require();
        String uid = AdminAuth.requireLogin(session);
        try {
            return R.ok(CouponStore.claim(uid, id));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/admin")
    public R<?> adminPage(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        return R.ok(CouponStore.pageAdmin(page, size));
    }

    @PostMapping("/admin")
    public R<?> adminCreate(@RequestBody Map<String, Object> body, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(CouponStore.createTemplate(body == null ? Map.of() : body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PutMapping("/admin/{id}")
    public R<?> adminUpdate(
            @PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(CouponStore.updateTemplate(id, body == null ? Map.of() : body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
