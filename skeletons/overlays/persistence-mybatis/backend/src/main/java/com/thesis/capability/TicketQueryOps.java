package com.thesis.capability;

import java.util.*;
import java.sql.Timestamp;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import com.thesis.service.MessageStore;
import com.thesis.service.UserStore;
import com.thesis.service.ExamStore;
import com.thesis.service.ClaimProofStore;
import com.thesis.service.OccupySpanStore;
import com.thesis.service.TimebankStore;
import com.thesis.service.BalanceLedgerStore;
import com.thesis.config.DomainResourceJson;

/**
 * TicketQueryOps：单据分页查询（含 SQL）。
 * package-private；TicketStore 保留 public 门面。
 */
final class TicketQueryOps {

    private TicketQueryOps() {}

    static Map<String, Object> page(
            String username,
            String status,
            int page,
            int size,
            String adminUid,
            boolean superAdmin,
            Boolean ratedOnly,
            Boolean todayAssigned) {
        TicketStore.expireBookHolds();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        if (username != null && !username.isBlank()) {
            TicketStore.maybeNotifyWeekReports(username);
        }
        if (TicketStore.useDeadline) {
            List<Map<String, Object>> open = TicketStore.mapper().selectOpenApprovedOverdue(TicketStore.TICKET);
            if (open != null) {
                for (Map<String, Object> raw : open) {
                    Map<String, Object> b = TicketRowMaps.shape(raw);
                    TicketStatusOps.refreshOverdue(b);
                }
            }
        }

        Map<String, Object> q = new LinkedHashMap<>();
        q.put("TicketStore.ticketTable", TicketStore.TICKET);
        if (username != null && !username.isBlank()) {
            q.put("username", username);
        } else if (!superAdmin && adminUid != null && !adminUid.isBlank() && TicketStore.hasColumn("assignee_username")) {
            // 子管可见范围：待办池全员 / 进行中仅自己 / 终态全员
            boolean historyStatus = TicketDeriveOps.isHistoryStatus(status);
            boolean todoPool = status == null || status.isBlank()
                    || "pending".equals(status)
                    || "pending_mid".equals(status)
                    || "pending_final".equals(status)
                    || "todo".equals(status);
            q.put("adminUid", adminUid);
            q.put("superAdmin", false);
            q.put("hasAssignee", true);
            q.put("historyStatus", historyStatus);
            q.put("todoPool", todoPool);
            q.put("todoPoolBlank", todoPool && (status == null || status.isBlank()));
        }
        if (status != null && !status.isBlank()) {
            if ("todo".equals(status)) {
                q.put("statusTodo", true);
            } else if ("stale".equals(status) && TicketStore.staleFollowDays > 0 && TicketStore.hasColumn("next_follow_at")) {
                // 未跟进 N 天：无下次跟进或已过期 N 天以上的未结单
                q.put("statusStale", true);
                q.put("staleBefore", LocalDateTime.now().minusDays(TicketStore.staleFollowDays).format(TicketSql.FMT));
            } else {
                q.put("statusExact", status);
            }
        }
        if (Boolean.TRUE.equals(TicketStore.ratedOnly) && TicketStore.hasColumn("rating")) {
            q.put("TicketStore.ratedOnly", true);
        }
        if (Boolean.TRUE.equals(todayAssigned) && TicketStore.todayBoard && TicketStore.hasColumn("assignee_username")) {
            String who = adminUid != null && !adminUid.isBlank() ? adminUid : username;
            if (who != null && !who.isBlank()) {
                q.put("todayAssignee", who);
                q.put("todayAssigned", true);
            }
        }
        PageHelper.startPage(page, size);
        List<Map<String, Object>> rawList = TicketStore.mapper().selectTickets(q);
        PageInfo<Map<String, Object>> pi = new PageInfo<>(rawList == null ? List.of() : rawList);
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> raw : pi.getList()) {
            list.add(TicketStatusOps.enrich(TicketRowMaps.shape(raw)));
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", pi.getTotal());
        out.put("page", page);
        out.put("size", size);
        out.put("TicketStore.staleFollowDays", TicketStore.staleFollowDays);
        out.put("TicketStore.levelSlaDays", TicketStore.levelSlaCsv());
        out.put("TicketStore.dutyNotify", TicketStore.dutyNotify);
        return out;
    }

}
