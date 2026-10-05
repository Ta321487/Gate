package com.thesis.capability;

import java.util.*;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import com.thesis.service.BalanceLedgerStore;
import com.thesis.service.ClaimProofStore;
import com.thesis.service.MessageStore;
import com.thesis.service.TimebankStore;

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
            first = true; // 核验通过后按初审路径办结
        }
        if (!first && !midStage && !finalStage && !holdReady && !verifying) {
            throw new IllegalStateException("仅待审核或待取书单据可审批");
        }
        if (verifying && !TicketStore.requireClaimProof) {
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
        if (TicketStore.minApproveRemarkWords > 0) {
            // 开启审意见字数时：通过不得回填原申请说明凑字数
            if (pass && note.isBlank()) {
                throw new IllegalStateException("请填写审核意见");
            }
            int words = note.replaceAll("\\s+", "").length();
            if (words < TicketStore.minApproveRemarkWords) {
                throw new IllegalStateException(
                        "审核意见不少于 " + TicketStore.minApproveRemarkWords + " 字后再提交");
            }
        } else if (pass && note.isBlank()) {
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
                TicketSql.db().update(
                        "UPDATE " + TicketStore.TICKET + " SET status='rejected', remark=?"
                                + (TicketStore.hasColumn("hold_expire_at") ? ", hold_expire_at=NULL" : "")
                                + " WHERE id=?",
                        note, ticketId);
                TicketDeriveOps.appendProgress(ticketId, "rejected", op,
                        note.isBlank() ? "驳回待取书预约" : note);
                TicketNotifyOps.notifyTicketResult(m, false, note);
                if (itemId > 0) TicketQueueOps.tryPromoteBookHold(itemId);
                return TicketDeriveOps.get(ticketId);
            }
            return TicketQueueOps.finalizeHoldReadyApprove(ticketId, m, note, op, dispatchTo, bind);
        }

        if (!pass) {
            if (bind) {
                TicketSql.db().update(
                        "UPDATE " + TicketStore.TICKET + " SET status='rejected', approve_at=NOW(), remark=?, assignee_username=? WHERE id=?",
                        note, op, ticketId);
            } else {
                TicketSql.db().update(
                        "UPDATE " + TicketStore.TICKET + " SET status='rejected', approve_at=NOW(), remark=? WHERE id=?",
                        note, ticketId);
            }
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
        // 二级：首关 → 待终审（不扣库存）；文案跟 verbs（报修「受理」等），勿写死「初审」
        if (TicketStore.twoLevelApprove && !TicketStore.threeLevelApprove && first) {
            String approveV = TicketCopy.verbLabel("approve", "通过");
            String waitLab = TicketCopy.stateLabel("pending_final", "待终审");
            advanceApproveStage(ticketId, "pending_final", note, op, bind, m,
                    approveV + "成功",
                    "「" + TicketNotifyOps.subjectOf(m) + "」" + approveV + "成功，等待终审。",
                    waitLab,
                    approveV);
            return TicketDeriveOps.get(ticketId);
        }

        // 终审通过或单级通过 → approved（扣库存 / 时间银行扣时长）
        if (TicketStore.useDeadline && !TicketStore.hasColumn("due_at")) {
            throw new IllegalStateException("系统未配置应还日字段，无法审批通过");
        }
        if (TicketStore.timebankRedeem) {
            TimebankStore.debitForTicketApprove(m);
        }
        BalanceLedgerStore.debitForTicketApprove(m);
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
        if (TicketStore.MODE == TicketStore.Mode.ARCHIVE && TicketStore.useDeadline) {
            LocalDateTime approveAt = LocalDateTime.now();
            LocalDateTime dueAt = approveAt.plusDays(TicketDeriveOps.levelSlaDays(m, TicketStore.loanDays()));
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
            boolean bindHandler = !handler.isBlank() && TicketStore.hasColumn("assignee_username");
            if (bindHandler) {
                StringBuilder sql = new StringBuilder(
                        "UPDATE " + TicketStore.TICKET + " SET status='approved', approve_at=?, remark=?, assignee_username=?");
                List<Object> args = new ArrayList<>();
                args.add(Timestamp.valueOf(approveAt));
                args.add(note);
                args.add(handler);
                sql.append(", due_at=?");
                args.add(Timestamp.valueOf(dueAt));
                if (TicketStore.hasColumn("fine_yuan")) {
                    sql.append(", fine_yuan=0");
                }
                if (TicketStore.hasColumn("remind_msg")) {
                    sql.append(", remind_msg=''");
                }
                sql.append(" WHERE id=?");
                args.add(ticketId);
                TicketSql.db().update(sql.toString(), args.toArray());
            } else {
                StringBuilder sql = new StringBuilder(
                        "UPDATE " + TicketStore.TICKET + " SET status='approved', approve_at=?, remark=?");
                List<Object> args = new ArrayList<>();
                args.add(Timestamp.valueOf(approveAt));
                args.add(note);
                sql.append(", due_at=?");
                args.add(Timestamp.valueOf(dueAt));
                if (TicketStore.hasColumn("fine_yuan")) {
                    sql.append(", fine_yuan=0");
                }
                if (TicketStore.hasColumn("remind_msg")) {
                    sql.append(", remind_msg=''");
                }
                sql.append(" WHERE id=?");
                args.add(ticketId);
                TicketSql.db().update(sql.toString(), args.toArray());
            }
        } else if (TicketStore.useDeadline) {
            // 独立工单 SLA：受理进入处理中时起算处理时限（等级影响时限时按等级取天数）
            LocalDateTime approveAt = LocalDateTime.now();
            LocalDateTime dueAt = approveAt.plusDays(TicketDeriveOps.levelSlaDays(m, TicketStore.loanDays()));
            String handler = !dispatchTo.isBlank() ? dispatchTo : op;
            boolean bindHandler = !handler.isBlank() && TicketStore.hasColumn("assignee_username");
            if (bindHandler) {
                TicketSql.db().update(
                        "UPDATE " + TicketStore.TICKET
                                + " SET status='approved', approve_at=?, remark=?, assignee_username=?, due_at=?"
                                + (TicketStore.hasColumn("fine_yuan") ? ", fine_yuan=0" : "")
                                + (TicketStore.hasColumn("remind_msg") ? ", remind_msg=''" : "")
                                + " WHERE id=?",
                        Timestamp.valueOf(approveAt),
                        note,
                        handler,
                        Timestamp.valueOf(dueAt),
                        ticketId);
            } else {
                TicketSql.db().update(
                        "UPDATE " + TicketStore.TICKET
                                + " SET status='approved', approve_at=?, remark=?, due_at=?"
                                + (TicketStore.hasColumn("fine_yuan") ? ", fine_yuan=0" : "")
                                + (TicketStore.hasColumn("remind_msg") ? ", remind_msg=''" : "")
                                + " WHERE id=?",
                        Timestamp.valueOf(approveAt),
                        note,
                        Timestamp.valueOf(dueAt),
                        ticketId);
            }
            if (TicketStore.slaSplit && TicketStore.hasColumn("response_due_at")) {
                LocalDateTime respDue = approveAt.plusDays(TicketDeriveOps.levelSlaDays(m, 1));
                TicketSql.db().update(
                        "UPDATE " + TicketStore.TICKET + " SET response_due_at=? WHERE id=?",
                        Timestamp.valueOf(respDue),
                        ticketId);
            }
        } else if (bind) {
            String handler = !dispatchTo.isBlank() ? dispatchTo : op;
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET status='approved', approve_at=NOW(), remark=?, assignee_username=? WHERE id=?",
                    note, handler, ticketId);
        } else {
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET status='approved', approve_at=NOW(), remark=? WHERE id=?",
                    note, ticketId);
        }
        String passCode = issuePassCodeIfNeeded(ticketId);
        issueCertIssueNoIfNeeded(ticketId);
        issueVerifyCodeIfNeeded(ticketId);
        issuePickupRedeemIfNeeded(ticketId);
        addTrainHoursIfNeeded(ticketId);
        TicketGuardOps.setMoralObjectionDueIfNeeded(ticketId);
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
        if (bind) {
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET status=?, remark=?, assignee_username=? WHERE id=?",
                    nextStatus, note, op, ticketId);
        } else {
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET status=?, remark=? WHERE id=?",
                    nextStatus, note, ticketId);
        }
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
            int n;
            if (TicketStore.allowPassExpire && TicketStore.passExpireDays > 0
                    && TicketStore.hasColumn("pass_expire_at")) {
                java.sql.Timestamp exp = java.sql.Timestamp.valueOf(
                        java.time.LocalDateTime.now().plusDays(TicketStore.passExpireDays));
                n = TicketSql.db().update(
                        "UPDATE " + TicketStore.TICKET + " SET pass_code=?, pass_expire_at=? WHERE id=?",
                        code, exp, ticketId);
            } else {
                n = TicketSql.db().update(
                        "UPDATE " + TicketStore.TICKET + " SET pass_code=? WHERE id=?", code, ticketId);
            }
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

