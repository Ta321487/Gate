package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.DictStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/** 通识数据字典：管理端 CRUD；选项接口登录可读。 */
@RestController
public class DictController {

    @GetMapping("/api/dict/options")
    public R<List<Map<String, Object>>> options(
            @RequestParam String type,
            HttpSession session) {
        AdminAuth.requireLogin(session);
        return R.ok(DictStore.options(type));
    }

    @GetMapping("/api/admin/dict/types")
    public R<List<String>> types(HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        return R.ok(DictStore.listTypes());
    }

    @GetMapping("/api/admin/dict")
    public R<Map<String, Object>> page(
            @RequestParam(required = false) String type,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false, defaultValue = "1") int page,
            @RequestParam(required = false, defaultValue = "20") int size,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            return R.ok(DictStore.page(type, keyword, page, size));
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/api/admin/dict")
    public R<Map<String, Object>> create(@RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            Map<String, Object> b = body == null ? Map.of() : body;
            return R.ok(DictStore.create(
                    str(b.get("dictType")),
                    str(b.get("itemCode")),
                    str(b.get("itemLabel")),
                    intOrNull(b.get("sortOrder")),
                    boolOrNull(b.get("enabled"))));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PutMapping("/api/admin/dict/{id}")
    public R<Map<String, Object>> update(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            Map<String, Object> b = body == null ? Map.of() : body;
            return R.ok(DictStore.update(
                    id,
                    b.containsKey("dictType") ? str(b.get("dictType")) : null,
                    b.containsKey("itemCode") ? str(b.get("itemCode")) : null,
                    b.containsKey("itemLabel") ? str(b.get("itemLabel")) : null,
                    b.containsKey("sortOrder") ? intOrNull(b.get("sortOrder")) : null,
                    b.containsKey("enabled") ? boolOrNull(b.get("enabled")) : null));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/api/admin/dict/{id}/sort")
    public R<Map<String, Object>> bumpSort(
            @PathVariable long id,
            @RequestBody(required = false) Map<String, Object> body,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            Map<String, Object> b = body == null ? Map.of() : body;
            int delta = 10;
            if (b.get("delta") != null) {
                delta = Integer.parseInt(String.valueOf(b.get("delta")).trim());
            }
            return R.ok(DictStore.bumpSort(id, delta));
        } catch (NumberFormatException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, "排序步长无效");
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @DeleteMapping("/api/admin/dict/{id}")
    public R<Void> delete(@PathVariable long id, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            DictStore.delete(id);
            return R.ok(null);
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o);
    }

    private static Integer intOrNull(Object o) {
        if (o == null || String.valueOf(o).isBlank()) return null;
        return Integer.parseInt(String.valueOf(o).trim());
    }

    private static Boolean boolOrNull(Object o) {
        if (o == null) return null;
        if (o instanceof Boolean b) return b;
        String s = String.valueOf(o).trim();
        if (s.isBlank()) return null;
        return "1".equals(s) || "true".equalsIgnoreCase(s) || "yes".equalsIgnoreCase(s);
    }
}
