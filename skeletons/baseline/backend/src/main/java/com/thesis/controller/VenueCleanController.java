package com.thesis.controller;

import com.thesis.capability.VenueCleanStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/venue-clean")
public class VenueCleanController {

    private void requireOn() {
        if (!VenueCleanStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "未开启场馆保洁");
        }
    }

    @GetMapping("/tasks")
    public R<?> tasks(HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(VenueCleanStore.dirtyList());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/items")
    public R<?> items(HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(VenueCleanStore.listAll());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/items/{id}/dirty")
    public R<?> markDirty(@PathVariable long id, HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        Object post = session.getAttribute("staffPost");
        if (post != null && "venue_cleaner".equals(String.valueOf(post))) {
            throw new BizException(ErrorCode.FORBIDDEN, "保洁岗请使用「打扫完成」");
        }
        try {
            VenueCleanStore.markDirty(id);
            return R.ok(null);
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/items/{id}/clean-done")
    public R<?> cleanDone(@PathVariable long id, HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        try {
            VenueCleanStore.markClean(id);
            return R.ok(null);
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
