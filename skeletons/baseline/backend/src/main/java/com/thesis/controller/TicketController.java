package com.thesis.controller;

import com.thesis.capability.AuditLogStore;
import com.thesis.capability.StaffRosterStore;
import com.thesis.capability.TicketStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.GradeScoreStore;
import com.thesis.service.MaterialCheckStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 通用单据 API：/api/tickets（借阅 / 报修等均走此路径；LIBRARY 另保留 /api/borrows 兼容） */
@RestController
@RequestMapping("/api/tickets")
public class TicketController {

    @Value("${thesis.register-role:user}")
    private String userRole;

    /** 受理派单：可选处理人（子管/维修员等）；挂 staff_roster 时标注当日当班 */
    @GetMapping("/dispatch-targets")
    public R<List<Map<String, Object>>> dispatchTargets(HttpSession session) {
        AdminAuth.requireAdmin(session);
        List<Map<String, Object>> raw = com.thesis.service.UserStore.listManaged(userRole, "subadmins", null);
        java.util.Set<String> onDuty = StaffRosterStore.enabled()
                ? StaffRosterStore.onDutyUsernames(java.time.LocalDate.now().toString())
                : java.util.Set.of();
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> row : raw) {
            if (row == null) continue;
            if (Boolean.FALSE.equals(row.get("enabled"))) continue;
            Map<String, Object> one = new LinkedHashMap<>();
            one.put("username", row.get("username"));
            one.put("nickname", row.get("nickname"));
            one.put("staffPost", row.get("staffPost"));
            one.put("staffKind", row.get("staffKind"));
            String un = row.get("username") == null ? "" : String.valueOf(row.get("username"));
            one.put("onDutyToday", onDuty.contains(un));
            out.add(one);
        }
        return R.ok(out);
    }

    @PostMapping("/apply")
    public R<Map<String, Object>> apply(@RequestBody Map<String, Object> body, HttpSession session) {
        String uid = requireLogin(session);
        requireUser(session);
        try {
            if (TicketStore.mode() == TicketStore.Mode.STANDALONE) {
                String title = str(body.get("title"));
                String location = str(body.get("location"));
                String remark = str(body.get("remark"));
                if (remark.isBlank()) remark = str(body.get("content"));
                Long typeId = toLongOrNull(body.get("typeId"));
                Long roomId = toLongOrNull(body.get("roomId"));
                String attachUrl = str(body.get("attachUrl"));
                String priority = str(body.get("priority"));
                String contactPhone = str(body.get("contactPhone"));
                if (contactPhone.isBlank()) contactPhone = str(body.get("phone"));
                Map<String, Object> created = TicketStore.applyStandalone(
                        uid, title, location, remark, typeId, roomId, attachUrl, priority, contactPhone);
                long tid = created.get("id") instanceof Number n ? n.longValue() : 0L;
                if (tid > 0) {
                    TicketStore.patchTicketExtras(tid, body);
                    if (Boolean.TRUE.equals(body.get("asDraft"))
                            || "true".equalsIgnoreCase(str(body.get("asDraft")))
                            || "draft".equalsIgnoreCase(str(body.get("status")))) {
                        created = TicketStore.saveDraft(tid, uid);
                    } else {
                        created = TicketStore.get(tid);
                    }
                    String dup = TicketStore.checkDupRepairHint(tid);
                    if (dup != null && !dup.isBlank()) created.put("dupRepairHint", dup);
                }
                return R.ok(created);
            }
            long itemId = Long.parseLong(String.valueOf(body.get("itemId") != null ? body.get("itemId") : body.get("bookId")));
            // 开题扫 GRADE：成绩异议/更正申请入口按时限关（未开时为 no-op）
            GradeScoreStore.assertObjectionOpen(uid, itemId);
            String remark = str(body.get("remark"));
            if (remark.isBlank()) remark = str(body.get("content"));
            String attachUrl = str(body.get("attachUrl"));
            Integer qty = toIntOrNull(body.get("qty"));
            String dueAt = str(body.get("dueAt"));
            if (dueAt.isBlank()) dueAt = str(body.get("borrowUntil"));
            String periodStart = str(body.get("periodStart"));
            if (periodStart.isBlank()) periodStart = str(body.get("startAt"));
            String periodEnd = str(body.get("periodEnd"));
            if (periodEnd.isBlank()) periodEnd = str(body.get("endAt"));
            String claimCode = str(body.get("pickupCode"));
            if (claimCode.isBlank()) claimCode = str(body.get("claimCode"));
            TicketStore.assertClaimCodeIfRequired(itemId, claimCode.isBlank() ? remark : claimCode);
            TicketStore.assertMatchProfileRoomIfRequired(uid, itemId);
            TicketStore.assertBedConstraintIfRequired(uid, itemId);
            TicketStore.assertCalibDueIfRequired(itemId);
            TicketStore.assertAckFlagsIfRequired(body);
            MaterialCheckStore.assertSubmitted(body.get("materials"));
            Map<String, Object> created = TicketStore.apply(
                    uid,
                    itemId,
                    remark,
                    attachUrl,
                    qty,
                    dueAt.isBlank() ? null : dueAt,
                    periodStart.isBlank() ? null : periodStart,
                    periodEnd.isBlank() ? null : periodEnd);
            long tid = created.get("id") instanceof Number n ? n.longValue() : 0L;
            MaterialCheckStore.saveTicketMaterials(tid, body.get("materials"));
            TicketStore.patchTicketExtras(tid, body);
            try {
                created = finishApplyExtras(tid, uid, body, created);
            } catch (IllegalArgumentException | IllegalStateException e) {
                if (tid > 0) TicketStore.deleteFreshTicket(tid);
                throw e;
            }
            return R.ok(tid > 0 ? TicketStore.get(tid) : created);
        } catch (NumberFormatException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, "缺少业务对象 id");
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /**
     * 提交即评分（评教）/ 提交即口令签到（查寝）：须 autoApprove，失败由调用方回滚单据。
     */
    private Map<String, Object> finishApplyExtras(
            long tid, String uid, Map<String, Object> body, Map<String, Object> created) {
        if (tid <= 0 || !TicketStore.isAutoApprove()) return created;
        String checkinCode = str(body.get("checkinCode"));
        if (checkinCode.isBlank()) checkinCode = str(body.get("code"));
        if (TicketStore.isAllowCheckin() && !checkinCode.isBlank()) {
            created = TicketStore.checkin(tid, uid, checkinCode);
        } else if (TicketStore.isAllowCheckin()) {
            throw new IllegalStateException("请输入签到码");
        }
        if (!TicketStore.isAllowRating()) return created;
        boolean wantRate = body.get("dims") != null || body.get("rating") != null;
        if (!wantRate && TicketStore.ratingDimsRequiredOnApply()) {
            throw new IllegalStateException("请完成各维度评分");
        }
        if (!wantRate) return created;
        int rating = 0;
        Object ratingRaw = body.get("rating");
        if (ratingRaw != null && !String.valueOf(ratingRaw).isBlank()
                && !"null".equalsIgnoreCase(String.valueOf(ratingRaw))) {
            try {
                rating = Integer.parseInt(String.valueOf(ratingRaw));
            } catch (Exception e) {
                throw new IllegalStateException("请选择 1～5 分");
            }
        }
        String rateNote = body.get("ratingRemark") == null ? "" : String.valueOf(body.get("ratingRemark")).trim();
        boolean anonymous = Boolean.TRUE.equals(body.get("anonymous"))
                || "true".equalsIgnoreCase(String.valueOf(body.get("anonymous")));
        Map<String, Integer> dims = null;
        Object dimsRaw = body.get("dims");
        if (dimsRaw instanceof Map<?, ?> map) {
            dims = new java.util.LinkedHashMap<>();
            for (Map.Entry<?, ?> e : map.entrySet()) {
                if (e.getKey() == null || e.getValue() == null) continue;
                try {
                    dims.put(String.valueOf(e.getKey()), Integer.parseInt(String.valueOf(e.getValue())));
                } catch (Exception ignored) {
                    throw new IllegalStateException("维度评分须为 1～5 分");
                }
            }
        }
        return TicketStore.rate(tid, uid, rating, rateNote, dims, anonymous);
    }

    @PostMapping("/{id}/approve")
    public R<Map<String, Object>> approve(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        AdminAuth.requireAdmin(session);
        boolean pass = body.get("pass") == null || Boolean.parseBoolean(String.valueOf(body.get("pass")));
        String remark = body.get("remark") == null ? "" : String.valueOf(body.get("remark")).trim();
        if (!pass && remark.isBlank()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "请填写驳回原因");
        }
        try {
            boolean superAdmin = AdminAuth.isSuperAdmin(session);
            String assignee = body.get("assigneeUsername") == null
                    ? ""
                    : String.valueOf(body.get("assigneeUsername")).trim();
            if ("null".equalsIgnoreCase(assignee)) assignee = "";
            Map<String, Object> approved = TicketStore.approve(id, pass, remark, uid, superAdmin, assignee);
            if (pass) {
                TicketStore.patchTicketExtras(id, body);
                approved = TicketStore.get(id);
            }
            AuditLogStore.record(
                    uid,
                    pass ? "ticket_approve" : "ticket_reject",
                    "ticket",
                    String.valueOf(id),
                    pass ? "审核通过" : ("驳回：" + remark));
            return R.ok(approved);
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /**
     * 招聘等：批量录用 / 淘汰（多选通过或驳回；开题挂 allowBatchHire 才可用）。
     * body: { ids:[long], pass:true|false, remark?:string }
     */
    @PostMapping("/batch-hire")
    public R<Map<String, Object>> batchHire(
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        AdminAuth.requireAdmin(session);
        if (!TicketStore.isAllowBatchHire()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "未开通批量录用");
        }
        boolean pass = body.get("pass") == null || Boolean.parseBoolean(String.valueOf(body.get("pass")));
        String remark = body.get("remark") == null ? "" : String.valueOf(body.get("remark")).trim();
        if (!pass && remark.isBlank()) {
            remark = "批量淘汰";
        }
        java.util.List<Long> ids = new java.util.ArrayList<>();
        Object raw = body.get("ids");
        if (raw instanceof java.util.Collection<?> col) {
            for (Object o : col) {
                if (o == null) continue;
                try {
                    ids.add(Long.parseLong(String.valueOf(o)));
                } catch (Exception ignored) {
                }
            }
        }
        try {
            boolean superAdmin = AdminAuth.isSuperAdmin(session);
            Map<String, Object> out = TicketStore.batchHire(ids, pass, remark, uid, superAdmin);
            AuditLogStore.record(
                    uid,
                    pass ? "ticket_batch_hire" : "ticket_batch_reject",
                    "ticket",
                    String.valueOf(out.get("okCount")),
                    pass ? "批量录用" : ("批量淘汰：" + remark));
            return R.ok(out);
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{id}/rate")
    public R<Map<String, Object>> rate(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        String uid = requireLogin(session);
        int rating = 0;
        Object ratingRaw = body.get("rating");
        if (ratingRaw != null && !String.valueOf(ratingRaw).isBlank()
                && !"null".equalsIgnoreCase(String.valueOf(ratingRaw))) {
            try {
                rating = Integer.parseInt(String.valueOf(ratingRaw));
            } catch (Exception e) {
                throw new BizException(ErrorCode.BAD_REQUEST, "请选择 1～5 分");
            }
        }
        String note = body.get("remark") == null ? "" : String.valueOf(body.get("remark")).trim();
        boolean anonymous = Boolean.TRUE.equals(body.get("anonymous"))
                || "true".equalsIgnoreCase(String.valueOf(body.get("anonymous")));
        Map<String, Integer> dims = null;
        Object dimsRaw = body.get("dims");
        if (dimsRaw instanceof Map<?, ?> map) {
            dims = new java.util.LinkedHashMap<>();
            for (Map.Entry<?, ?> e : map.entrySet()) {
                if (e.getKey() == null || e.getValue() == null) continue;
                try {
                    dims.put(String.valueOf(e.getKey()), Integer.parseInt(String.valueOf(e.getValue())));
                } catch (Exception ignored) {
                    throw new BizException(ErrorCode.BAD_REQUEST, "维度评分须为 1～5 分");
                }
            }
        }
        try {
            Map<String, Object> out = TicketStore.rate(id, uid, rating, note, dims, anonymous);
            if (body.containsKey("ratingTags") || body.containsKey("tags")) {
                Map<String, Object> extras = new LinkedHashMap<>();
                Object tags = body.get("ratingTags");
                if (tags == null) tags = body.get("tags");
                extras.put("ratingTags", tags == null ? "" : String.valueOf(tags));
                TicketStore.patchTicketExtras(id, extras);
                out = TicketStore.get(id);
            }
            return R.ok(out);
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/{id}/progress")
    public R<?> progress(@PathVariable long id, HttpSession session) {
        requireLogin(session);
        return R.ok(TicketStore.listProgress(id));
    }

    @PostMapping("/{id}/pickup")
    public R<?> pickup(@PathVariable long id, @RequestBody(required = false) Map<String, Object> body, HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        AdminAuth.requireAdmin(session);
        Map<String, Object> b = body == null ? Map.of() : body;
        Integer qty = toIntOrNull(b.get("actualQty"));
        try {
            return R.ok(TicketStore.markPickup(id, str(b.get("pickupPlace")), qty, uid));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{id}/fine-paid")
    public R<?> finePaid(@PathVariable long id, HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(TicketStore.markFinePaid(id, uid));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{id}/fine-waive")
    public R<?> fineWaive(
            @PathVariable long id,
            @RequestBody(required = false) Map<String, Object> body,
            HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        AdminAuth.requireAdmin(session);
        Map<String, Object> b = body == null ? Map.of() : body;
        String reason = str(b.get("reason"));
        if (reason.isBlank()) reason = str(b.get("remark"));
        try {
            return R.ok(TicketStore.markFineWaived(id, uid, reason));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{id}/confirm-procure-transfer")
    public R<?> confirmProcureTransfer(@PathVariable long id, HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(TicketStore.confirmProcureTransfer(id, uid));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{id}/to-stock-in")
    public R<?> toStockIn(@PathVariable long id, HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        AdminAuth.requireAdmin(session);
        try {
            Map<String, Object> out = TicketStore.transferApprovedToStockIn(id, uid);
            AuditLogStore.record(uid, "ticket_to_stock_in", "ticket", String.valueOf(id), "申购一键入库");
            return R.ok(out);
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{id}/peer-confirm")
    public R<?> peerConfirmTicket(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        String uid = requireLogin(session);
        Map<String, Object> b = body == null ? Map.of() : body;
        boolean pass = !Boolean.FALSE.equals(b.get("pass"))
                && !"false".equalsIgnoreCase(String.valueOf(b.get("pass")));
        String remark = str(b.get("remark"));
        try {
            return R.ok(TicketStore.peerConfirm(id, uid, pass, remark));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/peer-confirm-inbox")
    public R<?> peerConfirmInbox(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            HttpSession session) {
        String uid = requireLogin(session);
        return R.ok(TicketStore.pagePeerConfirmInbox(uid, page, size));
    }

    @PostMapping("/{id}/checkin")
    public R<Map<String, Object>> checkin(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        String uid = requireLogin(session);
        String code = body.get("code") == null ? "" : String.valueOf(body.get("code")).trim();
        try {
            return R.ok(TicketStore.checkin(id, uid, code));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** C-05：档案确认人收件箱（待确认志愿） */
    @GetMapping("/peer-inbox")
    public R<Map<String, Object>> peerInbox(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String status,
            HttpSession session) {
        String uid = requireLogin(session);
        return R.ok(TicketStore.pagePeerInbox(uid, status, page, size));
    }

    /** C-05：档案确认人接受/婉拒志愿 */
    @PostMapping("/{id}/peer-respond")
    public R<Map<String, Object>> peerRespond(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        String uid = requireLogin(session);
        boolean pass = body.get("pass") == null || Boolean.parseBoolean(String.valueOf(body.get("pass")));
        String remark = body.get("remark") == null ? "" : String.valueOf(body.get("remark")).trim();
        if (!pass && remark.isBlank()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "请填写婉拒原因");
        }
        try {
            return R.ok(TicketStore.peerRespond(id, uid, pass, remark));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 申请人撤销待审申请 */
    @PostMapping("/{id}/withdraw")
    public R<Map<String, Object>> withdraw(@PathVariable long id, HttpSession session) {
        String uid = requireLogin(session);
        try {
            return R.ok(TicketStore.withdraw(id, uid));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{id}/complete")
    public R<Map<String, Object>> complete(
            @PathVariable long id,
            @RequestBody(required = false) Map<String, Object> body,
            HttpSession session) {
        String uid = requireLogin(session);
        Map<String, Object> br = TicketStore.get(id);
        if (br == null) throw new BizException(ErrorCode.NOT_FOUND, "单据不存在");
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
        boolean owner = uid.equals(br.get("username"));
        if (TicketStore.isApplicantCompleteOnly()) {
            if (!owner) {
                throw new BizException(ErrorCode.FORBIDDEN, "请由申请人确认完结");
            }
        } else if (!admin && !owner) {
            throw new BizException(ErrorCode.FORBIDDEN, "只能完结自己的单据");
        }
        try {
            boolean asSuperOrOwner = owner || AdminAuth.isSuperAdmin(session);
            if (body != null && !body.isEmpty()) {
                TicketStore.patchTicketExtras(id, body);
            }
            String attach = body == null ? null : str(body.get("attachUrl"));
            if (attach == null || attach.isBlank()) {
                attach = body == null ? null : str(body.get("closeAttachUrl"));
            }
            return R.ok(TicketStore.complete(id, uid, asSuperOrOwner, attach));
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 兼容借阅「归还」语义 */
    @PostMapping("/{id}/return")
    public R<Map<String, Object>> returnTicket(
            @PathVariable long id,
            @RequestBody(required = false) Map<String, Object> body,
            HttpSession session) {
        return complete(id, body, session);
    }

    /** 读者：申报丢失 */
    @PostMapping("/{id}/report-lost")
    public R<Map<String, Object>> reportLost(@PathVariable long id, HttpSession session) {
        String uid = requireLogin(session);
        try {
            return R.ok(TicketStore.reportLost(id, uid));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 管理员：登记赔偿完成 */
    @PostMapping("/{id}/compensate")
    public R<Map<String, Object>> compensate(@PathVariable long id, HttpSession session) {
        AdminAuth.requireAdmin(session);
        String op = requireLogin(session);
        try {
            return R.ok(TicketStore.markCompensated(id, op));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 管理员：标记逾期 */
    @PostMapping("/{id}/overdue")
    public R<Map<String, Object>> overdue(@PathVariable long id, HttpSession session) {
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(TicketStore.markOverdue(id));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 管理员：催还提醒 */
    @PostMapping("/{id}/remind")
    public R<Map<String, Object>> remind(@PathVariable long id, HttpSession session) {
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(TicketStore.remind(id));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 用户催办（站内提醒，≠短信） */
    @PostMapping("/{id}/urge")
    public R<Map<String, Object>> urge(@PathVariable long id, HttpSession session) {
        String uid = requireLogin(session);
        try {
            return R.ok(TicketStore.userUrge(id, uid));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{id}/cancel-urge")
    public R<Map<String, Object>> cancelUrge(@PathVariable long id, HttpSession session) {
        String uid = requireLogin(session);
        try {
            return R.ok(TicketStore.cancelUrge(id, uid));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{id}/hold")
    public R<Map<String, Object>> hold(
            @PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireAdmin(session);
        String uid = requireLogin(session);
        String reason = body == null ? "" : str(body.get("reason"));
        if (reason.isBlank() && body != null) reason = str(body.get("holdReason"));
        try {
            return R.ok(TicketStore.holdTicket(id, uid, reason));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{id}/resume")
    public R<Map<String, Object>> resume(@PathVariable long id, HttpSession session) {
        AdminAuth.requireAdmin(session);
        String uid = requireLogin(session);
        try {
            return R.ok(TicketStore.resumeTicket(id, uid));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{id}/reassign")
    public R<Map<String, Object>> reassign(
            @PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireAdmin(session);
        String uid = requireLogin(session);
        String to = body == null ? "" : str(body.get("assigneeUsername"));
        if (to.isBlank() && body != null) to = str(body.get("to"));
        String remark = body == null ? "" : str(body.get("remark"));
        try {
            Map<String, Object> out = TicketStore.reassign(id, to, uid, remark);
            if (body != null) {
                TicketStore.patchTicketExtras(id, body);
                out = TicketStore.get(id);
            }
            return R.ok(out);
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 退回修改：次数记库并按上限拦截（maxReviseTimes=0 表示不限次）。 */
    @PostMapping("/{id}/return-revise")
    public R<Map<String, Object>> returnRevise(
            @PathVariable long id, @RequestBody(required = false) Map<String, Object> body, HttpSession session) {
        AdminAuth.requireAdmin(session);
        String uid = requireLogin(session);
        String note = body == null ? "" : str(body.get("note"));
        if (note.isBlank() && body != null) note = str(body.get("remark"));
        try {
            return R.ok(TicketStore.returnForRevise(id, uid, note));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 用户重新提交被退回的单据（受 maxReviseTimes 约束）。 */
    @PostMapping("/{id}/resubmit")
    public R<Map<String, Object>> resubmit(
            @PathVariable long id, @RequestBody(required = false) Map<String, Object> body, HttpSession session) {
        String uid = requireLogin(session);
        requireUser(session);
        String note = body == null ? "" : str(body.get("remark"));
        try {
            return R.ok(TicketStore.resubmit(id, uid, note));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{id}/reject-assignment")
    public R<Map<String, Object>> rejectAssignment(
            @PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireAdmin(session);
        String uid = requireLogin(session);
        String reason = body == null ? "" : str(body.get("reason"));
        if (reason.isBlank() && body != null) reason = str(body.get("remark"));
        try {
            return R.ok(TicketStore.rejectAssignment(id, uid, reason));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{id}/cancel-dispatched")
    public R<Map<String, Object>> cancelDispatched(
            @PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        String uid = requireLogin(session);
        String reason = body == null ? "" : str(body.get("reason"));
        if (reason.isBlank() && body != null) reason = str(body.get("remark"));
        try {
            return R.ok(TicketStore.cancelDispatched(id, uid, reason));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{id}/confirm-quote")
    public R<Map<String, Object>> confirmQuote(
            @PathVariable long id, @RequestBody(required = false) Map<String, Object> body, HttpSession session) {
        String uid = requireLogin(session);
        boolean pay = body != null && (Boolean.TRUE.equals(body.get("payMaterial"))
                || "true".equalsIgnoreCase(str(body.get("payMaterial"))));
        try {
            return R.ok(TicketStore.confirmQuote(id, uid, pay));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 申请人续借（须启用 loan_renew） */
    @PostMapping("/{id}/renew")
    public R<Map<String, Object>> renew(@PathVariable long id, HttpSession session) {
        String uid = requireLogin(session);
        try {
            return R.ok(TicketStore.renew(id, uid));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 申请人确认借阅（须启用 book_hold；hold_ready → approved） */
    @PostMapping("/{id}/claim-hold")
    public R<Map<String, Object>> claimHold(@PathVariable long id, HttpSession session) {
        String uid = requireLogin(session);
        try {
            return R.ok(TicketStore.claimHold(id, uid));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping
    public R<Map<String, Object>> page(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String status,
            @RequestParam(required = false) Boolean rated,
            @RequestParam(required = false) Boolean todayAssigned,
            HttpSession session) {
        String uid = requireLogin(session);
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
        if (!admin) {
            return R.ok(TicketStore.page(uid, status, page, size, uid, false, rated, todayAssigned));
        }
        boolean superAdmin = AdminAuth.isSuperAdmin(session);
        return R.ok(TicketStore.page(null, status, page, size, uid, superAdmin, rated, todayAssigned));
    }

    /** 档案下已通过单据（论坛楼层等）；无需登录 */
    @GetMapping("/thread/{itemId}")
    public R<Map<String, Object>> thread(
            @PathVariable long itemId,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "50") int size) {
        if (!TicketStore.enabled() || !TicketStore.isArchiveMode()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "当前不支持楼层");
        }
        return R.ok(TicketStore.listPublicByItem(itemId, page, size));
    }

    @GetMapping("/{id}")
    public R<Map<String, Object>> detail(@PathVariable long id, HttpSession session) {
        String uid = requireLogin(session);
        Map<String, Object> br = TicketStore.get(id);
        if (br == null) throw new BizException(ErrorCode.NOT_FOUND, "单据不存在");
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
        if (!admin && !uid.equals(br.get("username")) && !TicketStore.isPeerOwnerOf(id, uid)) {
            throw new BizException(ErrorCode.FORBIDDEN, "无权查看");
        }
        if (admin && !AdminAuth.isSuperAdmin(session)) {
            String st = str(br.get("status"));
            if (!TicketStore.isHistoryStatus(st) && !TicketStore.isTodoPoolStatus(st)) {
                String asg = str(br.get("assigneeUsername"));
                if (!asg.isBlank() && !asg.equals(uid)) {
                    throw new BizException(ErrorCode.FORBIDDEN, "该单已由其他处理人受理");
                }
            }
        }
        return R.ok(br);
    }

    /** 借用信誉分（分值列）：我的分值 + 我的变动台账；credit-on-overdue 未开时 enabled=false 且 rows 为空。 */
    @GetMapping("/credit/mine")
    public R<Map<String, Object>> creditMine(
            @RequestParam(defaultValue = "20") int size,
            HttpSession session) {
        String uid = requireLogin(session);
        Map<String, Object> out = new LinkedHashMap<>(
                com.thesis.capability.BorrowCreditStore.snapshot(uid));
        out.put("rows", com.thesis.capability.BorrowCreditStore.listLedger(uid, size));
        return R.ok(out);
    }

    /** 管理端信誉分台账：全站最近变动（逾期扣分 / 人工调整）。 */
    @GetMapping("/credit/ledger")
    public R<Map<String, Object>> creditLedger(
            @RequestParam(defaultValue = "50") int size,
            HttpSession session) {
        AdminAuth.requireAdmin(session);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("enabled", com.thesis.capability.BorrowCreditStore.enabled());
        out.put("rows", com.thesis.capability.BorrowCreditStore.listAllRecent(size));
        return R.ok(out);
    }

    /** 管理端人工调整信誉分：正数加分 / 负数扣分，写 credit_ledger 留痕。 */
    @PostMapping("/credit/adjust")
    public R<Map<String, Object>> creditAdjust(
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        AdminAuth.requireAdmin(session);
        String operator = requireLogin(session);
        String username = str(body.get("username"));
        Integer delta = toIntOrNull(body.get("delta"));
        if (username.isBlank()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "请填写要调整的用户名");
        }
        if (delta == null || delta == 0) {
            throw new BizException(ErrorCode.BAD_REQUEST, "调整分值不能为 0");
        }
        try {
            return R.ok(com.thesis.capability.BorrowCreditStore.adjust(
                    username, delta, str(body.get("reason")), operator));
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static Long toLongOrNull(Object o) {
        if (o == null || "".equals(o)) return null;
        if (o instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(String.valueOf(o).trim());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private static Integer toIntOrNull(Object o) {
        if (o == null || "".equals(o)) return null;
        if (o instanceof Number n) return n.intValue();
        try {
            return Integer.parseInt(String.valueOf(o).trim());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private static String requireLogin(HttpSession session) {
        return AdminAuth.requireLogin(session);
    }

    private void requireUser(HttpSession session) {
        String role = String.valueOf(session.getAttribute("role"));
        if ("admin".equals(role)) {
            throw new BizException(ErrorCode.BAD_REQUEST, "请使用业务账号提交单据");
        }
        if (!userRole.equals(role) && !"user".equals(role) && !"reader".equals(role) && !"student".equals(role)) {
            throw new BizException(ErrorCode.FORBIDDEN, "无权提交单据");
        }
    }
}
