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
                return R.ok(TicketStore.applyStandalone(uid, title, location, remark, typeId, roomId));
            }
            long itemId = Long.parseLong(String.valueOf(body.get("itemId") != null ? body.get("itemId") : body.get("bookId")));
            return R.ok(TicketStore.apply(uid, itemId));
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
            // 受理/驳回即绑定处理人（子管认领工单）
            return R.ok(TicketStore.approve(id, pass, remark, uid));
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
            HttpSession session) {
        String uid = requireLogin(session);
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
        if (!admin) {
            return R.ok(TicketStore.page(uid, status, page, size));
        }
        boolean superAdmin = AdminAuth.isSuperAdmin(session);
        return R.ok(TicketStore.page(null, status, page, size, uid, superAdmin));
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
        if (admin && !AdminAuth.isSuperAdmin(session) && !"pending".equals(br.get("status"))) {
            String asg = str(br.get("assigneeUsername"));
            if (!asg.isBlank() && !asg.equals(uid)) {
                throw new BizException(ErrorCode.FORBIDDEN, "该单已由其他处理人受理");
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
