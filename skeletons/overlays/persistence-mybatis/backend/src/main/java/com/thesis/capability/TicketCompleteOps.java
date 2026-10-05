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
        if (!List.of("approved", "overdue").contains(st)) {
            throw new IllegalStateException("仅进行中/逾期可完结");
        }
        // 驿站/失物等：审批即核销出库（TicketStore.approveEndsFlow + pickup 列），禁止再「取消取件」回补库存
        if (TicketStore.approveEndsFlow && TicketStore.hasColumn("pickup_at")
                && ("approved".equals(st) || "overdue".equals(st))) {
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
                throw new IllegalStateException(
                        TicketStore.allowSealClosePhoto
                                ? "请上传用印现场照片后再办结"
                                : TicketStore.allowPromoFeedback
                                ? "请上传投放反馈照片后再办结"
                                : "请上传结案报告附件后再办结");
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
        if (TicketStore.allowCertPickup
                && TicketStore.hasColumn("pickup_method")
                && "邮寄".equals(TicketSql.str(m.get("pickupMethod")).trim())) {
            if (!TicketStore.hasColumn("express_no")
                    || TicketSql.str(m.get("expressNo")).trim().isBlank()) {
                throw new IllegalStateException("邮寄件请回填快递单号后再办结");
            }
        }
        if (TicketStore.allowSealCopies) {
            if (TicketStore.hasColumn("seal_copy_nos")
                    && TicketSql.str(m.get("sealCopyNos")).trim().isBlank()) {
                throw new IllegalStateException("请回填用印份号后再办结");
            }
            if (TicketStore.hasColumn("seal_witness_ack")
                    && !TicketNotifyOps.truthy(m.get("sealWitnessAck"))) {
                throw new IllegalStateException("请勾选监印确认后再办结");
            }
        }
        if (TicketStore.allowCompHours) {
            Object ch = m.get("compHours");
            double hours = ch instanceof Number n ? n.doubleValue() : TicketSql.toDouble(ch);
            if (!(hours > 0)) {
                throw new IllegalStateException("请回填大于 0 的核定调休小时后再办结");
            }
        }
        if (TicketStore.allowFleetMileage) {
            Object mk = m.get("mileageKm");
            double km = mk instanceof Number n ? n.doubleValue() : TicketSql.toDouble(mk);
            if (!(km > 0)) {
                throw new IllegalStateException("请回填大于 0 的行驶里程后再办结");
            }
            if (TicketStore.hasColumn("fuel_note")
                    && TicketSql.str(m.get("fuelNote")).trim().isBlank()) {
                throw new IllegalStateException("请填写油耗备注后再办结");
            }
        }
        if (TicketStore.allowReturnFuel) {
            if (!TicketStore.hasColumn("return_fuel")) {
                throw new IllegalStateException("系统未配置回场油量字段");
            }
            Object rf = m.get("returnFuel");
            if (rf == null || String.valueOf(rf).isBlank()) {
                throw new IllegalStateException("请回填 0–100 的回场油量后再办结");
            }
            double fuel = rf instanceof Number n ? n.doubleValue() : TicketSql.toDouble(rf);
            if (fuel < 0 || fuel > 100) {
                throw new IllegalStateException("请回填 0–100 的回场油量后再办结");
            }
        }
        if (TicketStore.allowFleetViolation) {
            if (!TicketStore.hasColumn("violation_person")) {
                throw new IllegalStateException("系统未配置违章责任人字段");
            }
            if (TicketSql.str(m.get("violationPerson")).trim().isBlank()) {
                throw new IllegalStateException("请登记违章责任人后再办结");
            }
        }
        if (TicketStore.allowProcureReturn) {
            if (!TicketStore.hasColumn("return_fail")) {
                throw new IllegalStateException("系统未配置验收结果字段");
            }
            boolean fail = TicketNotifyOps.truthy(m.get("returnFail"));
            if (fail && TicketSql.str(m.get("returnNote")).trim().isBlank()) {
                throw new IllegalStateException("验收不合格时请填写退货说明后再办结");
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
        String remind = "";
        if (TicketStore.useDeadline) {
            String doneLab = TicketCopy.stateLabel("returned", TicketCopy.verbLabel("return", "已完结"));
            remind = TicketSql.toDouble(m.get("fineYuan")) > 0
                    ? doneLab + "，请按登记费用缴纳 " + m.get("fineYuan") + " 元。"
                    : String.valueOf(m.get("remindMsg") == null ? "" : m.get("remindMsg"));
        }
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("ticketTable", TicketStore.TICKET);
        row.put("id", ticketId);
        row.put("withRemindMsg", TicketStore.hasColumn("remind_msg"));
        row.put("remindMsg", remind);
        if (TicketStore.requireReturnAttach && TicketStore.hasColumn("attach_url") && !retAttach.isBlank()) {
            row.put("withAttachUrl", true);
            row.put("attachUrl", retAttach);
        }
        TicketStore.mapper().updateComplete(row);
        try {
            BalanceLedgerStore.creditForTicketReturn(m);
        } catch (Exception ignored) {
        }
        TicketDeriveOps.appendProgress(ticketId, "returned", actorUid, TicketCopy.stateLabel("returned", TicketCopy.verbLabel("return", "已完结")));
        return TicketDeriveOps.get(ticketId);
    }

}