static String issueCertIssueNoIfNeeded(long ticketId) {
        if (!TicketStore.allowCertIssueNo || ticketId <= 0) return "";
        if (!TicketStore.hasColumn("cert_issue_no")) {
            throw new IllegalStateException("系统未配置开具流水号字段，无法签发");
        }
        Map<String, Object> cur = TicketDeriveOps.get(ticketId);
        if (cur != null) {
            String prev = TicketSql.str(cur.get("certIssueNo"));
            if (!prev.isBlank()) return prev;
        }
        String code = "CERT" + String.format("%08d", Math.floorMod(System.nanoTime(), 100_000_000));
        try {
            int n = TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET cert_issue_no=? WHERE id=?", code, ticketId);
            if (n <= 0) {
                throw new IllegalStateException("开具流水号签发失败，请重试");
            }
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("开具流水号签发失败，请重试", e);
        }
        TicketDeriveOps.appendProgress(ticketId, "cert_issue_no", "system", "开具流水号 " + code);
        return code;
    }

static String issueVerifyCodeIfNeeded(long ticketId) {
        if (!TicketStore.allowCertVerify || ticketId <= 0) return "";
        if (!TicketStore.hasColumn("verify_code")) {
            throw new IllegalStateException("系统未配置真伪查询码字段，无法签发");
        }
        Map<String, Object> cur = TicketDeriveOps.get(ticketId);
        if (cur != null) {
            String prev = TicketSql.str(cur.get("verifyCode"));
            if (!prev.isBlank()) return prev;
        }
        String code = "VF" + String.format("%010d", Math.floorMod(System.nanoTime(), 10_000_000_000L));
        try {
            int n = TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET verify_code=? WHERE id=?", code, ticketId);
            if (n <= 0) {
                throw new IllegalStateException("真伪查询码签发失败，请重试");
            }
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("真伪查询码签发失败，请重试", e);
        }
        TicketDeriveOps.appendProgress(ticketId, "verify_code", "system", "真伪查询码 " + code);
        return code;
    }

