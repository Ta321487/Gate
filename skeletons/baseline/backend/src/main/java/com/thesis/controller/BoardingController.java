package com.thesis.controller;

import com.thesis.capability.BoardingStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/boarding")
public class BoardingController {

    private static void require() {
        if (!BoardingStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "寄养未开启");
        }
    }

    @GetMapping("/cares")
    public R<?> cares(HttpSession session) {
        require();
        AdminAuth.requireLogin(session);
        return R.ok(BoardingStore.cares(true));
    }

    @GetMapping("/cares/all")
    public R<?> allCares(HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        return R.ok(BoardingStore.cares(false));
    }

    @PostMapping("/cares")
    public R<?> saveCare(@RequestBody Map<String, Object> body, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(BoardingStore.saveCare(body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/logs")
    public R<?> logs(HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        return R.ok(BoardingStore.logs(null));
    }

    @GetMapping("/mine")
    public R<?> mine(HttpSession session) {
        require();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(BoardingStore.logs(uid));
    }

    @PostMapping("/logs")
    public R<?> saveLog(@RequestBody Map<String, Object> body, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(BoardingStore.saveLog(body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
