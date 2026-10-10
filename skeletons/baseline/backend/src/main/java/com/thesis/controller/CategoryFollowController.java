package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.CategoryFollowStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.Map;

/** 专栏订阅 API（C-04） */
@RestController
@RequestMapping("/api/category-follow")
public class CategoryFollowController {

    @GetMapping("/mine")
    public R<?> mine(HttpSession session) {
        if (!CategoryFollowStore.enabled()) throw new BizException(ErrorCode.BAD_REQUEST, "未开放专栏订阅");
        String uid = AdminAuth.requireLogin(session);
        return R.ok(CategoryFollowStore.listMine(uid));
    }

    @GetMapping("/count/{categoryId}")
    public R<?> count(@PathVariable long categoryId) {
        if (!CategoryFollowStore.enabled()) return R.ok(Map.of("count", 0));
        return R.ok(Map.of("count", CategoryFollowStore.followerCount(categoryId)));
    }

    @GetMapping("/status/{categoryId}")
    public R<?> status(@PathVariable long categoryId, HttpSession session) {
        if (!CategoryFollowStore.enabled()) {
            return R.ok(Map.of("following", false, "count", 0));
        }
        Object uidAttr = session.getAttribute("uid");
        String uid = uidAttr == null ? "" : uidAttr.toString().trim();
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("following", !uid.isBlank() && CategoryFollowStore.isFollowing(uid, categoryId));
        m.put("count", CategoryFollowStore.followerCount(categoryId));
        return R.ok(m);
    }

    @PostMapping("/{categoryId}/toggle")
    public R<?> toggle(@PathVariable long categoryId, HttpSession session) {
        if (!CategoryFollowStore.enabled()) throw new BizException(ErrorCode.BAD_REQUEST, "未开放专栏订阅");
        String uid = AdminAuth.requireLogin(session);
        boolean on = CategoryFollowStore.toggle(uid, categoryId);
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("following", on);
        m.put("count", CategoryFollowStore.followerCount(categoryId));
        return R.ok(m);
    }
}
