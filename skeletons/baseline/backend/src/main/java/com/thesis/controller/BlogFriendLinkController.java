package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.BlogFriendLinkStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/** 友情链接 API（C-04） */
@RestController
@RequestMapping("/api/blog-friend-links")
public class BlogFriendLinkController {

    @GetMapping
    public R<?> listPublic() {
        if (!BlogFriendLinkStore.enabled()) return R.ok(java.util.List.of());
        return R.ok(BlogFriendLinkStore.listPublic());
    }

    @GetMapping("/admin")
    public R<?> listAdmin(HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        if (!BlogFriendLinkStore.enabled()) throw new BizException(ErrorCode.BAD_REQUEST, "未开放友情链接");
        return R.ok(BlogFriendLinkStore.listAdmin());
    }

    @PostMapping("/admin")
    public R<?> save(@RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            Long id = body.get("id") == null ? null : Long.parseLong(String.valueOf(body.get("id")));
            String title = body.get("title") == null ? "" : String.valueOf(body.get("title"));
            String url = body.get("url") == null ? "" : String.valueOf(body.get("url"));
            int sort = 0;
            if (body.get("sortOrder") != null && !String.valueOf(body.get("sortOrder")).isBlank()) {
                sort = Integer.parseInt(String.valueOf(body.get("sortOrder")).trim());
            }
            boolean on = body.get("enabled") == null
                    || "1".equals(String.valueOf(body.get("enabled")))
                    || "true".equalsIgnoreCase(String.valueOf(body.get("enabled")));
            return R.ok(BlogFriendLinkStore.save(id, title, url, sort, on));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (Exception e) {
            throw new BizException(ErrorCode.BAD_REQUEST, "保存失败");
        }
    }

    @DeleteMapping("/admin/{id}")
    public R<Void> delete(@PathVariable long id, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        if (!BlogFriendLinkStore.delete(id)) throw new BizException(ErrorCode.NOT_FOUND, "链接不存在");
        return R.ok(null);
    }
}
