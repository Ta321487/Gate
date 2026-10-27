package com.thesis.controller;

import com.thesis.capability.ArchiveLogStore;
import com.thesis.capability.ArchiveStore;
import com.thesis.capability.OrderStore;
import com.thesis.capability.SlotStore;
import com.thesis.capability.TicketStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.SiteStatStore;
import com.thesis.service.StockIoStore;
import com.thesis.service.SurveyStore;
import com.thesis.service.UserStore;
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
 * 工作台角标接口；按角色收窄「处理中」计数。
 */
@RestController
@RequestMapping("/api/admin/dashboard")
public class TicketDashboardController {

    @Value("${thesis.register-role:user}")
    private String userRole;

    /** 侧栏角标轮询：只返回待办数字，避免拉全量图表。 */
    @GetMapping("/counts")
    public R<Map<String, Object>> counts(HttpSession session) {
        requireAdmin(session);
        Map<String, Object> full = buildDashboard(session);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("pendingTickets", num(full.get("pendingTickets")));
        out.put("activeTickets", num(full.get("activeTickets")));
        out.put("pendingOrders", num(full.get("pendingOrders")));
        out.put("pendingReservations", num(full.get("pendingReservations")));
        out.put("confirmedReservations", num(full.get("confirmedReservations")));
        out.put("missingCheckinToday", num(full.get("missingCheckinToday")));
        out.put("lowStockCount", num(full.get("lowStockCount")));
        out.put("todoScopedByRole", Boolean.TRUE.equals(full.get("todoScopedByRole")));
        return R.ok(out);
    }

    @GetMapping
    public R<Map<String, Object>> dashboard(HttpSession session) {
        requireAdmin(session);
        return R.ok(buildDashboard(session));
    }

    private Map<String, Object> buildDashboard(HttpSession session) {
        Map<String, Object> m = new LinkedHashMap<>();
        Map<String, Object> charts = new LinkedHashMap<>();
        charts.put("statusSeries", List.of());
        charts.put("trendSeries", List.of());
        charts.put("monthSeries", List.of());
        charts.put("stockSeries", List.of());

        boolean superAdmin = AdminAuth.isSuperAdmin(session);
        String uid = AdminAuth.requireLogin(session);
        // 多店：仅「有商家岗位」的账号按本店收窄；平台总管（无 staff_post）看全站，
        // 避免 superAdmin 会话标志异常时日报/分类库存被滤成空。
        String staffPost = "";
        Object sp = session.getAttribute("staffPost");
        if (sp != null) staffPost = String.valueOf(sp).trim();
        boolean merchantScoped =
                ArchiveStore.shopMarketplaceEnabled() && !superAdmin && !staffPost.isEmpty();

        if (TicketStore.enabled()) {
            try {
                m.putAll(TicketStore.dashboard(userRole, uid, superAdmin));
                charts.putAll(TicketStore.chartStats());
            } catch (Exception ignored) {
                m.put("pendingTickets", 0);
                m.put("activeTickets", 0);
                m.put("completedTickets", 0);
                m.put("rejectedTickets", 0);
                m.put("todoScopedByRole", false);
            }
        }
        // 无单据包 prune 掉 TicketStore 后不要再调 dashboard（会变成 putAll(null) 把 KPI 写成 0）

        if (OrderStore.enabled()) {
            String ownerFilter = merchantScoped ? uid : null;
            m.putAll(OrderStore.dashboard(ownerFilter));
            Map<String, Object> oc = OrderStore.chartStats(ownerFilter);
            if (!TicketStore.enabled() || isEmptySeries(charts.get("statusSeries"))) {
                charts.put("statusSeries", oc.get("statusSeries"));
                charts.put("trendSeries", oc.get("trendSeries"));
                charts.put("monthSeries", oc.get("monthSeries"));
            }
            if (oc.get("hotItemSeries") != null) {
                charts.put("hotItemSeries", oc.get("hotItemSeries"));
            }
            if (oc.get("salesDailySeries") != null) {
                charts.put("salesDailySeries", oc.get("salesDailySeries"));
            }
            if (oc.get("refundReasonSeries") != null) {
                charts.put("refundReasonSeries", oc.get("refundReasonSeries"));
            }
        }
        if (StockIoStore.enabled()) {
            try {
                charts.put("stockIoSeries", StockIoStore.typeSeries());
            } catch (Exception ignored) {
                charts.put("stockIoSeries", List.of());
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
            charts.put("stockSeries", ArchiveStore.stockByCategory(8, merchantScoped ? uid : null));
        } catch (Exception ignored) {
            charts.put("stockSeries", List.of());
        }
        try {
            charts.put("stageSeries", ArchiveStore.countByItemColumn("stage", 12));
            charts.put("leadSourceSeries", ArchiveStore.countByItemColumn("lead_source", 12));
            charts.put("listingFunnelSeries", ArchiveStore.countByItemColumn("rent_stage", 12));
            if (isEmptySeries(charts.get("listingFunnelSeries"))) {
                charts.put("listingFunnelSeries", ArchiveStore.countByItemColumn("stage", 12));
            }
        } catch (Exception ignored) {
            charts.putIfAbsent("stageSeries", List.of());
            charts.putIfAbsent("leadSourceSeries", List.of());
            charts.putIfAbsent("listingFunnelSeries", List.of());
        }
        try {
            TicketStore.maybeNotifyWeekReports(null);
        } catch (Exception ignored) {
        }
        if (ArchiveLogStore.enabled()) {
            m.put("missingCheckinToday", ArchiveLogStore.countMissingToday("checkin"));
        }
        if (SurveyStore.enabled()) {
            try {
                m.put("surveyRecycleCards", SurveyStore.recycleCards());
            } catch (Exception ignored) {
                m.put("surveyRecycleCards", List.of());
            }
        }
        if (ArchiveStore.shopMarketplaceEnabled()) {
            int warn = 10;
            try {
                Object w = m.get("stockWarnBelow");
                if (w instanceof Number n) warn = n.intValue();
            } catch (Exception ignored) {
            }
            m.put("lowStockCount", ArchiveStore.countLowStock(warn, merchantScoped ? uid : null));
            m.put("stockWarnBelow", warn);
            // 平台总管看全站用品数；商家岗只看本店（勿只给 merchantScoped 赋值）
            m.put("bookTotal", ArchiveStore.countItems(merchantScoped ? uid : null));
        } else if (!TicketStore.enabled()) {
            m.putIfAbsent("bookTotal", ArchiveStore.countItems());
        }
        if (SurveyStore.ready()) {
            try {
                m.put("surveyRecycleCards", SurveyStore.recycleCards());
            } catch (Exception ignored) {
                m.put("surveyRecycleCards", List.of());
            }
        }
        try {
            m.putAll(SiteStatStore.snapshot());
        } catch (Exception ignored) {
            m.putIfAbsent("pvToday", 0);
            m.putIfAbsent("pvTotal", 0);
        }
        // 买家/用户数：始终按注册角色重算（勿 putIfAbsent，避免 prune/异常路径留下的 0 锁死）
        String countRole = userRole == null || userRole.isBlank() ? "user" : userRole.trim();
        m.put("userTotal", UserStore.countByRole(countRole));
        m.put("charts", charts);
        return m;
    }

    private static long num(Object o) {
        if (o instanceof Number n) return n.longValue();
        if (o == null) return 0L;
        try {
            return Long.parseLong(String.valueOf(o).trim());
        } catch (Exception e) {
            return 0L;
        }
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
