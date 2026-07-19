package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.MessageStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 站内消息：登录用户只读写自己的收件箱。
 */
@RestController
@RequestMapping("/api/messages")
public class MessageController {

    @GetMapping
    public R<Map<String, Object>> page(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        return R.ok(MessageStore.page(uid, page, size));
    }

    @GetMapping("/unread-count")
    public R<Map<String, Object>> unread(HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("count", MessageStore.unreadCount(uid));
        return R.ok(m);
    }

    @PostMapping("/{id}/read")
    public R<Void> markRead(@PathVariable long id, HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        if (!MessageStore.markRead(uid, id)) {
            throw new BizException(ErrorCode.NOT_FOUND, "消息不存在");
        }
        return R.ok(null);
    }

    @PostMapping("/read-all")
    public R<Map<String, Object>> markAll(HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("updated", MessageStore.markAllRead(uid));
        return R.ok(m);
    }
}
