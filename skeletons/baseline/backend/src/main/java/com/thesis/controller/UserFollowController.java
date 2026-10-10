package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.UserFollowStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/** C-08：用户关注（评论仅粉丝可见）。 */
@RestController
@RequestMapping("/api/user-follow")
public class UserFollowController {

    @GetMapping("/status")
    public R<Map<String, Object>> status(@RequestParam String followee, HttpSession session) {
        if (!UserFollowStore.enabled()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开放关注");
        }
        String uid = AdminAuth.requireLogin(session);
        boolean following = UserFollowStore.isFollowing(uid, followee);
        return R.ok(Map.of("followee", followee == null ? "" : followee, "following", following));
    }

    @PostMapping
    public R<Map<String, Object>> follow(@RequestBody Map<String, Object> body, HttpSession session) {
        if (!UserFollowStore.enabled()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开放关注");
        }
        String uid = AdminAuth.requireLogin(session);
        String followee = body == null || body.get("followee") == null ? "" : String.valueOf(body.get("followee"));
        try {
            return R.ok(UserFollowStore.follow(uid, followee));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @DeleteMapping
    public R<Map<String, Object>> unfollow(@RequestParam String followee, HttpSession session) {
        if (!UserFollowStore.enabled()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开放关注");
        }
        String uid = AdminAuth.requireLogin(session);
        try {
            return R.ok(UserFollowStore.unfollow(uid, followee));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
