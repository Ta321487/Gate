package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.OrgStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/** 浅组织树：登录可读选项，超管维护。 */
@RestController
public class OrgController {

    @GetMapping("/api/org/options")
    public R<List<Map<String, Object>>> options(HttpSession session) {
        AdminAuth.requireLogin(session);
        return R.ok(OrgStore.options());
    }

    @GetMapping("/api/admin/org")
    public R<List<Map<String, Object>>> list(HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        return R.ok(OrgStore.listAll());
    }

    @PostMapping("/api/admin/org")
    public R<Map<String, Object>> create(@RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            Map<String, Object> b = body == null ? Map.of() : body;
            return R.ok(OrgStore.create(
                    str(b.get("name")),
                    longOrNull(b.get("parentId")),
                    intOrNull(b.get("sortOrder"))));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PutMapping("/api/admin/org/{id}")
    public R<Map<String, Object>> update(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            Map<String, Object> b = body == null ? Map.of() : body;
            Long parent = b.containsKey("parentId") ? longOrNull(b.get("parentId")) : null;
            if (!b.containsKey("parentId")) {
                Map<String, Object> cur = OrgStore.get(id);
                Object p = cur.get("parentId");
                parent = p instanceof Number n ? n.longValue() : null;
            }
            return R.ok(OrgStore.update(
                    id,
                    b.containsKey("name") ? str(b.get("name")) : null,
                    parent,
                    b.containsKey("sortOrder") ? intOrNull(b.get("sortOrder")) : null,
                    b.containsKey("enabled") ? boolOrNull(b.get("enabled")) : null));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @DeleteMapping("/api/admin/org/{id}")
    public R<Void> delete(@PathVariable long id, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            OrgStore.delete(id);
            return R.ok(null);
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o);
    }

    private static Long longOrNull(Object o) {
        if (o == null || String.valueOf(o).isBlank() || "null".equals(String.valueOf(o))) return null;
        return Long.parseLong(String.valueOf(o).trim());
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
        return "1".equals(s) || "true".equalsIgnoreCase(s);
    }
}
