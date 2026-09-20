package com.thesis.controller;

import com.thesis.capability.PurchaseGateStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/purchase-permits")
public class PurchaseGateController {

    private static void require() {
        if (!PurchaseGateStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "购买审核未开启");
        }
    }

    @GetMapping("/check")
    public R<?> check(
            @RequestParam long itemId,
            @RequestParam(defaultValue = "1") int qty,
            HttpSession session) {
        require();
        String uid = AdminAuth.requireLogin(session);
        try {
            return R.ok(PurchaseGateStore.check(uid, itemId, qty));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/targets")
    public R<?> targets(HttpSession session) {
        require();
        AdminAuth.requireLogin(session);
        return R.ok(PurchaseGateStore.targets());
    }

    @GetMapping("/mine")
    public R<?> mine(HttpSession session) {
        require();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(PurchaseGateStore.mine(uid));
    }

    @PostMapping
    public R<?> submit(@RequestBody(required = false) Map<String, Object> body, HttpSession session) {
        require();
        String uid = AdminAuth.requireLogin(session);
        try {
            return R.ok(PurchaseGateStore.submit(uid, body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping
    public R<?> list(HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        return R.ok(PurchaseGateStore.listAll());
    }

    @PostMapping("/review")
    public R<?> review(@RequestBody(required = false) Map<String, Object> body, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        String uid = AdminAuth.requireLogin(session);
        try {
            return R.ok(PurchaseGateStore.review(uid, body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
