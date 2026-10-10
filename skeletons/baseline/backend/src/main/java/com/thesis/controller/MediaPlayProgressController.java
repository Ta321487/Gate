package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.capability.ArchiveStore;
import com.thesis.service.MediaPlayProgressStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/** 播放进度 API（C-05） */
@RestController
@RequestMapping("/api/media-progress")
public class MediaPlayProgressController {

    @GetMapping
    public R<?> get(
            @RequestParam long itemId,
            @RequestParam(defaultValue = "0") long episodeId,
            HttpSession session) {
        if (!MediaPlayProgressStore.enabled()) {
            return R.ok(Map.of("itemId", itemId, "episodeId", episodeId, "positionSec", 0, "completed", false));
        }
        String uid = AdminAuth.requireLogin(session);
        return R.ok(MediaPlayProgressStore.get(uid, itemId, episodeId));
    }

    @PostMapping
    public R<?> save(@RequestBody Map<String, Object> body, HttpSession session) {
        if (!MediaPlayProgressStore.enabled()) throw new BizException(ErrorCode.BAD_REQUEST, "未开放播放进度");
        String uid = AdminAuth.requireLogin(session);
        try {
            long itemId = Long.parseLong(String.valueOf(body.get("itemId")));
            long episodeId = 0L;
            if (body.get("episodeId") != null && !String.valueOf(body.get("episodeId")).isBlank()) {
                episodeId = Long.parseLong(String.valueOf(body.get("episodeId")).trim());
            }
            int pos = 0;
            if (body.get("positionSec") != null && !String.valueOf(body.get("positionSec")).isBlank()) {
                pos = Integer.parseInt(String.valueOf(body.get("positionSec")).trim());
            }
            boolean completed = "1".equals(String.valueOf(body.get("completed")))
                    || "true".equalsIgnoreCase(String.valueOf(body.get("completed")));
            Map<String, Object> saved = MediaPlayProgressStore.save(uid, itemId, episodeId, pos, completed);
            ArchiveStore.bumpPlayCount(itemId);
            return R.ok(saved);
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (Exception e) {
            throw new BizException(ErrorCode.BAD_REQUEST, "保存失败");
        }
    }
}
