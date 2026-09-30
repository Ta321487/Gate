package com.thesis.capability;

import com.thesis.config.MbSql;
import com.thesis.config.MybatisSupport;
import com.thesis.mapper.TicketMapper;
import com.thesis.service.UserStore;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.LinkedHashMap;
import java.util.Map;

/** Overdue / no-show / enrich helpers (package-private). */
final class TicketStatusOps {

    private TicketStatusOps() {}

    private static TicketMapper mapper() {
        return MybatisSupport.mapper(TicketMapper.class);
    }

    /** 尚未 Mapper 化的原生 SQL 片段（与 MyBatis 共用库）。 */
    private static MbSql db() {
        return MybatisSupport.db();
    }

    static Map<String, Object> enrich(Map<String, Object> b) {
        Map<String, Object> m = new LinkedHashMap<>(b);
        touchTicketStatus(m);
        m.put("maxActive", TicketStore.maxActive());
        if (TicketStore.useDeadline) {
            m.put("loanDays", TicketStore.loanDays());
            m.put("finePerDay", TicketStore.finePerDay());
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
        if (TicketStore.useDeadline) {
            refreshOverdue(m);
            maybeNotifyDueSoon(m);
        }
        maybeNotifyFollowSoon(m);
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
            markEverOverdue(m);
            maybeEscalateRepairOverdue(m);
        }
    }

/** 报修超时：升紧急 + 可选通知主管（站内信）。 */
    static void maybeEscalateRepairOverdue(Map<String, Object> m) {
        if (!TicketStore.escalateOnOverdue && !TicketStore.notifySupervisorOnOverdue) return;
        long id = TicketSql.toLong(m.get("id"));
        if (id <= 0) return;
        if (TicketStore.escalateOnOverdue && TicketStore.hasColumn("priority")) {
            String p = TicketSql.str(m.get("priority"));
            if (!"紧急".equals(p) && !"高".equals(p)) {
                db().update(
                        "UPDATE " + TicketStore.TICKET + " SET priority='紧急' WHERE id=?", id);
                m.put("priority", "紧急");
                TicketStore.appendProgress(id, "overdue", "system", "超时自动升为紧急");
            }
        }
        if (TicketStore.notifySupervisorOnOverdue) {
            String title = TicketSql.str(m.get("title"));
            if (title.isBlank()) title = "单据#" + id;
            try {
                com.thesis.service.MessageStore.notifyAdmins(
                        "维修超时",
                        "「" + title + "」已超时，请主管关注跟进。",
                        "ticket",
                        id);
            } catch (Exception ignored) {
            }
        }
    }

        /** 应还日前 N 天站内提前催还（每单一回）。 */
    static void maybeNotifyDueSoon(Map<String, Object> m) {
        if (TicketStore.dueSoonDays <= 0) return;
        if (!"approved".equals(String.valueOf(m.get("status")))) return;
        if (!TicketStore.hasColumn("due_soon_notified_at")) return;
        Object notified = m.get("dueSoonNotifiedAt");
        if (notified != null && !String.valueOf(notified).isBlank()) return;
        Object due = m.get("dueAt");
        if (due == null || String.valueOf(due).isBlank()) return;
        LocalDateTime dueAt;
        try {
            dueAt = LocalDateTime.parse(String.valueOf(due), TicketSql.FMT);
        } catch (Exception e) {
            return;
        }
        LocalDateTime now = LocalDateTime.now();
        if (!now.isBefore(dueAt)) return;
        long daysLeft = ChronoUnit.DAYS.between(now.toLocalDate(), dueAt.toLocalDate());
        if (daysLeft > TicketStore.dueSoonDays) return;
        String owner = TicketSql.str(m.get("username"));
        if (owner.isBlank()) return;
        long id = TicketSql.toLong(m.get("id"));
        String title = TicketSql.str(m.get("title"));
        if (title.isBlank()) title = TicketSql.str(m.get("bookTitle"));
        if (title.isBlank()) title = "单据#" + id;
        String body = "「" + title + "」将于 " + TicketSql.fmt(dueAt) + " 到期，请按时归还。";
        try {
            com.thesis.service.MessageStore.send(owner, "即将到期提醒", body, "ticket", id);
        } catch (Exception ignored) {
        }
        Timestamp ts = Timestamp.valueOf(now);
        mapper().updateDueSoonNotified(TicketStore.TICKET, id, ts);
        m.put("dueSoonNotifiedAt", TicketSql.fmt(now));
    }

