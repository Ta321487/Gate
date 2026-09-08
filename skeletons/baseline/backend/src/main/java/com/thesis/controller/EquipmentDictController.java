package com.thesis.controller;

import com.thesis.capability.EquipmentDictStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
public class EquipmentDictController {

    /** 启用中的设备名（档案编辑多选；未挂能力返回空列表）。 */
    @GetMapping("/api/equipment-dict/options")
    public R<List<String>> options(HttpSession session) {
        if (session.getAttribute("uid") == null) {
            throw new BizException(ErrorCode.UNAUTHORIZED, "请先登录");
        }
        if (!EquipmentDictStore.enabled()) {
            return R.ok(List.of());
        }
        return R.ok(EquipmentDictStore.optionNames());
    }

    @GetMapping("/api/admin/equipment-dict")
    public R<?> page(
            @RequestParam(required = false) String keyword,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            HttpSession session) {
        requireEnabled();
        AdminAuth.requireSuperAdmin(session);
        try {
            return R.ok(EquipmentDictStore.page(keyword, page, size));
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/api/admin/equipment-dict")
    public R<?> create(@RequestBody Map<String, Object> body, HttpSession session) {
        requireEnabled();
        AdminAuth.requireSuperAdmin(session);
        try {
            return R.ok(EquipmentDictStore.create(
                    str(body.get("name")),
                    intOrNull(body.get("sortOrder")),
                    boolOrNull(body.get("enabled"))));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PutMapping("/api/admin/equipment-dict/{id}")
    public R<?> update(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        requireEnabled();
        AdminAuth.requireSuperAdmin(session);
        try {
            return R.ok(EquipmentDictStore.update(
                    id,
                    body.containsKey("name") ? str(body.get("name")) : null,
                    body.containsKey("sortOrder") ? intOrNull(body.get("sortOrder")) : null,
                    body.containsKey("enabled") ? boolOrNull(body.get("enabled")) : null));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @DeleteMapping("/api/admin/equipment-dict/{id}")
    public R<?> delete(@PathVariable long id, HttpSession session) {
        requireEnabled();
        AdminAuth.requireSuperAdmin(session);
        try {
            EquipmentDictStore.delete(id);
            return R.ok(null);
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    private static void requireEnabled() {
        if (!EquipmentDictStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "设备字典暂不可用");
        }
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static Integer intOrNull(Object o) {
        if (o == null || "".equals(String.valueOf(o).trim())) return null;
        try {
            return Integer.parseInt(String.valueOf(o).trim());
        } catch (Exception e) {
            return null;
        }
    }

    private static Boolean boolOrNull(Object o) {
        if (o == null) return null;
        if (o instanceof Boolean b) return b;
        String s = String.valueOf(o).trim().toLowerCase();
        if (s.isEmpty()) return null;
        return "1".equals(s) || "true".equals(s) || "yes".equals(s);
    }
}
