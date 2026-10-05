package com.thesis.capability;

import java.util.*;

/**
 * TicketReviseOps：草稿 / 退回修改 / 重新提交（含 SQL）。
 * package-private；TicketStore 保留 public 门面。
 */
final class TicketReviseOps {

    private TicketReviseOps() {}

    static Map<String, Object> saveDraft(long ticketId, String username) {
        if (!TicketStore.allowTicketDraft) throw new IllegalStateException("当前未开启草稿报修");
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!TicketSql.str(m.get("username")).equals(username)) {
            throw new IllegalStateException("只能保存自己的草稿");
        }
        String st = String.valueOf(m.get("status"));
        if (!"pending".equals(st) && !"draft".equals(st)) {
            throw new IllegalStateException("仅新建单据可存为草稿");
        }
        TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET status='draft' WHERE id=?", ticketId);
        TicketDeriveOps.appendProgress(ticketId, "draft", username, "保存草稿");
        return TicketDeriveOps.get(ticketId);
    }

    static Map<String, Object> returnForRevise(long ticketId, String op, String note) {
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        String st = String.valueOf(m.get("status"));
        if (!"pending".equals(st) && !"pending_mid".equals(st) && !"pending_final".equals(st)) {
            throw new IllegalStateException("仅待审单据可退回修改");
        }
        int used = reviseCountOf(m);
        if (TicketStore.maxReviseTimes > 0 && used >= TicketStore.maxReviseTimes) {
            throw new IllegalStateException(
                    "退回修改次数已达上限（" + TicketStore.maxReviseTimes + " 次），请直接驳回或联系管理员。");
        }
        int next = used + 1;
        String reason = note == null || note.isBlank() ? ("退回修改第 " + next + " 次") : note.trim();
        if (TicketStore.hasColumn("revise_count")) {
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET status='returned', revise_count=? WHERE id=?",
                    next, ticketId);
        } else {
            TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET status='returned' WHERE id=?", ticketId);
        }
        TicketDeriveOps.appendProgress(ticketId, "returned", op == null ? "" : op, reason);
        return TicketDeriveOps.get(ticketId);
    }

    static Map<String, Object> resubmit(long ticketId, String username, String remark) {
        return resubmit(ticketId, username, remark, null);
    }

    static Map<String, Object> resubmit(long ticketId, String username, String remark, String attachUrl) {
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!String.valueOf(m.get("username")).equals(username)) {
            throw new IllegalStateException("只能重新提交自己的单据");
        }
        if (!"returned".equals(String.valueOf(m.get("status")))) {
            throw new IllegalStateException("仅被退回的单据可重新提交");
        }
        if (TicketStore.maxReviseTimes > 0 && reviseCountOf(m) >= TicketStore.maxReviseTimes) {
            throw new IllegalStateException("修改次数已达上限（" + TicketStore.maxReviseTimes + " 次），请联系管理员。");
        }
        String attach = attachUrl == null ? "" : attachUrl.trim();
        if (TicketStore.allowAttachKeepOld && TicketStore.hasColumn("attach_url") && !attach.isBlank()) {
            TicketGuardOps.keepAttachHistory(ticketId, TicketSql.str(m.get("attachUrl")), attach);
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET status='pending', attach_url=? WHERE id=?",
                    attach.length() > 255 ? attach.substring(0, 255) : attach, ticketId);
        } else {
            TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET status='pending' WHERE id=?", ticketId);
        }
        TicketDeriveOps.appendProgress(ticketId, "pending", username,
                remark == null || remark.isBlank() ? "重新提交" : remark.trim());
        return TicketDeriveOps.get(ticketId);
    }

    static int reviseCountOf(Map<String, Object> m) {
        return m.get("reviseCount") instanceof Number n ? n.intValue() : 0;
    }
}
