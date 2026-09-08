package com.thesis.controller;

import com.thesis.capability.AuditLogStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/admin/audit-logs")
public class AuditLogController {

    @GetMapping
    public R<?> page(
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String action,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            HttpSession session) {
        if (!AuditLogStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "操作日志功能暂不可用");
        }
        AdminAuth.requireSuperAdmin(session);
        try {
            return R.ok(AuditLogStore.page(keyword, action, page, size));
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
