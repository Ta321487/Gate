package com.thesis.controller;

import com.thesis.capability.ArchiveStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/** 档案分类：列表公开可读；增删改需总管 */
@RestController
@RequestMapping("/api/categories")
public class CategoryController {

    @GetMapping
    public R<List<Map<String, Object>>> list() {
        return R.ok(ArchiveStore.listCategories());
    }

    @PostMapping
    public R<Map<String, Object>> create(@RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            return R.ok(ArchiveStore.createCategory(str(body.get("name"))));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PutMapping("/{id}")
    public R<Map<String, Object>> update(
            @PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            return R.ok(ArchiveStore.updateCategory(id, str(body.get("name"))));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @DeleteMapping("/{id}")
    public R<Void> delete(@PathVariable long id, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            ArchiveStore.deleteCategory(id);
            return R.ok(null);
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o);
    }
}
