package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.LibraryStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/borrows")
public class BorrowController {

    /** 读者：申请借阅 */
    @PostMapping("/apply")
    public R<Map<String, Object>> apply(@RequestBody Map<String, Object> body, HttpSession session) {
        String uid = requireLogin(session);
        requireReader(session);
        long bookId = Long.parseLong(String.valueOf(body.get("bookId")));
        try {
            return R.ok(LibraryStore.applyBorrow(uid, bookId));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 管理员：审核 */
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
            return R.ok(LibraryStore.approve(id, pass, remark, uid));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 归还（读者本人或管理员） */
    @PostMapping("/{id}/return")
    public R<Map<String, Object>> returnBook(@PathVariable long id, HttpSession session) {
        String uid = requireLogin(session);
        Map<String, Object> br = LibraryStore.getBorrow(id);
        if (br == null) throw new BizException(ErrorCode.NOT_FOUND, "借阅单不存在");
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
        boolean owner = uid.equals(br.get("username"));
        if (!admin && !owner) {
            throw new BizException(ErrorCode.FORBIDDEN, "只能归还自己的借阅");
        }
        try {
            boolean asSuperOrOwner = owner || AdminAuth.isSuperAdmin(session);
            return R.ok(LibraryStore.returnBook(id, uid, asSuperOrOwner));
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 管理员：标记逾期 */
    @PostMapping("/{id}/overdue")
    public R<Map<String, Object>> overdue(@PathVariable long id, HttpSession session) {
        requireAdmin(session);
        try {
            return R.ok(LibraryStore.markOverdue(id));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 管理员：催还提醒（读者端可见 remindMsg） */
    @PostMapping("/{id}/remind")
    public R<Map<String, Object>> remind(@PathVariable long id, HttpSession session) {
        requireAdmin(session);
        try {
            return R.ok(LibraryStore.remind(id));
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
            return R.ok(LibraryStore.pageBorrows(uid, status, page, size));
        }
        boolean superAdmin = AdminAuth.isSuperAdmin(session);
        return R.ok(LibraryStore.pageBorrows(null, status, page, size, uid, superAdmin));
    }

    @GetMapping("/{id}")
    public R<Map<String, Object>> detail(@PathVariable long id, HttpSession session) {
        String uid = requireLogin(session);
        Map<String, Object> br = LibraryStore.getBorrow(id);
        if (br == null) throw new BizException(ErrorCode.NOT_FOUND, "借阅单不存在");
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
        if (!admin && !uid.equals(br.get("username"))) {
            throw new BizException(ErrorCode.FORBIDDEN, "无权查看");
        }
        if (admin && !AdminAuth.isSuperAdmin(session) && !"pending".equals(br.get("status"))) {
            String asg = br.get("assigneeUsername") == null ? "" : String.valueOf(br.get("assigneeUsername"));
            if (!asg.isBlank() && !asg.equals(uid)) {
                throw new BizException(ErrorCode.FORBIDDEN, "该单已由其他处理人受理");
            }
        }
        return R.ok(br);
    }

    private static String requireLogin(HttpSession session) {
        Object uid = session.getAttribute("uid");
        if (uid == null) throw new BizException(ErrorCode.UNAUTHORIZED, "未登录");
        return uid.toString();
    }

    private static void requireAdmin(HttpSession session) {
        if (!"admin".equals(String.valueOf(session.getAttribute("role")))) {
            throw new BizException(ErrorCode.FORBIDDEN, "需要管理员权限");
        }
    }

    private static void requireReader(HttpSession session) {
        String role = String.valueOf(session.getAttribute("role"));
        if (!"reader".equals(role) && !"user".equals(role)) {
            // 子管理也可代测；超管一般不借书，允许 reader/user
            if ("admin".equals(role)) {
                throw new BizException(ErrorCode.BAD_REQUEST, "请使用读者账号申请借阅");
            }
        }
    }
}
