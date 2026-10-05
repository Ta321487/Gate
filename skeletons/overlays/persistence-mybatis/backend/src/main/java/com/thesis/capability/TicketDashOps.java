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
 * TicketDashOps：看板与图表统计（含 SQL）。
 * package-private；TicketStore 保留 public 门面。
 */
final class TicketDashOps {

    private TicketDashOps() {}

    static Map<String, Object> dashboard(String readerRole) {
        if (!TicketStore.enabled) {
            Map<String, Object> empty = new LinkedHashMap<>();
            empty.put("pendingTickets", 0);
            empty.put("activeTickets", 0);
            empty.put("completedTickets", 0);
            empty.put("rejectedTickets", 0);
            empty.put("approveEndsFlow", TicketStore.approveEndsFlow);
            empty.put("userTotal", UserStore.countByRole(
                    readerRole == null || readerRole.isBlank() ? TicketStore.userRole : readerRole));
            empty.put("bookTotal", ArchiveStore.countItems());
            empty.put("stockTotal", ArchiveStore.sumStock());
            empty.put("categoryTotal", ArchiveStore.countCategories());
            return empty;
        }
        String role = readerRole == null || readerRole.isBlank() ? TicketStore.userRole : readerRole;
        if (TicketStore.useDeadline) {
            List<Map<String, Object>> open = TicketStore.mapper().selectOpenApprovedOverdue(TicketStore.TICKET);
            if (open != null) {
                for (Map<String, Object> raw : open) {
                    Map<String, Object> b = TicketRowMaps.shape(raw);
                    TicketStatusOps.refreshOverdue(b);
                }
            }
        }
        Long pending = TicketStore.mapper().countPending(TicketStore.TICKET);
        Long approved = TicketStore.mapper().countByStatus(TicketStore.TICKET, "approved");
        Long overdue = TicketStore.useDeadline || TicketStore.noShowAfterEnd
                ? TicketStore.mapper().countByStatus(TicketStore.TICKET, "overdue")
                : 0L;
        Long returned = TicketStore.mapper().countByStatus(TicketStore.TICKET, "returned");
        Long rejected = TicketStore.mapper().countByStatus(TicketStore.TICKET, "rejected");
        Long completed;
        Long active;
        if (TicketStore.approveEndsFlow) {
            long a = approved == null ? 0 : approved;
            long r = returned == null ? 0 : returned;
            long j = rejected == null ? 0 : rejected;
            long o = overdue == null ? 0 : overdue;
            // 通过 / 驳回 / 取消 / 爽约 均视为已处理；处理中不再含 approved
            completed = a + r + j + o;
            active = 0L;
        } else {
            completed = returned == null ? 0L : returned;
            active = approved == null ? 0L : approved;
        }
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("pendingTickets", pending == null ? 0 : pending);
        m.put("activeTickets", active);
        m.put("completedTickets", completed);
        m.put("rejectedTickets", rejected == null ? 0 : rejected);
        m.put("approveEndsFlow", TicketStore.approveEndsFlow);
        m.put("userTotal", UserStore.countByRole(role));
        m.put("pendingBorrow", pending == null ? 0 : pending);
        m.put("onLoan", TicketStore.approveEndsFlow ? 0 : (approved == null ? 0 : approved));
        m.put("overdueBorrow", overdue == null ? 0 : overdue);
        m.put("returnedBorrow", returned == null ? 0 : returned);
        if (TicketStore.approveEndsFlow) {
            m.put("approvedTickets", approved == null ? 0 : approved);
        }
        m.put("readerTotal", UserStore.countByRole(role));
        if (TicketStore.MODE == TicketStore.Mode.ARCHIVE) {
            m.put("bookTotal", ArchiveStore.countItems());
            m.put("stockTotal", ArchiveStore.sumStock());
            m.put("categoryTotal", ArchiveStore.countCategories());
            if (TicketStore.useDeadline && TicketStore.hasColumn("fine_yuan")) {
                Double fineOpen = TicketStore.mapper().sumOpenFine(TicketStore.TICKET);
                m.put("openFineYuan", Math.round((fineOpen == null ? 0 : fineOpen) * 10.0) / 10.0);
            } else {
                m.put("openFineYuan", 0);
            }
        } else {
            m.put("bookTotal", 0);
            m.put("stockTotal", 0);
            m.put("categoryTotal", 0);
            m.put("openFineYuan", 0);
        }
        m.put("mode", TicketStore.MODE.name().toLowerCase());
        m.put("maxActive", TicketStore.maxActive());
        if (TicketStore.useDeadline) {
            m.put("loanDays", TicketStore.loanDays());
            m.put("finePerDay", TicketStore.finePerDay());
        }
        if (TicketStore.allowRating && TicketStore.hasColumn("rating")) {
            Double avg = TicketStore.mapper().avgRating(TicketStore.TICKET);
            Long ratedCnt = TicketStore.mapper().countRated(TicketStore.TICKET);
            m.put("avgRating", avg == null ? 0 : Math.round(avg * 10.0) / 10.0);
            m.put("ratedCount", ratedCnt == null ? 0 : ratedCnt);
        }
        if (TicketStore.repairThicken && TicketStore.hasColumn("assignee_username")) {
            try {
                Long rejectCnt = TicketStore.db().queryForObject(
                        "SELECT COUNT(*) FROM " + TicketStore.TICKET + " WHERE remark LIKE '拒单%' OR remark LIKE '%拒单回池%'",
                        Long.class);
                m.put("rejectAssignmentCount", rejectCnt == null ? 0 : rejectCnt);
            } catch (Exception ignored) {
                m.put("rejectAssignmentCount", 0);
            }
        }
        return m;
    }

