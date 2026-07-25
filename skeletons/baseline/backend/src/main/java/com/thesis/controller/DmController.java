package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.DmStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 一对一私信：会话列表 / 消息拉取 / 发送 / 已读；登录用户仅读写自己相关消息。
 */
@RestController
@RequestMapping("/api/dm")
public class DmController {

    private void requireReady() {
        if (!DmStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通私信功能");
        }
    }

    @GetMapping("/peers")
    public R<List<Map<String, Object>>> peers(
            @RequestParam(defaultValue = "50") int limit,
            HttpSession session) {
        requireReady();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(DmStore.peers(uid, limit));
    }

    @GetMapping("/conversations")
    public R<List<Map<String, Object>>> conversations(HttpSession session) {
        requireReady();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(DmStore.conversations(uid));
    }

    @GetMapping("/messages")
    public R<List<Map<String, Object>>> messages(
            @RequestParam String peer,
            @RequestParam(defaultValue = "0") long sinceId,
            HttpSession session) {
        requireReady();
        String uid = AdminAuth.requireLogin(session);
        if (peer == null || peer.isBlank()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "请指定会话对象");
        }
        return R.ok(DmStore.messages(uid, peer, sinceId));
    }

    @PostMapping("/messages")
    public R<Map<String, Object>> send(@RequestBody Map<String, String> body, HttpSession session) {
        requireReady();
        String uid = AdminAuth.requireLogin(session);
        String to = body == null ? "" : body.getOrDefault("toUsername", "");
        String text = body == null ? "" : body.getOrDefault("body", "");
        if (to == null || to.isBlank()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "请指定收件人");
        }
        if (text == null || text.isBlank()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "消息不能为空");
        }
        Map<String, Object> row = DmStore.send(uid, to, text);
        if (row == null) {
            throw new BizException(ErrorCode.BAD_REQUEST, "发送失败（对方不存在或不可发）");
        }
        return R.ok(row);
    }

    @PostMapping("/read")
    public R<Map<String, Object>> markRead(@RequestBody Map<String, String> body, HttpSession session) {
        requireReady();
        String uid = AdminAuth.requireLogin(session);
        String peer = body == null ? "" : body.getOrDefault("peer", "");
        if (peer == null || peer.isBlank()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "请指定会话对象");
        }
        int n = DmStore.markRead(uid, peer);
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("updated", n);
        return R.ok(m);
    }

    @GetMapping("/unread-count")
    public R<Map<String, Object>> unread(HttpSession session) {
        requireReady();
        String uid = AdminAuth.requireLogin(session);
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("count", DmStore.unreadCount(uid));
        return R.ok(m);
    }
}
