package com.thesis.controller;

import com.thesis.capability.AuditLogStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.RoleMenuStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 岗位菜单勾选：无记录时前端继续用原岗位菜单。 */
@RestController
public class RoleMenuController {

    @GetMapping("/api/auth/menu-keys")
    public R<Map<String, Object>> mine(HttpSession session) {
        AdminAuth.requireLogin(session);
        Object post = session.getAttribute("staffPost");
        String staffPost = post == null ? "" : String.valueOf(post);
        List<String> keys = RoleMenuStore.keysOf(staffPost);
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("staffPost", staffPost);
        m.put("usePacks", keys == null);
        m.put("keys", keys == null ? List.of() : keys);
        return R.ok(m);
    }

    @GetMapping("/api/admin/role-menus")
    public R<Map<String, Object>> get(
            @RequestParam String staffPost,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        List<String> keys = RoleMenuStore.keysOf(staffPost);
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("staffPost", staffPost);
        m.put("usePacks", keys == null);
        m.put("keys", keys == null ? List.of() : keys);
        return R.ok(m);
    }

    @PutMapping("/api/admin/role-menus")
    public R<Map<String, Object>> save(@RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            Map<String, Object> b = body == null ? Map.of() : body;
            String post = String.valueOf(b.getOrDefault("staffPost", "")).trim();
            List<String> keys = new ArrayList<>();
            Object raw = b.get("keys");
            if (raw instanceof List<?> list) {
                for (Object o : list) {
                    if (o != null) keys.add(String.valueOf(o));
                }
            }
            List<String> saved = RoleMenuStore.replace(post, keys);
            String op = AdminAuth.requireLogin(session);
            AuditLogStore.record(op, "role_menus", "staff_post", post, "更新岗位菜单");
            return R.ok(Map.of("staffPost", post, "usePacks", saved.isEmpty(), "keys", saved));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
