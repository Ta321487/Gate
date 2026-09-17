package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.GuestTeaser;
import com.thesis.common.R;
import com.thesis.service.ItemCommentStore;
import com.thesis.service.UserStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * 档案条下评论：按 itemId 列表/发表；管理端分页与删除。≠ 门户留言 guestbook。
 */
@RestController
@RequestMapping("/api/item-comments")
public class ItemCommentController {

    @GetMapping("/by-item/{itemId}")
    public R<Map<String, Object>> byItem(
            @PathVariable long itemId,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            HttpSession session) {
        if (!ItemCommentStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通评论功能");
        }
        int p = GuestTeaser.clampPage(session, page);
        int s = GuestTeaser.clampSize(session, size);
        return R.ok(ItemCommentStore.pageByItem(itemId, p, s));
    }

    @GetMapping
    public R<Map<String, Object>> adminPage(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) Long itemId,
            HttpSession session) {
        AdminAuth.requireAdmin(session);
        if (!ItemCommentStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通评论功能");
        }
        return R.ok(ItemCommentStore.pageAdmin(page, size, itemId));
    }

    @PostMapping
    public R<Map<String, Object>> create(@RequestBody Map<String, Object> body, HttpSession session) {
        if (!ItemCommentStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通评论功能");
        }
        String uid = AdminAuth.requireLogin(session);
        UserStore.Profile p = UserStore.get(uid);
        if (p == null) throw new BizException(ErrorCode.UNAUTHORIZED, "用户不存在");
        long itemId = 0L;
        if (body != null && body.get("itemId") != null) {
            try {
                itemId = Long.parseLong(String.valueOf(body.get("itemId")).trim());
            } catch (NumberFormatException e) {
                itemId = 0L;
            }
        }
        if (itemId <= 0) {
            throw new BizException(ErrorCode.BAD_REQUEST, "缺少内容编号");
        }
        String text = body == null || body.get("body") == null ? "" : String.valueOf(body.get("body"));
        if (text.isBlank()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "评论内容不能为空");
        }
        Map<String, Object> row = ItemCommentStore.add(itemId, p.username, p.nickname, text);
        if (row == null) throw new BizException(ErrorCode.BAD_REQUEST, "评论失败");
        return R.ok(row);
    }

    @DeleteMapping("/{id}")
    public R<Void> delete(@PathVariable long id, HttpSession session) {
        AdminAuth.requireAdmin(session);
        if (!ItemCommentStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通评论功能");
        }
        if (!ItemCommentStore.delete(id)) throw new BizException(ErrorCode.NOT_FOUND, "评论不存在");
        return R.ok(null);
    }
}