static String issuePickupRedeemIfNeeded(long ticketId) {
        if (!TicketStore.allowCertPickupRedeem || ticketId <= 0) return "";
        if (!TicketStore.hasColumn("pickup_redeem_code")) {
            throw new IllegalStateException("系统未配置领取核销码字段，无法签发");
        }
        Map<String, Object> cur = TicketDeriveOps.get(ticketId);
        if (cur != null) {
            String prev = TicketSql.str(cur.get("pickupRedeemCode"));
            if (!prev.isBlank()) return prev;
        }
        String code = "PK" + String.format("%010d", Math.floorMod(System.nanoTime() + 17, 10_000_000_000L));
        try {
            int n = TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET pickup_redeem_code=? WHERE id=?", code, ticketId);
            if (n <= 0) {
                throw new IllegalStateException("领取核销码签发失败，请重试");
            }
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("领取核销码签发失败，请重试", e);
        }
        TicketDeriveOps.appendProgress(ticketId, "pickup_redeem_code", "system", "领取核销码 " + code);
        return code;
    }

static void addTrainHoursIfNeeded(long ticketId) {
        if (!TicketStore.allowTrainHours || ticketId <= 0) return;
        Map<String, Object> cur = TicketDeriveOps.get(ticketId);
        if (cur == null) return;
        double hours = TicketSql.toDouble(cur.get("trainHours"));
        if (!(hours > 0)) return;
        long itemId = TicketSql.toLong(cur.get("itemId"));
        if (itemId <= 0) itemId = TicketSql.toLong(cur.get("bookId"));
        if (itemId <= 0) return;
        ArchiveStore.addTrainHours(itemId, hours);
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
            ids = TicketSql.db().query(
                    "SELECT id FROM " + TicketStore.TICKET
                            + " WHERE " + TicketStore.itemFkColumn() + "=? AND id<>? AND status IN ('pending','pending_mid','pending_final')",
                    (rs, i) -> rs.getLong(1),
                    itemId,
                    approvedTicketId);
        } catch (Exception e) {
            throw new IllegalStateException("库存耗尽后查询同档待审失败", e);
        }
        if (ids == null || ids.isEmpty()) return 0;
        int rejected = 0;
        for (Long sid : ids) {
            if (sid == null || sid <= 0) continue;
            try {
                int n = TicketSql.db().update(
                        "UPDATE " + TicketStore.TICKET
                                + " SET status='rejected', approve_at=NOW(), remark=? WHERE id=? AND status IN ('pending','pending_mid','pending_final')",
                        reason,
                        sid);
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
