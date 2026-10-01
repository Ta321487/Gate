package com.thesis.capability;

import java.util.*;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import com.thesis.service.MessageStore;

/**
 * TicketApproveOps：审核状态机（含 SQL）。
 * package-private；TicketStore 保留 public 门面。
 */
final class TicketApproveOps {

    private TicketApproveOps() {}

static Map<String, Object> approve(long ticketId, boolean pass, String remark) {
        return approve(ticketId, pass, remark, null, true, null);
    }

static Map<String, Object> approve(long ticketId, boolean pass, String remark, String operator) {
        return approve(ticketId, pass, remark, operator, true, null);
    }

static Map<String, Object> approve(
            long ticketId, boolean pass, String remark, String operator, boolean superAdmin) {
        return approve(ticketId, pass, remark, operator, superAdmin, null);
    }

static Map<String, Object> approve(
            long ticketId,
            boolean pass,
            String remark,
            String operator,
            boolean superAdmin,
            String assigneeUsername) {
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        String st = String.valueOf(m.get("status"));
        boolean first = "pending".equals(st);
        boolean verifying = "verifying".equals(st);
        boolean midStage = "pending_mid".equals(st);
        boolean finalStage = "pending_final".equals(st);
        boolean holdReady = "hold_ready".equals(st);
        if (TicketStore.requireClaimProof && first && pass) {
            throw new IllegalStateException("请先提交并核验认领凭证");
        }
        if (TicketStore.requireClaimProof && verifying && pass) {
            ClaimProofStore.assertPassed(ticketId);
            first = true;
        }
        if (!first && !midStage && !finalStage && !holdReady && !(verifying && TicketStore.requireClaimProof)) {
            throw new IllegalStateException("仅待审核或待取书单据可审批");
        }
        if (TicketStore.twoLevelApprove && finalStage && pass && !superAdmin) {
            throw new IllegalStateException("终审通过需总管操作");
        }
        if (pass && TicketStore.requirePeerConfirm && TicketStore.hasColumn("peer_ack")) {
            Object rawAck = m.get("peerAck");
            boolean acked = Boolean.TRUE.equals(rawAck)
                    || "1".equals(String.valueOf(rawAck))
                    || "true".equalsIgnoreCase(String.valueOf(rawAck));
            if (!acked) {
                throw new IllegalStateException("对方尚未确认，暂不可审核通过");
            }
        }
        String op = operator == null ? "" : operator.trim();
        String dispatchTo = assigneeUsername == null ? "" : assigneeUsername.trim();
        boolean bind = !op.isBlank() && TicketStore.hasColumn("assignee_username");
        String note = remark == null ? "" : remark.trim();
        if (!pass && note.isBlank()) {
            throw new IllegalStateException("请填写驳回原因");
        }
        if (pass && note.isBlank()) {
            Object prev = m.get("remark");
            note = prev == null ? "" : String.valueOf(prev);
        }

        // 到书待取：通过=确认借出（库存已在晋升时预扣）；驳回=回补并顺延
        if (holdReady) {
            long itemId = TicketSql.toLong(m.get("bookId"));
            int nQty = TicketDeriveOps.rowQty(m);
            if (!pass) {
                if (TicketStore.MODE == TicketStore.Mode.ARCHIVE && TicketStore.useQuota && itemId > 0
                        && ArchiveStore.getItemRaw(itemId) != null) {
                    ArchiveStore.adjustStock(itemId, nQty);
                }
                Map<String, Object> rej = new LinkedHashMap<>();
                rej.put("ticketTable", TicketStore.TICKET);
                rej.put("id", ticketId);
                rej.put("status", "rejected");
                rej.put("remark", note);
                rej.put("clearHoldExpire", TicketStore.hasColumn("hold_expire_at"));
                mapper().updateCancelOrRejectHold(rej);
                TicketDeriveOps.appendProgress(ticketId, "rejected", op,
                        note.isBlank() ? "驳回待取书预约" : note);
                TicketNotifyOps.notifyTicketResult(m, false, note);
                if (itemId > 0) TicketQueueOps.tryPromoteBookHold(itemId);
                return TicketDeriveOps.get(ticketId);
            }
            return TicketQueueOps.finalizeHoldReadyApprove(ticketId, m, note, op, dispatchTo, bind);
        }


        if (!pass) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("ticketTable", TicketStore.TICKET);
            row.put("id", ticketId);
            row.put("remark", note);
            row.put("bindAssignee", bind);
            if (bind) row.put("assigneeUsername", op);
            mapper().updateReject(row);
            TicketNotifyOps.notifyTicketResult(m, false, note);
            TicketDeriveOps.appendProgress(ticketId, "rejected", op,
                    note == null || note.isBlank() ? TicketCopy.stateLabel("rejected", TicketCopy.verbLabel("reject", "已驳回")) : note);
            return TicketDeriveOps.get(ticketId);
        }

