package com.thesis.controller;

import com.thesis.capability.TicketStore;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnExpression;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 薄领域工作台（archive / standalone）。
 * LIBRARY 厚叠加用 {@code LibraryDashboardController}，故排除 DOM-LIBRARY。
 */
@RestController
@RequestMapping("/api/admin/dashboard")
@ConditionalOnExpression("!'${thesis.domain:}'.equals('DOM-LIBRARY')")
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
