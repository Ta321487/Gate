package com.thesis.controller;

import com.thesis.capability.ArchiveStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.GuestTeaser;
import com.thesis.common.R;
import com.thesis.service.NoticeStore;
import com.thesis.service.UserStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * 公告：所有人可读；增删改仅总管理员（多店时商家可提交待审）。
 * 过期下架、强制弹窗确认、简易富文本格式。
 */
@RestController
@RequestMapping("/api/notices")
public class NoticeController {

    @GetMapping
    public R<Map<String, Object>> page(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        int p = GuestTeaser.clampPage(session, page);
        int s = GuestTeaser.clampSize(session, size);
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
        boolean approvedOnly = !admin;
        String submitterOnly = null;
        if (admin
                && ArchiveStore.shopMarketplaceEnabled()
                && NoticeStore.hasAuditStatus()
                && !AdminAuth.isSuperAdmin(session)) {
            submitterOnly = AdminAuth.requireLogin(session);
        }
        return R.ok(NoticeStore.page(p, s, approvedOnly, submitterOnly));
    }

    @GetMapping("/force-pending")
    public R<List<Map<String, Object>>> forcePending(HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        return R.ok(NoticeStore.listForcePending(uid));
    }

    @PostMapping("/{id}/ack")
    public R<Void> ack(@PathVariable long id, HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        Map<String, Object> m = NoticeStore.get(id);
        if (m == null) throw new BizException(ErrorCode.NOT_FOUND, "公告不存在");
        NoticeStore.ackForce(id, uid);
        return R.ok(null);
    }

    @GetMapping("/{id}")
    public R<Map<String, Object>> detail(@PathVariable long id, HttpSession session) {
        Map<String, Object> m = NoticeStore.get(id);
        if (m == null) throw new BizException(ErrorCode.NOT_FOUND, "公告不存在");
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
        if (!admin && NoticeStore.hasAuditStatus()) {
            String as = String.valueOf(m.getOrDefault("auditStatus", "")).trim();
            if (!as.isEmpty() && !"approved".equals(as)) {
                throw new BizException(ErrorCode.NOT_FOUND, "公告不存在");
            }
        }
        if (!admin && !NoticeStore.isPortalVisible(m)) {
            throw new BizException(ErrorCode.NOT_FOUND, "公告不存在");
        }
        return R.ok(m);
    }

    @PostMapping
    public R<Map<String, Object>> create(@RequestBody Map<String, Object> body, HttpSession session) {
        if (body == null) body = Map.of();
        String title = str(body, "title");
        if (title.isBlank()) throw new BizException(ErrorCode.BAD_REQUEST, "标题不能为空");
        String content = str(body, "content");
        String expireAt = body.containsKey("expireAt") ? str(body, "expireAt") : null;
        Boolean forceAck = body.containsKey("forceAck") ? boolObj(body.get("forceAck")) : null;
        String contentFmt = body.containsKey("contentFmt") ? str(body, "contentFmt") : null;
        UserStore.Profile pub = publisher(session);
        if (ArchiveStore.shopMarketplaceEnabled() && NoticeStore.hasAuditStatus()) {
            AdminAuth.requireAdmin(session);
            if (!AdminAuth.isSuperAdmin(session)) {
                return R.ok(NoticeStore.add(
                        title, content, pub.username, pub.nickname,
                        "pending", pub.username, expireAt, forceAck, contentFmt));
            }
            return R.ok(NoticeStore.add(
                    title, content, pub.username, pub.nickname,
                    "approved", "", expireAt, forceAck, contentFmt));
        }
        AdminAuth.requireSuperAdmin(session);
        return R.ok(NoticeStore.add(
                title, content, pub.username, pub.nickname,
                null, null, expireAt, forceAck, contentFmt));
    }

    @PostMapping("/{id}/approve")
    public R<Map<String, Object>> approve(@PathVariable long id, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            Map<String, Object> m = NoticeStore.approve(id);
            if (m == null) throw new BizException(ErrorCode.NOT_FOUND, "公告不存在");
            return R.ok(m);
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PutMapping("/{id}")
    public R<Map<String, Object>> update(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        if (body == null) body = Map.of();
        String title = body.get("title") == null ? null : String.valueOf(body.get("title"));
        String content = body.get("content") == null ? null : String.valueOf(body.get("content"));
        Boolean pinned = null;
        if (body.containsKey("pinned")) {
            pinned = boolObj(body.get("pinned"));
        }
        String expireAt = body.containsKey("expireAt") ? str(body, "expireAt") : null;
        Boolean forceAck = body.containsKey("forceAck") ? boolObj(body.get("forceAck")) : null;
        String contentFmt = body.containsKey("contentFmt") ? str(body, "contentFmt") : null;
        try {
            Map<String, Object> m = NoticeStore.update(id, title, content, pinned, expireAt, forceAck, contentFmt);
            if (m == null) throw new BizException(ErrorCode.NOT_FOUND, "公告不存在");
            return R.ok(m);
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{id}/pin")
    public R<Map<String, Object>> pin(
            @PathVariable long id,
            @RequestBody(required = false) Map<String, Object> body,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        boolean on = true;
        if (body != null && body.containsKey("pinned")) {
            on = Boolean.TRUE.equals(boolObj(body.get("pinned")));
        }
        try {
            Map<String, Object> m = NoticeStore.setPinned(id, on);
            if (m == null) throw new BizException(ErrorCode.NOT_FOUND, "公告不存在");
            return R.ok(m);
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @DeleteMapping("/{id}")
    public R<Void> delete(@PathVariable long id, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        if (!NoticeStore.delete(id)) throw new BizException(ErrorCode.NOT_FOUND, "公告不存在");
        return R.ok(null);
    }

    private static UserStore.Profile publisher(HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        UserStore.Profile p = UserStore.get(uid);
        if (p == null) throw new BizException(ErrorCode.UNAUTHORIZED, "用户不存在");
        return p;
    }

    private static String str(Map<String, Object> body, String key) {
        Object v = body.get(key);
        return v == null ? "" : String.valueOf(v).trim();
    }

    private static Boolean boolObj(Object p) {
        if (p instanceof Boolean b) return b;
        if (p == null) return false;
        String s = String.valueOf(p).trim();
        return "1".equals(s) || "true".equalsIgnoreCase(s);
    }
}