        // 三级：初审通过 → 待复审
        if (TicketStore.threeLevelApprove && first) {
            advanceApproveStage(ticketId, "pending_mid", note, op, bind, m,
                    "初审已通过", "「" + TicketNotifyOps.subjectOf(m) + "」已通过初审，等待复审。",
                    "待复审", "初审通过");
            return TicketDeriveOps.get(ticketId);
        }
        // 三级：复审通过 → 待终审
        if (TicketStore.threeLevelApprove && midStage) {
            advanceApproveStage(ticketId, "pending_final", note, op, bind, m,
                    "复审已通过", "「" + TicketNotifyOps.subjectOf(m) + "」已通过复审，等待终审。",
                    "待终审", "复审通过");
            return TicketDeriveOps.get(ticketId);
        }
        // 二级：初审通过 → 待终审（不扣库存）
        if (TicketStore.twoLevelApprove && !TicketStore.threeLevelApprove && first) {
            advanceApproveStage(ticketId, "pending_final", note, op, bind, m,
                    "初审已通过", "「" + TicketNotifyOps.subjectOf(m) + "」已通过初审，等待终审。",
                    "待终审", "初审通过");
            return TicketDeriveOps.get(ticketId);
        }

        // 终审通过或单级通过 → approved（扣库存 / 时间银行扣时长）
        if (TicketStore.useDeadline && !TicketStore.hasColumn("due_at")) {
            throw new IllegalStateException("系统未配置应还日字段，无法审批通过");
        }
        if (TicketStore.timebankRedeem) {
            TimebankStore.debitForTicketApprove(m);
        }
        long approvedItemId = 0L;
        if (TicketStore.MODE == TicketStore.Mode.ARCHIVE && TicketStore.useQuota) {
            long itemId = TicketSql.toLong(m.get("bookId"));
            Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
            if (item == null) throw new IllegalStateException("对象不存在");
            int stock = item.get("stock") instanceof Number n ? n.intValue() : 0;
            int nQty = TicketDeriveOps.rowQty(m);
            if (stock < nQty) throw new IllegalStateException(ArchiveStore.stockShortageNeed(nQty));
            ArchiveStore.adjustStock(itemId, -nQty);
            approvedItemId = itemId;
        }
        String handler = !dispatchTo.isBlank() ? dispatchTo : op;
        boolean bindHandler = !handler.isBlank() && TicketStore.hasColumn("assignee_username");
        if (TicketStore.useDeadline) {
            LocalDateTime approveAt = LocalDateTime.now();
            LocalDateTime dueAt = approveAt.plusDays(TicketDeriveOps.levelSlaDays(m, TicketStore.loanDays()));
            if (TicketStore.MODE == TicketStore.Mode.ARCHIVE) {
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
            }
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("ticketTable", TicketStore.TICKET);
            row.put("id", ticketId);
            row.put("remark", note);
            row.put("bindAssignee", bindHandler);
            if (bindHandler) row.put("assigneeUsername", handler);
            row.put("approveAt", Timestamp.valueOf(approveAt));
            row.put("withDue", true);
            row.put("dueAt", Timestamp.valueOf(dueAt));
            row.put("withFineYuan", TicketStore.hasColumn("fine_yuan"));
            row.put("withRemindMsg", TicketStore.hasColumn("remind_msg"));
            mapper().updateApproved(row);
        } else {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("ticketTable", TicketStore.TICKET);
            row.put("id", ticketId);
            row.put("remark", note);
            row.put("bindAssignee", bindHandler);
            if (bindHandler) row.put("assigneeUsername", handler);
            row.put("withDue", false);
            row.put("withFineYuan", false);
            row.put("withRemindMsg", false);
            mapper().updateApproved(row);
        }
        String passCode = issuePassCodeIfNeeded(ticketId);
        TicketNotifyOps.notifyTicketResult(m, true, note, passCode);
        TicketNotifyOps.notifyArrivalIfNeeded(m);
        TicketDeriveOps.appendProgress(ticketId, "approved", op, note.isBlank()
                ? TicketCopy.stateLabel("approved", TicketCopy.verbLabel("approve", "审核通过")) : note);
        // 库存扣尽：同对象其它待审自动驳回（失物一件一主；图书最后一本等同）
        int autoRejected = 0;
        if (approvedItemId > 0) {
            autoRejected = rejectSiblingsWhenStockGone(approvedItemId, ticketId);
        }
        Map<String, Object> out = TicketDeriveOps.get(ticketId);
        if (out != null) {
            out.put("autoRejectedCount", autoRejected);
        }
        return out;
    }

