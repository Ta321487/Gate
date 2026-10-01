package com.thesis.capability;

import java.util.*;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import com.thesis.service.MessageStore;

/**
 * TicketQueueOps：候补/预约晋升与 hold_ready 确认（含 SQL）。
 * package-private；TicketStore 保留门面。
 */
final class TicketQueueOps {

    private TicketQueueOps() {}

    static void tryPromoteWaitlist(long itemId) {
        if (!TicketStore.allowWaitlist || TicketStore.MODE != TicketStore.Mode.ARCHIVE || !TicketStore.useQuota || itemId <= 0) {
            return;
        }
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) return;
        int stock = item.get("stock") instanceof Number n ? n.intValue() : 0;
        if (stock <= 0) return;
        Long wid = null;
        try {
            wid = TicketSql.db().queryForObject(
                    "SELECT id FROM " + TicketStore.TICKET
                            + " WHERE " + TicketStore.itemFkColumn() + "=? AND status='waitlisted'"
                            + " ORDER BY apply_at ASC, id ASC LIMIT 1",
                    Long.class, itemId);
        } catch (Exception ignored) {
            return;
        }
        if (wid == null || wid <= 0) return;
        Map<String, Object> w = TicketRowMaps.load(wid);
        if (w == null) return;
        int need = TicketDeriveOps.rowQty(w);
        if (stock < need) return;
        int n = TicketSql.db().update(
                "UPDATE " + TicketStore.TICKET + " SET status='pending' WHERE id=? AND status='waitlisted'",
                wid);
        if (n <= 0) return;
        TicketDeriveOps.appendProgress(wid, "pending", "system", "候补晋升：名额空出，转为待审");
        try {
            String user = TicketSql.str(w.get("username"));
            if (!user.isBlank()) {
                MessageStore.send(
                        user,
                        "候补已晋升",
                        "「" + TicketNotifyOps.subjectOf(w) + "」已有名额，候补已转为待审，请等待审核。",
                        "ticket",
                        wid);
            }
            TicketNotifyOps.notifyAdminsNewTicket(wid, user, TicketNotifyOps.subjectOf(TicketDeriveOps.get(wid)));
        } catch (Exception ignored) {
            // 通知失败不影响晋升
        }
    }

    static void tryPromoteBookHold(long itemId) {
        if (!TicketStore.allowBookHold || TicketStore.MODE != TicketStore.Mode.ARCHIVE || !TicketStore.useQuota || itemId <= 0) {
            return;
        }
        if (!TicketStore.hasColumn("hold_expire_at")) {
            // 能力开了却缺过期列：禁止晋升成永不超时的 hold_ready
            return;
        }
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) return;
        int stock = item.get("stock") instanceof Number n ? n.intValue() : 0;
        if (stock <= 0) return;
        Long hid = null;
        try {
            hid = TicketSql.db().queryForObject(
                    "SELECT id FROM " + TicketStore.TICKET
                            + " WHERE " + TicketStore.itemFkColumn() + "=? AND status='held'"
                            + " ORDER BY apply_at ASC, id ASC LIMIT 1",
                    Long.class, itemId);
        } catch (Exception ignored) {
            return;
        }
        if (hid == null || hid <= 0) return;
        Map<String, Object> h = TicketRowMaps.load(hid);
        if (h == null) return;
        int need = TicketDeriveOps.rowQty(h);
        if (stock < need) return;
        ArchiveStore.adjustStock(itemId, -need);
        LocalDateTime expireAt = LocalDateTime.now().plusHours(TicketStore.holdHours);
        int n = TicketSql.db().update(
                "UPDATE " + TicketStore.TICKET + " SET status='hold_ready', hold_expire_at=? WHERE id=? AND status='held'",
                Timestamp.valueOf(expireAt), hid);
        if (n <= 0) {
            ArchiveStore.adjustStock(itemId, need);
            return;
        }
        TicketDeriveOps.appendProgress(hid, "hold_ready", "system",
                "到书通知：请于 " + TicketSql.fmt(Timestamp.valueOf(expireAt)) + " 前确认借阅");
        try {
            String user = TicketSql.str(h.get("username"));
            if (!user.isBlank()) {
                MessageStore.send(
                        user,
                        "到书通知",
                        "「" + TicketNotifyOps.subjectOf(h) + "」已到馆，请在 "
                                + TicketSql.fmt(Timestamp.valueOf(expireAt))
                                + " 前确认借阅；逾期将取消并顺延下一位。",
                        "ticket",
                        hid);
            }
        } catch (Exception ignored) {
            // 通知失败不影响晋升
        }
    }

    static void expireBookHolds() {
        if (!TicketStore.allowBookHold || !TicketStore.hasColumn("hold_expire_at")) return;
        List<Long> ids;
        try {
            ids = TicketSql.db().query(
                    "SELECT id FROM " + TicketStore.TICKET
                            + " WHERE status='hold_ready' AND hold_expire_at IS NOT NULL"
                            + " AND hold_expire_at < NOW()",
                    (rs, i) -> rs.getLong("id"));
        } catch (Exception e) {
            return;
        }
        java.util.LinkedHashSet<Long> promoteItems = new java.util.LinkedHashSet<>();
        for (Long id : ids) {
            if (id == null || id <= 0) continue;
            Map<String, Object> m = TicketRowMaps.load(id);
            if (m == null || !"hold_ready".equals(String.valueOf(m.get("status")))) continue;
            long itemId = TicketSql.toLong(m.get("bookId"));
            int n = TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET status='cancelled', hold_expire_at=NULL"
                            + " WHERE id=? AND status='hold_ready'",
                    id);
            if (n <= 0) continue;
            if (TicketStore.MODE == TicketStore.Mode.ARCHIVE && TicketStore.useQuota && itemId > 0
                    && ArchiveStore.getItemRaw(itemId) != null) {
                ArchiveStore.adjustStock(itemId, TicketDeriveOps.rowQty(m));
            }
            TicketDeriveOps.appendProgress(id, "cancelled", "system", "预约取书超时自动取消");
            try {
                String user = TicketSql.str(m.get("username"));
                if (!user.isBlank()) {
                    MessageStore.send(
                            user,
                            "预约已超时",
                            "「" + TicketNotifyOps.subjectOf(m) + "」取书时限已过，预约已取消。",
                            "ticket",
                            id);
                }
            } catch (Exception ignored) {
            }
            if (itemId > 0) promoteItems.add(itemId);
        }
        for (Long itemId : promoteItems) {
            TicketQueueOps.tryPromoteBookHold(itemId);
        }
    }

    static Map<String, Object> finalizeHoldReadyApprove(
            long ticketId,
            Map<String, Object> m,
            String note,
            String op,
            String dispatchTo,
            boolean bind) {
        if (TicketStore.useDeadline && !TicketStore.hasColumn("due_at")) {
            throw new IllegalStateException("系统未配置应还日字段，无法审批通过");
        }
        LocalDateTime approveAt = LocalDateTime.now();
        LocalDateTime dueAt = approveAt.plusDays(TicketStore.loanDays());
        Object requested = m.get("dueAt");
        if (requested != null && !String.valueOf(requested).isBlank()) {
            try {
                dueAt = TicketSql.parseDateTimeFlexible(String.valueOf(requested).trim());
            } catch (RuntimeException e) {
                throw e;
            } catch (Exception e) {
                throw new IllegalStateException("应还日期无效", e);
            }
        }
        String handler = !dispatchTo.isBlank() ? dispatchTo : op;
        boolean bindHandler = bind && !handler.isBlank() && TicketStore.hasColumn("assignee_username");
        StringBuilder sql = new StringBuilder(
                "UPDATE " + TicketStore.TICKET + " SET status='approved', approve_at=?, remark=?");
        List<Object> args = new ArrayList<>();
        args.add(Timestamp.valueOf(approveAt));
        args.add(note == null ? "" : note);
        if (bindHandler) {
            sql.append(", assignee_username=?");
            args.add(handler);
        }
        if (TicketStore.useDeadline) {
            sql.append(", due_at=?");
            args.add(Timestamp.valueOf(dueAt));
        }
        if (TicketStore.hasColumn("fine_yuan")) {
            sql.append(", fine_yuan=0");
        }
        if (TicketStore.hasColumn("remind_msg")) {
            sql.append(", remind_msg=''");
        }
        if (TicketStore.hasColumn("hold_expire_at")) {
            sql.append(", hold_expire_at=NULL");
        }
        sql.append(" WHERE id=? AND status='hold_ready'");
        args.add(ticketId);
        int n = TicketSql.db().update(sql.toString(), args.toArray());
        if (n <= 0) throw new IllegalStateException("确认借阅失败，状态已变更");
        String passCode = TicketStore.issuePassCodeIfNeeded(ticketId);
        TicketNotifyOps.notifyTicketResult(m, true, note == null ? "" : note, passCode);
        TicketDeriveOps.appendProgress(ticketId, "approved", op,
                note == null || note.isBlank() ? "确认借阅" : note);
        long approvedItemId = TicketSql.toLong(m.get("bookId"));
        int autoRejected = 0;
        if (approvedItemId > 0) {
            autoRejected = TicketStore.rejectSiblingsWhenStockGone(approvedItemId, ticketId);
        }
        Map<String, Object> out = TicketDeriveOps.get(ticketId);
        if (out != null && autoRejected > 0) {
            out.put("autoRejectedSiblings", autoRejected);
        }
        return out;
    }
}
