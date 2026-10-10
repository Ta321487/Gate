package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.DoclibStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/doclib")
public class DoclibController {

    private static void requireDoclib() {
        if (!DoclibStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通文库功能");
        }
    }

    private static boolean isAdmin(HttpSession session) {
        return "admin".equals(String.valueOf(session.getAttribute("role")));
    }

    private static String roleOf(HttpSession session) {
        Object r = session.getAttribute("role");
        return r == null ? "" : String.valueOf(r);
    }

    @GetMapping("/items")
    public R<List<Map<String, Object>>> items(HttpSession session) {
        requireDoclib();
        AdminAuth.requireLogin(session);
        return R.ok(DoclibStore.listOpenItems(isAdmin(session)));
    }

    @GetMapping("/items/{id}")
    public R<Map<String, Object>> item(@PathVariable long id, HttpSession session) {
        requireDoclib();
        AdminAuth.requireLogin(session);
        Map<String, Object> item = DoclibStore.getItem(id);
        if (item == null) throw new BizException(ErrorCode.NOT_FOUND, "资料不存在");
        return R.ok(item);
    }

    @PostMapping("/items/{id}/download")
    public R<Map<String, Object>> download(@PathVariable long id, HttpSession session) {
        requireDoclib();
        String uid = AdminAuth.requireLogin(session);
        try {
            return R.ok(DoclibStore.download(uid, id, isAdmin(session), roleOf(session)));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/mine")
    public R<Map<String, Object>> mine(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        requireDoclib();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(DoclibStore.pageMine(uid, page, size));
    }

    @GetMapping("/tags/cloud")
    public R<List<Map<String, Object>>> tagCloud(
            @RequestParam(defaultValue = "30") int limit, HttpSession session) {
        requireDoclib();
        AdminAuth.requireLogin(session);
        return R.ok(DoclibStore.tagCloud(limit));
    }

    @GetMapping("/items/{id}/chapters")
    public R<List<Map<String, Object>>> chapters(@PathVariable long id, HttpSession session) {
        requireDoclib();
        AdminAuth.requireLogin(session);
        return R.ok(DoclibStore.listChapters(id));
    }

    @GetMapping("/items/{id}/versions")
    public R<List<Map<String, Object>>> versions(@PathVariable long id, HttpSession session) {
        requireDoclib();
        AdminAuth.requireLogin(session);
        return R.ok(DoclibStore.listVersions(id));
    }

    @PostMapping("/items/{id}/feedback")
    public R<Map<String, Object>> feedback(
            @PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        requireDoclib();
        String uid = AdminAuth.requireLogin(session);
        try {
            String kind = body == null ? "" : String.valueOf(body.getOrDefault("kind", ""));
            String text = body == null ? "" : String.valueOf(body.getOrDefault("body", ""));
            return R.ok(DoclibStore.submitFeedback(uid, id, kind, text));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/admin/logs")
    public R<Map<String, Object>> adminLogs(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) Long itemId,
            HttpSession session) {
        requireDoclib();
        AdminAuth.requireAdmin(session);
        return R.ok(DoclibStore.pageLogsAdmin(page, size, itemId));
    }

    @PutMapping("/admin/items/{id}")
    public R<Map<String, Object>> updateMeta(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        requireDoclib();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(DoclibStore.updateMeta(id, body == null ? Map.of() : body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/admin/items/{id}/chapters")
    public R<Map<String, Object>> saveChapter(
            @PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        requireDoclib();
        AdminAuth.requireAdmin(session);
        try {
            Long cid = null;
            if (body != null && body.get("id") != null && !String.valueOf(body.get("id")).isBlank()) {
                cid = Long.parseLong(String.valueOf(body.get("id")));
            }
            String title = body == null ? "" : String.valueOf(body.getOrDefault("title", ""));
            String anchor = body == null ? "" : String.valueOf(body.getOrDefault("anchor", ""));
            int sortOrd = 0;
            if (body != null && body.get("sortOrd") != null) {
                try {
                    sortOrd = Integer.parseInt(String.valueOf(body.get("sortOrd")));
                } catch (NumberFormatException ignored) {
                }
            }
            return R.ok(DoclibStore.saveChapter(cid, id, title, anchor, sortOrd));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @DeleteMapping("/admin/items/{itemId}/chapters/{id}")
    public R<Void> deleteChapter(
            @PathVariable long itemId, @PathVariable long id, HttpSession session) {
        requireDoclib();
        AdminAuth.requireAdmin(session);
        try {
            DoclibStore.deleteChapter(id, itemId);
            return R.ok(null);
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/admin/items/{id}/versions")
    public R<Map<String, Object>> addVersion(
            @PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        requireDoclib();
        AdminAuth.requireAdmin(session);
        try {
            String ver = body == null ? "" : String.valueOf(body.getOrDefault("versionNo", ""));
            String note = body == null ? "" : String.valueOf(body.getOrDefault("note", ""));
            return R.ok(DoclibStore.addVersion(id, ver, note));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/admin/feedback")
    public R<Map<String, Object>> adminFeedback(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String status,
            HttpSession session) {
        requireDoclib();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(DoclibStore.pageFeedbackAdmin(page, size, status));
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PutMapping("/admin/feedback/{id}")
    public R<Map<String, Object>> handleFeedback(
            @PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        requireDoclib();
        AdminAuth.requireAdmin(session);
        try {
            String st = body == null ? "handled" : String.valueOf(body.getOrDefault("status", "handled"));
            String note = body == null ? "" : String.valueOf(body.getOrDefault("handleNote", ""));
            return R.ok(DoclibStore.handleFeedback(id, st, note));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/admin/download-requests")
    public R<Map<String, Object>> downloadRequests(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String status,
            HttpSession session) {
        requireDoclib();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(DoclibStore.pageDownloadRequests(page, size, status));
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PutMapping("/admin/download-requests/{id}")
    public R<Map<String, Object>> handleDownloadRequest(
            @PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        requireDoclib();
        AdminAuth.requireAdmin(session);
        try {
            String st = body == null ? "approved" : String.valueOf(body.getOrDefault("status", "approved"));
            String note = body == null ? "" : String.valueOf(body.getOrDefault("handleNote", ""));
            return R.ok(DoclibStore.handleDownloadRequest(id, st, note));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
