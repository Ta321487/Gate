package com.thesis.controller;

import com.thesis.capability.BlindBoxStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/blind-boxes")
public class BlindBoxController {

    private static void require() {
        if (!BlindBoxStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "盲盒未开启");
        }
    }

    @GetMapping("/boxes")
    public R<?> boxes(HttpSession session) {
        require();
        String username = AdminAuth.requireLogin(session);
        try {
            return R.ok(BlindBoxStore.boxes(username));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/prizes")
    public R<?> prizes(HttpSession session) {
        require();
        AdminAuth.requireLogin(session);
        try {
            return R.ok(BlindBoxStore.prizeOnly());
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/progress")
    public R<?> progress(@RequestParam(defaultValue = "0") long itemId, HttpSession session) {
        require();
        String username = AdminAuth.requireLogin(session);
        try {
            return R.ok(BlindBoxStore.progress(username, itemId));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping
    public R<?> list(HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(BlindBoxStore.listAll());
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/products")
    public R<?> products(HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(BlindBoxStore.products());
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping
    public R<?> save(@RequestBody(required = false) Map<String, Object> body, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(BlindBoxStore.save(body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
