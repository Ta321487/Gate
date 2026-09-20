package com.thesis.controller;

import com.thesis.capability.LessonStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/lessons")
public class LessonController {

    private static void require() {
        if (!LessonStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "课时未开启");
        }
    }

    private static String username(HttpSession session) {
        return AdminAuth.requireLogin(session);
    }

    @GetMapping("/packs")
    public R<?> packs(HttpSession session) {
        require();
        username(session);
        return R.ok(LessonStore.packs(true));
    }

    @GetMapping("/packs/all")
    public R<?> allPacks(HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        return R.ok(LessonStore.packs(false));
    }

    @PostMapping("/packs")
    public R<?> savePack(@RequestBody Map<String, Object> body, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        return R.ok(LessonStore.savePack(body));
    }

    @GetMapping("/mine")
    public R<?> mine(HttpSession session) {
        require();
        return R.ok(LessonStore.mine(username(session)));
    }

    @PostMapping("/buy")
    public R<?> buy(@RequestBody Map<String, Object> body, HttpSession session) {
        require();
        Object raw = body == null ? null : body.get("packId");
        long packId = 0;
        if (raw instanceof Number n) packId = n.longValue();
        else if (raw != null) {
            try {
                packId = Long.parseLong(String.valueOf(raw));
            } catch (NumberFormatException ignored) {
                packId = 0;
            }
        }
        return R.ok(LessonStore.buy(username(session), packId));
    }

    @GetMapping("/uses")
    public R<?> uses(HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        return R.ok(LessonStore.uses());
    }
}
