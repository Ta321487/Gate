package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.DoclibStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/doclib")
public class DoclibController {

    private static void requireDoclib() {
        if (!DoclibStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通文库功能");
        }
    }

    private static boolean isAdmin(HttpSession session) {
        return "admin".equals(String.valueOf(session.getAttribute("role")));
    }

    @GetMapping("/items")
    public R<List<Map<String, Object>>> items(HttpSession session) {
        requireDoclib();
        AdminAuth.requireLogin(session);
        return R.ok(DoclibStore.listOpenItems(isAdmin(session)));
    }

    @GetMapping("/items/{id}")
    public R<Map<String, Object>> item(@PathVariable long id, HttpSession session) {
        requireDoclib();
        AdminAuth.requireLogin(session);
        Map<String, Object> item = DoclibStore.getItem(id);
        if (item == null) throw new BizException(ErrorCode.NOT_FOUND, "资料不存在");
        return R.ok(item);
    }

    @PostMapping("/items/{id}/download")
    public R<Map<String, Object>> download(@PathVariable long id, HttpSession session) {
        requireDoclib();
        String uid = AdminAuth.requireLogin(session);
        try {
            return R.ok(DoclibStore.download(uid, id, isAdmin(session)));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/mine")
    public R<Map<String, Object>> mine(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        requireDoclib();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(DoclibStore.pageMine(uid, page, size));
    }

    @GetMapping("/admin/logs")
    public R<Map<String, Object>> adminLogs(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) Long itemId,
            HttpSession session) {
        requireDoclib();
        AdminAuth.requireAdmin(session);
        return R.ok(DoclibStore.pageLogsAdmin(page, size, itemId));
    }

    @PutMapping("/admin/items/{id}")
    public R<Map<String, Object>> updateMeta(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        requireDoclib();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(DoclibStore.updateMeta(id, body == null ? Map.of() : body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
