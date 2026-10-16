package com.thesis.controller;

import com.thesis.capability.AuditLogStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.SiteSettingStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/** 系统外观浅设置：公开读 + 超管写。 */
@RestController
public class SiteSettingController {

    @GetMapping("/api/site-settings")
    public R<Map<String, Object>> publicSettings() {
        return R.ok(SiteSettingStore.publicMap());
    }

    @GetMapping("/api/admin/site-settings")
    public R<Map<String, Object>> adminGet(HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        return R.ok(SiteSettingStore.adminMap());
    }

    @PutMapping("/api/admin/site-settings")
    public R<Map<String, Object>> adminSave(
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            Map<String, Object> saved = SiteSettingStore.saveAdmin(body);
            String op = AdminAuth.requireLogin(session);
            AuditLogStore.record(op, "site_settings", "site", "settings", "更新系统外观");
            return R.ok(saved);
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