static void advanceApproveStage(
            long ticketId,
            String nextStatus,
            String note,
            String op,
            boolean bind,
            Map<String, Object> m,
            String userTitle,
            String userBody,
            String adminTitle,
            String progressDefault) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("ticketTable", TicketStore.TICKET);
        row.put("id", ticketId);
        row.put("status", nextStatus);
        row.put("remark", note);
        row.put("bindAssignee", bind);
        if (bind) row.put("assigneeUsername", op);
        mapper().updateApproveStage(row);
        try {
            String user = TicketSql.str(m.get("username"));
            if (!user.isBlank()) {
                MessageStore.send(user, userTitle, userBody, "ticket", TicketSql.toLong(m.get("id")));
            }
            MessageStore.notifyAdmins(
                    adminTitle, userBody, "ticket", TicketSql.toLong(m.get("id")), op);
        } catch (Exception ignored) {
        }
        TicketDeriveOps.appendProgress(ticketId, nextStatus, op, note.isBlank()
                ? TicketCopy.stateLabel(nextStatus, progressDefault) : note);
    }

static String issuePassCodeIfNeeded(long ticketId) {
        if (!TicketStore.issuePassCode || ticketId <= 0) return "";
        if (!TicketStore.hasColumn("pass_code")) {
            throw new IllegalStateException("系统未配置通行码字段，无法签发");
        }
        Map<String, Object> cur = TicketDeriveOps.get(ticketId);
        if (cur != null) {
            String prev = TicketSql.str(cur.get("passCode"));
            if (!prev.isBlank()) return prev;
        }
        String code = "VIS" + String.format("%08d", Math.floorMod(System.nanoTime(), 100_000_000));
        try {
            int n = mapper().updatePassCode(TicketStore.TICKET, ticketId, code);
            if (n <= 0) {
                throw new IllegalStateException("通行码签发失败，请重试");
            }
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("通行码签发失败，请重试", e);
        }
        TicketDeriveOps.appendProgress(ticketId, "pass_code", "system", "通行码 " + code);
        return code;
    }

static int rejectSiblingsWhenStockGone(long itemId, long approvedTicketId) {
        if (TicketStore.MODE != TicketStore.Mode.ARCHIVE || !TicketStore.useQuota || itemId <= 0) return 0;
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) return 0;
        int remain = item.get("stock") instanceof Number n ? n.intValue() : 0;
        if (remain > 0) return 0;
        String reason = TicketCopy.siblingRejectTip();
        List<Long> ids;
        try {
            ids = mapper().selectSiblingPendingIds(TicketStore.TICKET, TicketStore.itemFkColumn(), itemId, approvedTicketId);
        } catch (Exception e) {
            throw new IllegalStateException("库存耗尽后查询同档待审失败", e);
        }
        if (ids == null || ids.isEmpty()) return 0;
        int rejected = 0;
        for (Long sid : ids) {
            if (sid == null || sid <= 0) continue;
            try {
                int n = mapper().updateRejectSibling(TicketStore.TICKET, sid, reason);
                if (n <= 0) continue;
                rejected++;
                Map<String, Object> sibling = TicketRowMaps.load(sid);
                if (sibling != null) {
                    TicketNotifyOps.notifyTicketResult(sibling, false, reason);
                }
                TicketDeriveOps.appendProgress(sid, "rejected", "system", reason);
            } catch (Exception e) {
                throw new IllegalStateException("库存耗尽后驳回同档待审失败", e);
            }
        }
        return rejected;
    }

}
