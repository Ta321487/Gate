package com.thesis.capability;

import com.thesis.service.UserStore;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.LinkedHashMap;
import java.util.Map;

/** Overdue / no-show / enrich helpers (package-private). */
final class TicketStatusOps {

    private TicketStatusOps() {}

    static Map<String, Object> enrich(Map<String, Object> b) {
        Map<String, Object> m = new LinkedHashMap<>(b);
        touchTicketStatus(m);
        if (TicketStore.useDeadline) {
            m.put("loanDays", TicketStore.LOAN_DAYS);
            m.put("finePerDay", TicketStore.FINE_PER_DAY);
        }
        if (TicketStore.noShowAfterEnd && TicketStore.noShowPenaltyYuan > 0) {
            m.put("TicketStore.noShowPenaltyYuan", TicketStore.noShowPenaltyYuan);
        }
        m.put("mode", TicketStore.MODE.name().toLowerCase());
        Object u = m.get("username");
        if (u != null && !String.valueOf(u).isBlank()) {
            m.put("displayName", UserStore.displayName(String.valueOf(u)));
        }
        return m;
    }

    /** 列表/详情时推进逾期或爽约状态 */
    static void touchTicketStatus(Map<String, Object> m) {
        if (m == null) return;
        if (TicketStore.useDeadline) refreshOverdue(m);
        if (TicketStore.noShowAfterEnd) refreshNoShow(m);
    }

    static void refreshOverdue(Map<String, Object> m) {
        if (!TicketStore.useDeadline) return;
        String st = String.valueOf(m.get("status"));
        if (!"approved".equals(st) && !"overdue".equals(st)) return;
        Object due = m.get("dueAt");
        if (due == null || String.valueOf(due).isBlank()) return;
        LocalDateTime dueAt = LocalDateTime.parse(String.valueOf(due), TicketSql.FMT);
        if (LocalDateTime.now().isAfter(dueAt)) {
            m.put("status", "overdue");
            applyFineAndRemind(m, false);
            persistFine(m);
        }
    }

    /**
     * 活动结束仍未签到 → overdue（文案多为「爽约」）+ 可选固定费用。
     * 与借还逾期互斥场景：活动域通常 TicketStore.useDeadline=false。
     */
    static void refreshNoShow(Map<String, Object> m) {
        if (!TicketStore.noShowAfterEnd || !TicketStore.allowCheckin) return;
        String st = String.valueOf(m.get("status"));
        if (!"approved".equals(st)) return;
        Object checked = m.get("checkedInAt");
        if (checked != null && !String.valueOf(checked).isBlank()) return;
        long itemId = TicketSql.toLong(m.get("bookId"));
        if (itemId <= 0) itemId = TicketSql.toLong(m.get("itemId"));
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) return;
        String endStr = TicketSql.str(item.get("endAt"));
        if (endStr.isBlank()) return;
        LocalDateTime endAt;
        try {
            endAt = LocalDateTime.parse(endStr.length() == 10 ? endStr + " 23:59:59" : endStr, TicketSql.FMT);
        } catch (Exception e) {
            return;
        }
        if (!LocalDateTime.now().isAfter(endAt)) return;
        m.put("status", "overdue");
        double penalty = TicketStore.noShowPenaltyYuan;
        m.put("fineYuan", penalty);
        String overdueLab = TicketCopy.stateLabel("overdue", "爽约");
        String msg = penalty > 0
                ? TicketCopy.archiveNoun() + "已结束且未签到，记为" + overdueLab + "；费用 " + penalty + " 元。"
                : TicketCopy.archiveNoun() + "已结束且未签到，记为" + overdueLab + "。";
        m.put("remindMsg", msg);
        persistFine(m);
        try {
            TicketStore.appendProgress(TicketSql.toLong(m.get("id")), "overdue", "system", msg);
        } catch (Exception ignored) {
        }
    }

    static void applyFineAndRemind(Map<String, Object> m, boolean forceRemind) {
        double fine = calcFineYuan(m);
        m.put("fineYuan", fine);
        String msg;
        if (fine > 0) {
            msg = "已逾期，请尽快处理。当前预估费用 " + fine + " 元（" + TicketStore.FINE_PER_DAY + " 元/天）。";
        } else {
            msg = "请于到期日前处理，逾期将按 " + TicketStore.FINE_PER_DAY + " 元/天计费。";
        }
        if (forceRemind) {
            m.put("remindedAt", TicketSql.now());
            m.put("remindMsg", "【催办】" + msg);
        } else {
            m.put("remindMsg", msg);
        }
    }

    static void persistFine(Map<String, Object> m) {
        Object reminded = m.get("remindedAt");
        Timestamp remindedTs = null;
        if (reminded != null && !String.valueOf(reminded).isBlank()) {
            remindedTs = Timestamp.valueOf(LocalDateTime.parse(String.valueOf(reminded), TicketSql.FMT));
        }
        TicketSql.db().update(
                "UPDATE " + TicketStore.TICKET + " SET status=?, fine_yuan=?, remind_msg=?, reminded_at=? WHERE id=?",
                m.get("status"), TicketSql.toDouble(m.get("fineYuan")),
                String.valueOf(m.get("remindMsg") == null ? "" : m.get("remindMsg")),
                remindedTs, m.get("id"));
    }

    static double calcFineYuan(Map<String, Object> m) {
        Object due = m.get("dueAt");
        if (due == null || String.valueOf(due).isBlank()) return 0.0;
        LocalDateTime dueAt = LocalDateTime.parse(String.valueOf(due), TicketSql.FMT);
        LocalDateTime end = m.get("returnAt") != null && !String.valueOf(m.get("returnAt")).isBlank()
                ? LocalDateTime.parse(String.valueOf(m.get("returnAt")), TicketSql.FMT)
                : LocalDateTime.now();
        long days = ChronoUnit.DAYS.between(dueAt.toLocalDate(), end.toLocalDate());
        if (days <= 0) return 0.0;
        return Math.round(days * TicketStore.FINE_PER_DAY * 10.0) / 10.0;
    }


}