    /** 下次跟进日前 N 天站内提醒（每单一回；不依赖借还 deadline）。 */
    static void maybeNotifyFollowSoon(Map<String, Object> m) {
        if (TicketStore.followRemindDays <= 0) return;
        if (!TicketStore.hasColumn("follow_soon_notified_at")) return;
        Object notified = m.get("followSoonNotifiedAt");
        if (notified != null && !String.valueOf(notified).isBlank()) return;
        Object next = m.get("nextFollowAt");
        if (next == null || String.valueOf(next).isBlank()) return;
        LocalDateTime nextAt;
        try {
            nextAt = LocalDateTime.parse(String.valueOf(next), TicketSql.FMT);
        } catch (Exception e) {
            return;
        }
        LocalDateTime now = LocalDateTime.now();
        if (!now.isBefore(nextAt)) return;
        long daysLeft = ChronoUnit.DAYS.between(now.toLocalDate(), nextAt.toLocalDate());
        if (daysLeft > TicketStore.followRemindDays) return;
        String owner = TicketSql.str(m.get("username"));
        if (owner.isBlank()) return;
        long id = TicketSql.toLong(m.get("id"));
        String title = TicketSql.str(m.get("title"));
        if (title.isBlank()) title = TicketSql.str(m.get("bookTitle"));
        if (title.isBlank()) title = "单据#" + id;
        String body = "「" + title + "」将于 " + TicketSql.fmt(nextAt) + " 到期跟进，请及时处理。";
        try {
            com.thesis.service.MessageStore.send(owner, "跟进提醒", body, "ticket", id);
        } catch (Exception ignored) {
        }
        Timestamp ts = Timestamp.valueOf(now);
        mapper().updateFollowSoonNotified(TicketStore.TICKET, id, ts);
        m.put("followSoonNotifiedAt", TicketSql.fmt(now));
    }

    static void markEverOverdue(Map<String, Object> m) {
        if (TicketStore.maxOverdueTimes <= 0) return;
        if (!TicketStore.hasColumn("ever_overdue")) return;
        Object flag = m.get("everOverdue");
        if (flag instanceof Number n && n.intValue() == 1) return;
        if ("1".equals(String.valueOf(flag))) return;
        long id = TicketSql.toLong(m.get("id"));
        if (id <= 0) return;
        mapper().updateEverOverdue(TicketStore.TICKET, id);
        m.put("everOverdue", 1);
        String owner = TicketSql.str(m.get("username"));
        if (!owner.isBlank()) {
            BorrowCreditStore.penalizeOverdue(owner, id);
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
            msg = "已逾期，请尽快处理。当前预估费用 " + fine + " 元（" + TicketStore.finePerDay() + " 元/天）。";
        } else {
            msg = "请于到期日前处理，逾期将按 " + TicketStore.finePerDay() + " 元/天计费。";
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
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("ticketTable", TicketStore.TICKET);
        row.put("id", m.get("id"));
        row.put("status", m.get("status"));
        row.put("fineYuan", TicketSql.toDouble(m.get("fineYuan")));
        row.put("remindMsg", String.valueOf(m.get("remindMsg") == null ? "" : m.get("remindMsg")));
        row.put("remindedAt", remindedTs);
        mapper().updateFinePersist(row);
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
        return Math.round(days * TicketStore.finePerDay() * 10.0) / 10.0;
    }
}
