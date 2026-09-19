package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.LostMessageStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/lost/message")
public class LostMessageController {

    private static void requireClue() {
        if (!LostMessageStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通线索留言");
        }
    }

    @GetMapping
    public R<List<Map<String, Object>>> list(
            @RequestParam(required = false) Long lostItemId,
            HttpSession session) {
        requireClue();
        if (lostItemId != null && lostItemId > 0) {
            return R.ok(LostMessageStore.listByItem(lostItemId));
        }
        AdminAuth.requireAdmin(session);
        return R.ok(LostMessageStore.listRecent(100));
    }

    /** 公开发表：登录记 user_id；未登录须 guestName。 */
    @PostMapping
    public R<Map<String, Object>> post(@RequestBody Map<String, Object> body, HttpSession session) {
        requireClue();
        long itemId = 0L;
        if (body != null && body.get("lostItemId") instanceof Number n) itemId = n.longValue();
        else if (body != null && body.get("lostItemId") != null) {
            try {
                itemId = Long.parseLong(String.valueOf(body.get("lostItemId")).trim());
            } catch (Exception ignored) {
                itemId = 0L;
            }
        }
        String userId = null;
        Object uid = session == null ? null : session.getAttribute("uid");
        if (uid != null) userId = String.valueOf(uid);
        String guestName = body == null || body.get("guestName") == null ? "" : String.valueOf(body.get("guestName"));
        String guestContact = body == null || body.get("guestContact") == null ? "" : String.valueOf(body.get("guestContact"));
        String content = body == null || body.get("content") == null ? "" : String.valueOf(body.get("content"));
        String type = body == null || body.get("type") == null ? "clue" : String.valueOf(body.get("type"));
        try {
            long id = LostMessageStore.post(itemId, userId, guestName, guestContact, content, type);
            return R.ok(Map.of("id", id));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
