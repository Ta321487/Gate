package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.GuestTeaser;
import com.thesis.common.R;
import com.thesis.service.NoticeStore;
import com.thesis.service.UserStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * 公告：所有人可读；增删改仅总管理员。
 */
@RestController
@RequestMapping("/api/notices")
public class NoticeController {

    @GetMapping
    public R<Map<String, Object>> page(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        int p = GuestTeaser.clampPage(session, page);
        int s = GuestTeaser.clampSize(session, size);
        return R.ok(NoticeStore.page(p, s));
    }

    @GetMapping("/{id}")
    public R<Map<String, Object>> detail(@PathVariable long id) {
        Map<String, Object> m = NoticeStore.get(id);
        if (m == null) throw new BizException(ErrorCode.NOT_FOUND, "公告不存在");
        return R.ok(m);
    }

    @PostMapping
    public R<Map<String, Object>> create(@RequestBody Map<String, String> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        String title = body.getOrDefault("title", "");
        if (title.isBlank()) throw new BizException(ErrorCode.BAD_REQUEST, "标题不能为空");
        UserStore.Profile pub = publisher(session);
        return R.ok(NoticeStore.add(
                title,
                body.getOrDefault("content", ""),
                pub.username,
                pub.nickname
        ));
    }

    @PutMapping("/{id}")
    public R<Map<String, Object>> update(
            @PathVariable long id,
            @RequestBody Map<String, String> body,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        Map<String, Object> m = NoticeStore.update(id, body.get("title"), body.get("content"));
        if (m == null) throw new BizException(ErrorCode.NOT_FOUND, "公告不存在");
        return R.ok(m);
    }

    @DeleteMapping("/{id}")
    public R<Void> delete(@PathVariable long id, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        if (!NoticeStore.delete(id)) throw new BizException(ErrorCode.NOT_FOUND, "公告不存在");
        return R.ok(null);
    }

    private static UserStore.Profile publisher(HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        UserStore.Profile p = UserStore.get(uid);
        if (p == null) throw new BizException(ErrorCode.UNAUTHORIZED, "用户不存在");
        return p;
    }
}
