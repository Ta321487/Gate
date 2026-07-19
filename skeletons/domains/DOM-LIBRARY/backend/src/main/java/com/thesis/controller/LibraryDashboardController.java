package com.thesis.controller;

import com.thesis.capability.ArchiveStore;
import com.thesis.capability.TicketStore;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.LibraryStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/admin/dashboard")
public class LibraryDashboardController {

    @GetMapping
    public R<Map<String, Object>> dashboard(HttpSession session) {
        requireAdmin(session);
        Map<String, Object> m = new LinkedHashMap<>(LibraryStore.dashboard());
        Map<String, Object> charts = new LinkedHashMap<>();
        charts.putAll(TicketStore.chartStats());
        try {
            charts.put("stockSeries", ArchiveStore.stockByCategory(8));
        } catch (Exception e) {
            charts.put("stockSeries", List.of());
        }
        m.put("charts", charts);
        return R.ok(m);
    }

    private static void requireAdmin(HttpSession session) {
        if (!"admin".equals(String.valueOf(session.getAttribute("role")))) {
            throw new BizException(ErrorCode.FORBIDDEN, "需要管理员权限");
        }
    }
}
