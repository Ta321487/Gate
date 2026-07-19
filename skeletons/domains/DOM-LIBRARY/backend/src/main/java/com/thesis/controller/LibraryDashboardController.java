package com.thesis.controller;

import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.LibraryStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/admin/dashboard")
public class LibraryDashboardController {

    @GetMapping
    public R<Map<String, Object>> dashboard(HttpSession session) {
        requireAdmin(session);
        return R.ok(LibraryStore.dashboard());
    }

    private static void requireAdmin(HttpSession session) {
        if (!"admin".equals(String.valueOf(session.getAttribute("role")))) {
            throw new BizException(ErrorCode.FORBIDDEN, "需要管理员权限");
        }
    }
}
