package com.thesis.controller;

import com.thesis.capability.ArchiveStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/** 通用档案 API：/api/archive（设备 / 物资等；LIBRARY 另保留 /api/books） */
@RestController
@RequestMapping("/api/archive")
public class ArchiveController {

    @GetMapping
    public R<Map<String, Object>> page(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) Long categoryId) {
        return R.ok(ArchiveStore.pageItems(keyword, categoryId, page, size));
    }

    @GetMapping("/{id}")
    public R<Map<String, Object>> detail(@PathVariable long id) {
        Map<String, Object> item = ArchiveStore.getItem(id);
        if (item == null) throw new BizException(ErrorCode.NOT_FOUND, "对象不存在");
        return R.ok(item);
    }

    @PostMapping
    public R<Map<String, Object>> create(@RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        String title = str(body.get("title"));
        if (title.isBlank()) throw new BizException(ErrorCode.BAD_REQUEST, "名称不能为空");
        return R.ok(ArchiveStore.addItem(
                title,
                str(body.get("author")),
                str(body.get("isbn")),
                body.get("categoryId") == null ? 1L : Long.parseLong(String.valueOf(body.get("categoryId"))),
                body.get("stock") == null ? 1 : Integer.parseInt(String.valueOf(body.get("stock"))),
                str(body.get("coverUrl")),
                body
        ));
    }

    @PutMapping("/{id}")
    public R<Map<String, Object>> update(
            @PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        Map<String, Object> updated = ArchiveStore.updateItem(id, body);
        if (updated == null) throw new BizException(ErrorCode.NOT_FOUND, "对象不存在");
        return R.ok(updated);
    }

    @DeleteMapping("/{id}")
    public R<Void> delete(@PathVariable long id, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        if (!ArchiveStore.deleteItem(id)) throw new BizException(ErrorCode.NOT_FOUND, "对象不存在");
        return R.ok(null);
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o);
    }
}
