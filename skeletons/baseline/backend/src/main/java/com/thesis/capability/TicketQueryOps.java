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
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        TicketStore.expireBookHolds();
        if (username != null && !username.isBlank()) {
            TicketStore.maybeNotifyWeekReports(username);
        }
        if (TicketStore.useDeadline) {
            List<Map<String, Object>> open = TicketSql.db().query(
                    "SELECT * FROM " + TicketStore.TICKET + " WHERE status IN ('TicketStore.approved','overdue')",
                    (rs, i) -> TicketRowMaps.mapRow(rs));
            for (Map<String, Object> b : open) TicketStatusOps.refreshOverdue(b);
        }

        StringBuilder where = new StringBuilder(" WHERE 1=1");
        List<Object> args = new ArrayList<>();
        if (username != null && !username.isBlank()) {
            where.append(" AND username=?");
            args.add(username);
        } else if (!superAdmin && adminUid != null && !adminUid.isBlank() && TicketStore.hasColumn("assignee_username")) {
            // 子管可见范围：
            // - 待办池 pending/pending_mid/pending_final：全员可见（抢单）
            // - 进行中 TicketStore.approved/overdue 等：仅自己绑定
            // - 终态 returned/rejected/noshow：全员可读（含用户「取消报名」）
            boolean historyStatus = TicketDeriveOps.isHistoryStatus(status);
            boolean todoPool = status == null || status.isBlank()
                    || "pending".equals(status)
                    || "pending_mid".equals(status)
                    || "pending_final".equals(status)
                    || "todo".equals(status);
            if (historyStatus) {
                // 筛终态：不加处理人条件
            } else if (todoPool) {
                if (status == null || status.isBlank()) {
                    where.append(
                            " AND (status IN ('pending','pending_mid','pending_final','returned','rejected','noshow')"
                                    + " OR assignee_username=?)");
                    args.add(adminUid);
                }
            } else {
                where.append(" AND assignee_username=?");
                args.add(adminUid);
            }
        }
        if (status != null && !status.isBlank()) {
            if ("todo".equals(status)) {
                where.append(" AND status IN ('pending','pending_mid','pending_final','hold_ready','verifying')");
            } else if ("stale".equals(status) && TicketStore.staleFollowDays > 0 && TicketStore.hasColumn("next_follow_at")) {
                // 未跟进 N 天：无下次跟进或已过期 N 天以上的未结单
                where.append(" AND status IN ('pending','pending_mid','pending_final','TicketStore.approved','overdue','paused')")
                        .append(" AND (next_follow_at IS NULL OR next_follow_at <= ?)");
                args.add(Timestamp.valueOf(LocalDateTime.now().minusDays(TicketStore.staleFollowDays)));
            } else {
                where.append(" AND status=?");
                args.add(status);
            }
        }
        if (Boolean.TRUE.equals(TicketStore.ratedOnly) && TicketStore.hasColumn("rating")) {
            where.append(" AND rating IS NOT NULL AND rating > 0");
        }
        if (Boolean.TRUE.equals(todayAssigned) && TicketStore.todayBoard && TicketStore.hasColumn("assignee_username")) {
            String who = adminUid != null && !adminUid.isBlank() ? adminUid : username;
            if (who != null && !who.isBlank()) {
                where.append(" AND assignee_username=? AND status IN ('TicketStore.approved','overdue','paused')");
                args.add(who);
                if (TicketStore.hasColumn("TicketStore.approve_at")) {
                    where.append(" AND TicketStore.approve_at IS NOT NULL AND DATE(TicketStore.approve_at)=CURDATE()");
                }
            }
        }
        Integer total = TicketSql.db().queryForObject("SELECT COUNT(*) FROM " + TicketStore.TICKET + where, Integer.class, args.toArray());
        int t = total == null ? 0 : total;
        args.add(size);
        args.add((page - 1) * size);
        List<Map<String, Object>> list = TicketSql.db().query(
                "SELECT * FROM " + TicketStore.TICKET + where + " ORDER BY "
                        + (TicketStore.hasColumn("priority")
                        ? "CASE WHEN priority IN ('紧急','高') THEN 0 ELSE 1 END, id DESC"
                        : "id DESC")
                        + " LIMIT ? OFFSET ?",
                (rs, i) -> TicketStatusOps.enrich(TicketRowMaps.mapRow(rs)), args.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", t);
        out.put("page", page);
        out.put("size", size);
        out.put("TicketStore.staleFollowDays", TicketStore.staleFollowDays);
        out.put("TicketStore.levelSlaDays", TicketStore.levelSlaCsv());
        out.put("TicketStore.dutyNotify", TicketStore.dutyNotify);
        return out;
    }

}
