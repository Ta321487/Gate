package com.thesis.controller;

import com.thesis.capability.ArchiveLogStore;
import com.thesis.capability.ArchiveStore;
import com.thesis.capability.OrderStore;
import com.thesis.capability.SlotStore;
import com.thesis.capability.TicketStore;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 薄领域工作台（archive / standalone / LIBRARY）。
 */
@RestController
@RequestMapping("/api/admin/dashboard")
public class TicketDashboardController {

    @Value("${thesis.register-role:user}")
    private String userRole;

    @GetMapping
    public R<Map<String, Object>> dashboard(HttpSession session) {
        requireAdmin(session);
        Map<String, Object> m = new LinkedHashMap<>();
        Map<String, Object> charts = new LinkedHashMap<>();
        charts.put("statusSeries", List.of());
        charts.put("trendSeries", List.of());
        charts.put("stockSeries", List.of());

        if (TicketStore.enabled()) {
            try {
                m.putAll(TicketStore.dashboard(userRole));
                charts.putAll(TicketStore.chartStats());
            } catch (Exception ignored) {
                m.put("pendingTickets", 0);
                m.put("activeTickets", 0);
                m.put("completedTickets", 0);
                m.put("rejectedTickets", 0);
            }
        } else {
            try {
                m.putAll(TicketStore.dashboard(userRole));
            } catch (Exception ignored) {
                m.putIfAbsent("userTotal", 0);
                m.putIfAbsent("bookTotal", 0);
            }
        }

        if (OrderStore.enabled()) {
            m.putAll(OrderStore.dashboard());
            // 订单域优先用订单图；单据未启用时补趋势
            Map<String, Object> oc = OrderStore.chartStats();
            if (!TicketStore.enabled() || isEmptySeries(charts.get("statusSeries"))) {
                charts.put("statusSeries", oc.get("statusSeries"));
                charts.put("trendSeries", oc.get("trendSeries"));
            }
        }
        if (SlotStore.enabled()) {
            m.putAll(SlotStore.dashboard());
            Map<String, Object> sc = SlotStore.chartStats();
            if (!TicketStore.enabled() && !OrderStore.enabled()) {
                charts.put("statusSeries", sc.get("statusSeries"));
                charts.put("trendSeries", sc.get("trendSeries"));
            }
        }
        try {
            charts.put("stockSeries", ArchiveStore.stockByCategory(8));
        } catch (Exception ignored) {
            charts.put("stockSeries", List.of());
        }
        if (ArchiveLogStore.enabled()) {
            m.put("missingCheckinToday", ArchiveLogStore.countMissingToday("checkin"));
        }
        m.put("charts", charts);
        return R.ok(m);
    }

    private static boolean isEmptySeries(Object series) {
        return !(series instanceof List<?> list) || list.isEmpty();
    }

    private static void requireAdmin(HttpSession session) {
        if (!"admin".equals(String.valueOf(session.getAttribute("role")))) {
            throw new BizException(ErrorCode.FORBIDDEN, "需要管理员权限");
        }
    }
}
