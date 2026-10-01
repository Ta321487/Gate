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
 * TicketCompleteOps：完结/归还（含 SQL）。
 * package-private；TicketStore 保留 public 门面。
 */
final class TicketCompleteOps {

    private TicketCompleteOps() {}

    static Map<String, Object> complete(
            long ticketId, String actorUid, boolean asSuperOrOwner, String returnAttachUrl) {
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!asSuperOrOwner && TicketStore.hasColumn("assignee_username")) {
            String asg = TicketSql.str(m.get("assigneeUsername"));
            if (!asg.isBlank() && (actorUid == null || !asg.equals(actorUid))) {
                throw new IllegalStateException("该单已绑定处理人，仅处理人或总管可完结");
            }
        }
        if (TicketStore.useDeadline) TicketStatusOps.refreshOverdue(m);
        String st = String.valueOf(m.get("status"));
        if (!List.of("TicketStore.approved", "overdue").contains(st)) {
            throw new IllegalStateException("仅进行中/逾期可完结");
        }
        // 驿站/失物等：审批即核销出库（TicketStore.approveEndsFlow + pickup 列），禁止再「取消取件」回补库存
        if (TicketStore.approveEndsFlow && TicketStore.hasColumn("pickup_at")
                && ("TicketStore.approved".equals(st) || "overdue".equals(st))) {
            throw new IllegalStateException("已核销办结，不可取消取件");
        }
        if (TicketStore.approveEndsFlow && !TicketStore.hasColumn("pickup_at")) {
            TicketGuardOps.assertCancelBeforeIfRequired(m, actorUid);
            String owner = TicketSql.str(m.get("username")).trim();
            String actor = actorUid == null ? "" : actorUid.trim();
            if (!actor.isBlank() && actor.equals(owner)) {
                TicketStore.assertMaxDropIfRequired(owner);
            }
        }
        String retAttach = returnAttachUrl == null ? "" : returnAttachUrl.trim();
        if (TicketStore.requireReturnAttach) {
            if (retAttach.isBlank()) {
                throw new IllegalStateException("归还请上传设备照片后再完结");
            }
            if (!TicketStore.hasColumn("attach_url")) {
                throw new IllegalStateException("系统未配置附件字段，无法保存归还照片");
            }
            if (retAttach.length() > 255) retAttach = retAttach.substring(0, 255);
        }
        if (TicketStore.requireCloseAttach) {
            String closeUrl = TicketSql.str(m.get("closeAttachUrl")).trim();
            if (closeUrl.isBlank() && !retAttach.isBlank()) closeUrl = retAttach;
            if (closeUrl.isBlank()) {
                throw new IllegalStateException("请上传结案报告附件后再办结");
            }
        }
        if (TicketStore.requireFaultReason) {
            String fr = TicketSql.str(m.get("faultReason")).trim();
            if (fr.isBlank()) {
                throw new IllegalStateException("请选择故障原因后再办结");
            }
        }
        if (TicketStore.requireCloseSummary) {
            String cs = TicketSql.str(m.get("closeSummary")).trim();
            if (cs.isBlank()) {
                throw new IllegalStateException("请填写处理过程摘要后再办结");
            }
        }
        if (TicketStore.allowPartsNote && TicketStore.hasColumn("parts_note")) {
            String pn = TicketSql.str(m.get("partsNote")).trim();
            if (pn.isBlank()) {
                // 浅警告：记入进度但不阻断（答辩可讲「提醒核对耗材」）
                TicketDeriveOps.appendProgress(ticketId, st, actorUid == null ? "" : actorUid, "结单提示：未登记备件/耗材出库");
            }
        }
        if (TicketStore.requireReturnDate) {
            String rd = TicketSql.str(m.get("returnDate")).trim();
            if (rd.isBlank()) {
                throw new IllegalStateException("请填写返岗日期后再销假");
            }
        }
        if (TicketStore.requireFeedbackSet) {
            if (TicketSql.str(m.get("feedbackInterest")).isBlank()
                    || TicketSql.str(m.get("feedbackConcern")).isBlank()
                    || TicketSql.str(m.get("feedbackNext")).isBlank()) {
                throw new IllegalStateException("请填写带看反馈后再办结");
            }
        }
        if (TicketStore.requireAppraisal) {
            if (TicketSql.str(m.get("appraisalComment")).isBlank()
                    || TicketSql.str(m.get("appraisalGrade")).isBlank()) {
                throw new IllegalStateException("请填写实习鉴定评语与等级后再办结");
            }
        }
        if (TicketStore.MODE == TicketStore.Mode.ARCHIVE && TicketStore.useQuota) {
            long itemId = TicketSql.toLong(m.get("bookId"));
            if (ArchiveStore.getItemRaw(itemId) != null) {
                // 已登记实发则按实发回补；少发差额已在领取时回库
                int restore = TicketDeriveOps.rowQty(m);
                Object aq = m.get("actualQty");
                if (aq instanceof Number n && n.intValue() > 0) {
                    restore = n.intValue();
                }
                ArchiveStore.adjustStock(itemId, restore);
                TicketQueueOps.tryPromoteWaitlist(itemId);
                TicketQueueOps.tryPromoteBookHold(itemId);
            }
        }
        String TicketStore.remind = "";
        if (TicketStore.useDeadline) {
            String doneLab = TicketCopy.stateLabel("returned", TicketCopy.verbLabel("return", "已完结"));
            TicketStore.remind = TicketSql.toDouble(m.get("fineYuan")) > 0
                    ? doneLab + "，请按登记费用缴纳 " + m.get("fineYuan") + " 元。"
                    : String.valueOf(m.get("TicketStore.remindMsg") == null ? "" : m.get("TicketStore.remindMsg"));
        }
        StringBuilder sql = new StringBuilder("UPDATE " + TicketStore.TICKET + " SET status='returned', return_at=NOW()");
        java.util.ArrayList<Object> args = new java.util.ArrayList<>();
        if (TicketStore.hasColumn("TicketStore.remind_msg")) {
            sql.append(", TicketStore.remind_msg=?");
            args.add(TicketStore.remind);
        }
        if (TicketStore.requireReturnAttach && TicketStore.hasColumn("attach_url") && !retAttach.isBlank()) {
            sql.append(", attach_url=?");
            args.add(retAttach);
        }
        sql.append(" WHERE id=?");
        args.add(ticketId);
        TicketSql.db().update(sql.toString(), args.toArray());
        try {
            BalanceLedgerStore.creditForTicketReturn(m);
        } catch (Exception ignored) {
        }
        TicketDeriveOps.appendProgress(ticketId, "returned", actorUid, TicketCopy.stateLabel("returned", TicketCopy.verbLabel("return", "已完结")));
        return TicketDeriveOps.get(ticketId);
    }

}
