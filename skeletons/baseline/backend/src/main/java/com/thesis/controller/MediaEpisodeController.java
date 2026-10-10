package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.MediaEpisodeStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/** 影音分集 API（C-05） */
@RestController
@RequestMapping("/api/media-episodes")
public class MediaEpisodeController {

    @GetMapping("/by-item/{itemId}")
    public R<?> list(@PathVariable long itemId) {
        if (!MediaEpisodeStore.enabled()) return R.ok(java.util.List.of());
        return R.ok(MediaEpisodeStore.listByItem(itemId));
    }

    @PostMapping("/admin")
    public R<?> save(@RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            Long id = body.get("id") == null ? null : Long.parseLong(String.valueOf(body.get("id")));
            long itemId = Long.parseLong(String.valueOf(body.get("itemId")));
            String title = body.get("title") == null ? "" : String.valueOf(body.get("title"));
            int sort = 0;
            if (body.get("sortOrd") != null && !String.valueOf(body.get("sortOrd")).isBlank()) {
                sort = Integer.parseInt(String.valueOf(body.get("sortOrd")).trim());
            }
            String url = body.get("mediaUrl") == null ? "" : String.valueOf(body.get("mediaUrl"));
            boolean notify = body.get("notify") == null
                    || "1".equals(String.valueOf(body.get("notify")))
                    || "true".equalsIgnoreCase(String.valueOf(body.get("notify")));
            return R.ok(MediaEpisodeStore.save(id, itemId, title, sort, url, notify));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (Exception e) {
            throw new BizException(ErrorCode.BAD_REQUEST, "保存失败");
        }
    }

    @DeleteMapping("/admin/{id}")
    public R<Void> delete(@PathVariable long id, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        if (!MediaEpisodeStore.delete(id)) throw new BizException(ErrorCode.NOT_FOUND, "分集不存在");
        return R.ok(null);
    }
}
