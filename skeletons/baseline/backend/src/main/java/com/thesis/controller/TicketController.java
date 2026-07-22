package com.thesis.controller;

import com.thesis.capability.TicketStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/** 通用单据 API：/api/tickets（借阅 / 报修等均走此路径；LIBRARY 另保留 /api/borrows 兼容） */
@RestController
@RequestMapping("/api/tickets")
public class TicketController {

    @Value("${thesis.register-role:user}")
    private String userRole;

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
                return R.ok(TicketStore.applyStandalone(uid, title, location, remark, typeId, roomId, attachUrl));
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
            return R.ok(tid > 0 ? TicketStore.get(tid) : created);
        } catch (NumberFormatException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, "缺少业务对象 id");
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
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
            return R.ok(TicketStore.approve(id, pass, remark, uid, superAdmin));
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
        int rating;
        try {
            rating = Integer.parseInt(String.valueOf(body.get("rating")));
        } catch (Exception e) {
            throw new BizException(ErrorCode.BAD_REQUEST, "请选择 1～5 分");
        }
        String note = body.get("remark") == null ? "" : String.valueOf(body.get("remark")).trim();
        try {
            return R.ok(TicketStore.rate(id, uid, rating, note));
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

    @PostMapping("/{id}/complete")
    public R<Map<String, Object>> complete(@PathVariable long id, HttpSession session) {
        String uid = requireLogin(session);
        Map<String, Object> br = TicketStore.get(id);
        if (br == null) throw new BizException(ErrorCode.NOT_FOUND, "单据不存在");
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
        boolean owner = uid.equals(br.get("username"));
        if (!admin && !owner) {
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
        if (!admin && !uid.equals(br.get("username"))) {
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
