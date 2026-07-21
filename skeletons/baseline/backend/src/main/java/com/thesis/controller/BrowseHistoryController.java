package com.thesis.controller;

import com.thesis.capability.BrowseHistoryStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/browse-history")
public class BrowseHistoryController {

    private static void require() {
        if (!BrowseHistoryStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "浏览历史暂不可用");
        }
    }

    @GetMapping
    public R<?> page(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        require();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(BrowseHistoryStore.page(uid, page, size));
    }

    @PostMapping("/{itemId}")
    public R<?> touch(@PathVariable long itemId, HttpSession session) {
        require();
        String uid = AdminAuth.requireLogin(session);
        BrowseHistoryStore.touch(uid, itemId);
        return R.ok(Map.of("ok", true));
    }

    @DeleteMapping
    public R<?> clear(HttpSession session) {
        require();
        String uid = AdminAuth.requireLogin(session);
        BrowseHistoryStore.clear(uid);
        return R.ok(null);
    }
}
