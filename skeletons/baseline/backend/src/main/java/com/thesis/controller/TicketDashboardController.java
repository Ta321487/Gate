package com.thesis.controller;

import com.thesis.capability.TicketStore;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/** 薄领域工作台；LIBRARY 等厚叠加用专用 DashboardController */
@RestController
@RequestMapping("/api/admin/dashboard")
@ConditionalOnProperty(name = "thesis.ticket-mode", havingValue = "standalone")
public class TicketDashboardController {

    @Value("${thesis.register-role:user}")
    private String userRole;

    @GetMapping
    public R<Map<String, Object>> dashboard(HttpSession session) {
        requireAdmin(session);
        return R.ok(TicketStore.dashboard(userRole));
    }

    private static void requireAdmin(HttpSession session) {
        if (!"admin".equals(String.valueOf(session.getAttribute("role")))) {
            throw new BizException(ErrorCode.FORBIDDEN, "需要管理员权限");
        }
    }
}
