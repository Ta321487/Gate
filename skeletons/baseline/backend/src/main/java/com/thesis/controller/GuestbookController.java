package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.GuestTeaser;
import com.thesis.common.R;
import com.thesis.service.GuestbookStore;
import com.thesis.service.UserStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * 门户留言：列表可读；发表需登录；删除/回复仅总管。
 */
@RestController
@RequestMapping("/api/guestbook")
public class GuestbookController {

    @GetMapping
    public R<Map<String, Object>> page(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        if (!GuestbookStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通留言功能");
        }
        int p = GuestTeaser.clampPage(session, page);
        int s = GuestTeaser.clampSize(session, size);
        return R.ok(GuestbookStore.page(p, s));
    }

    @PostMapping
    public R<Map<String, Object>> create(@RequestBody Map<String, String> body, HttpSession session) {
        if (!GuestbookStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通留言功能");
        }
        String uid = AdminAuth.requireLogin(session);
        UserStore.Profile p = UserStore.get(uid);
        if (p == null) throw new BizException(ErrorCode.UNAUTHORIZED, "用户不存在");
        String text = body == null ? "" : body.getOrDefault("body", "");
        if (text == null || text.isBlank()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "留言内容不能为空");
        }
        Map<String, Object> row = GuestbookStore.add(p.username, p.nickname, text);
        if (row == null) throw new BizException(ErrorCode.BAD_REQUEST, "留言失败");
        return R.ok(row);
    }

    @PutMapping("/{id}/reply")
    public R<Map<String, Object>> reply(
            @PathVariable long id,
            @RequestBody Map<String, String> body,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        if (!GuestbookStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通留言功能");
        }
        String uid = AdminAuth.requireLogin(session);
        String reply = body == null ? "" : body.getOrDefault("reply", "");
        if (reply == null || reply.isBlank()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "回复不能为空");
        }
        Map<String, Object> row = GuestbookStore.reply(id, reply, uid);
        if (row == null) throw new BizException(ErrorCode.NOT_FOUND, "留言不存在");
        return R.ok(row);
    }

    @DeleteMapping("/{id}")
    public R<Void> delete(@PathVariable long id, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        if (!GuestbookStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通留言功能");
        }
        if (!GuestbookStore.delete(id)) throw new BizException(ErrorCode.NOT_FOUND, "留言不存在");
        return R.ok(null);
    }
}
