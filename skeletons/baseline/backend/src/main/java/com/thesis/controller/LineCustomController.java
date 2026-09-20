package com.thesis.controller;

import com.thesis.capability.LineCustomStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/line-specs")
public class LineCustomController {

    private static void require() {
        if (!LineCustomStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "定制未开启");
        }
    }

    @GetMapping("/options")
    public R<?> options(HttpSession session) {
        require();
        AdminAuth.requireLogin(session);
        return R.ok(LineCustomStore.listEnabled());
    }

    @GetMapping
    public R<?> list(HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(LineCustomStore.listAll());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping
    public R<?> save(@RequestBody(required = false) Map<String, Object> body, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(LineCustomStore.save(body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
