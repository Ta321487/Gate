package com.thesis.controller;

import com.thesis.capability.TicketStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
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

    /** 受理派单：可选处理人（子管/维修员等） */
    @GetMapping("/dispatch-targets")
    public R<List<Map<String, Object>>> dispatchTargets(HttpSession session) {
        AdminAuth.requireAdmin(session);
        List<Map<String, Object>> raw = com.thesis.service.UserStore.listManaged(userRole, "subadmins", null);
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> row : raw) {
            if (row == null) continue;
            if (Boolean.FALSE.equals(row.get("enabled"))) continue;
            Map<String, Object> one = new LinkedHashMap<>();
            one.put("username", row.get("username"));
            one.put("nickname", row.get("nickname"));
            one.put("staffPost", row.get("staffPost"));
            one.put("staffKind", row.get("staffKind"));
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
                return R.ok(TicketStore.applyStandalone(
                        uid, title, location, remark, typeId, roomId, attachUrl, priority, contactPhone));
            }
            long itemId = Long.parseLong(String.valueOf(body.get("itemId") != null ? body.get("itemId") : body.get("bookId")));
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
            return R.ok(TicketStore.approve(id, pass, remark, uid, superAdmin, assignee));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
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
            return R.ok(TicketStore.rate(id, uid, rating, note, dims, anonymous));
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
    public R<Map<String, Object>> complete(@PathVariable long id, HttpSession session) {
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
            return R.ok(TicketStore.complete(id, uid, asSuperOrOwner));
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 兼容借阅「归还」语义 */
    @PostMapping("/{id}/return")
    public R<Map<String, Object>> returnTicket(@PathVariable long id, HttpSession session) {
        return complete(id, session);
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

    @GetMapping
    public R<Map<String, Object>> page(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String status,
            @RequestParam(required = false) Boolean rated,
            HttpSession session) {
        String uid = requireLogin(session);
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
        if (!admin) {
            return R.ok(TicketStore.page(uid, status, page, size));
        }
        boolean superAdmin = AdminAuth.isSuperAdmin(session);
        return R.ok(TicketStore.page(null, status, page, size, uid, superAdmin, rated));
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