    static Map<String, Object> chartStats() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("statusSeries", List.of());
        out.put("trendSeries", List.of());
        out.put("channelSeries", List.of());
        if (!TicketStore.enabled) return out;
        try {
            List<Map<String, Object>> status = TicketStore.mapper().selectStatusSeries(TicketStore.TICKET);
            out.put("statusSeries", status == null ? List.of() : status);
            List<Map<String, Object>> trend = TicketStore.mapper().selectTrendSeries(TicketStore.TICKET);
            out.put("trendSeries", trend == null ? List.of() : trend);
            if (TicketStore.hasColumn("contact_channel")) {
                List<Map<String, Object>> channel = TicketStore.mapper().selectChannelSeries(TicketStore.TICKET);
                out.put("channelSeries", channel == null ? List.of() : channel);
            }
            // 热借/热办排行：按档案条目聚合（图书借阅量等）
            if (TicketStore.MODE == TicketStore.Mode.ARCHIVE && TicketStore.hasColumn(TicketStore.itemFkColumn())) {
                String itemTable = ArchiveStore.itemTable();
                List<Map<String, Object>> hot = TicketStore.mapper().selectHotItemSeries(TicketStore.TICKET, itemTable, TicketStore.itemFkColumn());
                out.put("hotItemSeries", hot == null ? List.of() : hot);
            }
            if (TicketStore.repairThicken && TicketStore.hasColumn("assignee_username")) {
                List<Map<String, Object>> workers = TicketStore.db().query(
                        "SELECT COALESCE(NULLIF(TRIM(assignee_username),''),'未派') AS name,"
                                + " SUM(CASE WHEN status IN ('approved','overdue','paused') THEN 1 ELSE 0 END) AS active,"
                                + " SUM(CASE WHEN status='returned' THEN 1 ELSE 0 END) AS done"
                                + " FROM " + TicketStore.TICKET
                                + " GROUP BY COALESCE(NULLIF(TRIM(assignee_username),''),'未派')"
                                + " ORDER BY done DESC, active DESC LIMIT 12",
                        (rs, i) -> {
                            Map<String, Object> row = new LinkedHashMap<>();
                            row.put("name", rs.getString("name"));
                            row.put("active", rs.getLong("active"));
                            row.put("done", rs.getLong("done"));
                            row.put("value", rs.getLong("done"));
                            return row;
                        });
                out.put("workerSeries", workers);
            }
            if (TicketStore.repairThicken && TicketStore.MODE == TicketStore.Mode.STANDALONE && TicketStore.hasColumn("location")) {
                List<Map<String, Object>> heat = TicketStore.db().query(
                        "SELECT COALESCE(NULLIF(TRIM(location),''),'未填地点') AS name, COUNT(*) AS value FROM "
                                + TicketStore.TICKET
                                + " WHERE status IN ('pending','pending_final','pending_mid','approved','overdue','paused')"
                                + " GROUP BY COALESCE(NULLIF(TRIM(location),''),'未填地点') ORDER BY value DESC LIMIT 12",
                        (rs, i) -> {
                            Map<String, Object> row = new LinkedHashMap<>();
                            row.put("name", rs.getString("name"));
                            row.put("value", rs.getLong("value"));
                            return row;
                        });
                out.put("locationHeatSeries", heat);
            }
            if (TicketStore.repairThicken && TicketStore.hasColumn("fault_reason")) {
                List<Map<String, Object>> faults = TicketStore.db().query(
                        "SELECT COALESCE(NULLIF(TRIM(fault_reason),''),'未填') AS name, COUNT(*) AS value FROM "
                                + TicketStore.TICKET
                                + " WHERE fault_reason IS NOT NULL AND TRIM(fault_reason)<>''"
                                + " GROUP BY COALESCE(NULLIF(TRIM(fault_reason),''),'未填') ORDER BY value DESC LIMIT 12",
                        (rs, i) -> {
                            Map<String, Object> row = new LinkedHashMap<>();
                            row.put("name", rs.getString("name"));
                            row.put("value", rs.getLong("value"));
                            return row;
                        });
                out.put("faultReasonSeries", faults);
            }
        } catch (Exception ignored) {
            // 表结构差异时不炸工作台
        }
        return out;
    }

}
