package com.thesis.controller;

import com.thesis.capability.GroupBuyStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/group-buys")
public class GroupBuyController {

    private static void require() {
        if (!GroupBuyStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "拼团未开启");
        }
    }

    @GetMapping("/open")
    public R<?> open(HttpSession session) {
        require();
        AdminAuth.requireLogin(session);
        try {
            return R.ok(GroupBuyStore.listOpen());
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping
    public R<?> list(HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        return R.ok(GroupBuyStore.listAll());
    }

    @GetMapping("/products")
    public R<?> products(HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        return R.ok(GroupBuyStore.products());
    }

    @PostMapping
    public R<?> save(@RequestBody(required = false) Map<String, Object> body, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(GroupBuyStore.save(body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
