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
@RequestMapping("/api/favorites")
public class FavoriteController {

    private static void requireFav() {
        if (!FavoriteStore.enabled()) throw new BizException(ErrorCode.BAD_REQUEST, "收藏功能暂不可用");
    }

    @GetMapping
    public R<?> page(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        requireFav();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(FavoriteStore.page(uid, page, size));
    }

    @GetMapping("/ids")
    public R<?> ids(HttpSession session) {
        requireFav();
        String uid = AdminAuth.requireLogin(session);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("ids", FavoriteStore.idsOf(uid));
        return R.ok(out);
    }

    @PostMapping("/{itemId}/toggle")
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
}
