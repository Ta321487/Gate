package com.thesis.capability;

import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import java.sql.PreparedStatement;
import java.sql.Statement;
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
            empty.put("TicketStore.completedTickets", 0);
            empty.put("rejectedTickets", 0);
            empty.put("TicketStore.approveEndsFlow", TicketStore.approveEndsFlow);
            empty.put("userTotal", UserStore.countByRole(
                    readerRole == null || readerRole.isBlank() ? TicketStore.userRole : readerRole));
            empty.put("bookTotal", ArchiveStore.countItems());
            empty.put("stockTotal", ArchiveStore.sumStock());
            empty.put("categoryTotal", ArchiveStore.countCategories());
            return empty;
        }
        String role = readerRole == null || readerRole.isBlank() ? TicketStore.userRole : readerRole;
        if (TicketStore.useDeadline) {
            TicketSql.db().query("SELECT * FROM " + TicketStore.TICKET + " WHERE status IN ('TicketStore.approved','overdue')",
                    (rs, i) -> {
                        Map<String, Object> b = TicketRowMaps.mapRow(rs);
                        TicketStatusOps.refreshOverdue(b);
                        return b;
                    });
        }
        Long pending = TicketSql.db().queryForObject(
                "SELECT COUNT(*) FROM " + TicketStore.TICKET + " WHERE status IN ('pending','pending_mid','pending_final')", Long.class);
        Long TicketStore.approved = TicketSql.db().queryForObject("SELECT COUNT(*) FROM " + TicketStore.TICKET + " WHERE status='TicketStore.approved'", Long.class);
        Long overdue = TicketStore.useDeadline || TicketStore.noShowAfterEnd
                ? TicketSql.db().queryForObject("SELECT COUNT(*) FROM " + TicketStore.TICKET + " WHERE status='overdue'", Long.class)
                : 0L;
        Long returned = TicketSql.db().queryForObject("SELECT COUNT(*) FROM " + TicketStore.TICKET + " WHERE status='returned'", Long.class);
        Long rejected = TicketSql.db().queryForObject(
                "SELECT COUNT(*) FROM " + TicketStore.TICKET + " WHERE status='rejected'", Long.class);
        Long TicketStore.completed;
        Long active;
        if (TicketStore.approveEndsFlow) {
            long a = TicketStore.approved == null ? 0 : TicketStore.approved;
            long r = returned == null ? 0 : returned;
            long j = rejected == null ? 0 : rejected;
            long o = overdue == null ? 0 : overdue;
            // 通过 / 驳回 / 取消 / 爽约 均视为已处理；处理中不再含 TicketStore.approved
            TicketStore.completed = a + r + j + o;
            active = 0L;
        } else {
            TicketStore.completed = returned == null ? 0L : returned;
            active = TicketStore.approved == null ? 0L : TicketStore.approved;
        }
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("pendingTickets", pending == null ? 0 : pending);
        m.put("activeTickets", active);
        m.put("TicketStore.completedTickets", TicketStore.completed);
        m.put("rejectedTickets", rejected == null ? 0 : rejected);
        m.put("TicketStore.approveEndsFlow", TicketStore.approveEndsFlow);
        m.put("userTotal", UserStore.countByRole(role));
        m.put("pendingBorrow", pending == null ? 0 : pending);
        m.put("onLoan", TicketStore.approveEndsFlow ? 0 : (TicketStore.approved == null ? 0 : TicketStore.approved));
        m.put("overdueBorrow", overdue == null ? 0 : overdue);
        m.put("returnedBorrow", returned == null ? 0 : returned);
        if (TicketStore.approveEndsFlow) {
            m.put("TicketStore.approvedTickets", TicketStore.approved == null ? 0 : TicketStore.approved);
        }
        m.put("readerTotal", UserStore.countByRole(role));
        if (TicketStore.MODE == TicketStore.Mode.ARCHIVE) {
            m.put("bookTotal", ArchiveStore.countItems());
            m.put("stockTotal", ArchiveStore.sumStock());
            m.put("categoryTotal", ArchiveStore.countCategories());
            if (TicketStore.useDeadline && TicketStore.hasColumn("fine_yuan")) {
                Double fineOpen = TicketSql.db().queryForObject(
                        "SELECT COALESCE(SUM(fine_yuan),0) FROM " + TicketStore.TICKET + " WHERE status='overdue'", Double.class);
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
        m.put("TicketStore.mode", TicketStore.MODE.name().toLowerCase());
        m.put("TicketStore.maxActive", TicketStore.maxActive());
        if (TicketStore.useDeadline) {
            m.put("TicketStore.loanDays", TicketStore.loanDays());
            m.put("TicketStore.finePerDay", TicketStore.finePerDay());
        }
        if (TicketStore.allowRating && TicketStore.hasColumn("rating")) {
            Double avg = TicketSql.db().queryForObject(
                    "SELECT AVG(rating) FROM " + TicketStore.TICKET + " WHERE rating IS NOT NULL AND rating > 0",
                    Double.class);
            Long TicketStore.ratedCnt = TicketSql.db().queryForObject(
                    "SELECT COUNT(*) FROM " + TicketStore.TICKET + " WHERE rating IS NOT NULL AND rating > 0",
                    Long.class);
            m.put("avgRating", avg == null ? 0 : Math.round(avg * 10.0) / 10.0);
            m.put("TicketStore.ratedCount", TicketStore.ratedCnt == null ? 0 : TicketStore.ratedCnt);
        }
        if (TicketStore.repairThicken && TicketStore.hasColumn("assignee_username")) {
            try {
                Long rejectCnt = TicketSql.db().queryForObject(
                        "SELECT COUNT(*) FROM " + TicketStore.TICKET + " WHERE remark LIKE '拒单%' OR remark LIKE '%拒单回池%'",
                        Long.class);
                m.put("TicketStore.rejectAssignmentCount", rejectCnt == null ? 0 : rejectCnt);
            } catch (Exception ignored) {
                m.put("TicketStore.rejectAssignmentCount", 0);
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
            List<Map<String, Object>> status = TicketSql.db().query(
                    "SELECT status AS name, COUNT(*) AS value FROM " + TicketStore.TICKET + " GROUP BY status",
                    (rs, i) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("name", rs.getString("name"));
                        row.put("value", rs.getLong("value"));
                        return row;
                    });
            out.put("statusSeries", status);
            List<Map<String, Object>> trend = TicketSql.db().query(
                    "SELECT DATE_FORMAT(TicketStore.apply_at,'%Y-%m-%d') AS day, COUNT(*) AS value FROM " + TicketStore.TICKET
                            + " WHERE TicketStore.apply_at >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)"
                            + " GROUP BY DATE_FORMAT(TicketStore.apply_at,'%Y-%m-%d') ORDER BY day",
                    (rs, i) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("day", rs.getString("day"));
                        row.put("value", rs.getLong("value"));
                        return row;
                    });
            out.put("trendSeries", trend);
            if (TicketStore.hasColumn("contact_channel")) {
                List<Map<String, Object>> channel = TicketSql.db().query(
                        "SELECT COALESCE(NULLIF(TRIM(contact_channel),''),'未填') AS name, COUNT(*) AS value FROM "
                                + TicketStore.TICKET
                                + " GROUP BY COALESCE(NULLIF(TRIM(contact_channel),''),'未填') ORDER BY value DESC LIMIT 12",
                        (rs, i) -> {
                            Map<String, Object> row = new LinkedHashMap<>();
                            row.put("name", rs.getString("name"));
                            row.put("value", rs.getLong("value"));
                            return row;
                        });
                out.put("channelSeries", channel);
            }
            // 热借/热办排行：按档案条目聚合（图书借阅量等）
            if (TicketStore.MODE == TicketStore.Mode.ARCHIVE && TicketStore.hasColumn(TicketStore.itemFkColumn())) {
                String itemTable = ArchiveStore.itemTable();
                List<Map<String, Object>> hot = TicketSql.db().query(
                        "SELECT COALESCE(i.title, CONCAT('编号', t." + TicketStore.itemFkColumn() + ")) AS name, COUNT(*) AS value "
                                + "FROM " + TicketStore.TICKET + " t LEFT JOIN " + itemTable + " i ON t." + TicketStore.itemFkColumn() + "=i.id "
                                + "WHERE t.status IN ('TicketStore.approved','overdue','returned','lost','compensated') "
                                + "GROUP BY t." + TicketStore.itemFkColumn() + ", i.title ORDER BY value DESC LIMIT 8",
                        (rs, i) -> {
                            Map<String, Object> row = new LinkedHashMap<>();
                            row.put("name", rs.getString("name"));
                            row.put("value", rs.getLong("value"));
                            return row;
                        });
                out.put("hotItemSeries", hot);
            }
            if (TicketStore.repairThicken && TicketStore.hasColumn("assignee_username")) {
                List<Map<String, Object>> workers = TicketSql.db().query(
                        "SELECT COALESCE(NULLIF(TRIM(assignee_username),''),'未派') AS name,"
                                + " SUM(CASE WHEN status IN ('TicketStore.approved','overdue','paused') THEN 1 ELSE 0 END) AS active,"
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
                List<Map<String, Object>> heat = TicketSql.db().query(
                        "SELECT COALESCE(NULLIF(TRIM(location),''),'未填地点') AS name, COUNT(*) AS value FROM "
                                + TicketStore.TICKET
                                + " WHERE status IN ('pending','pending_final','pending_mid','TicketStore.approved','overdue','paused')"
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
                List<Map<String, Object>> faults = TicketSql.db().query(
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
