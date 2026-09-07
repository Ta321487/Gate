package com.thesis.controller;

import com.thesis.capability.ArchiveStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.GuestTeaser;
import com.thesis.common.R;
import com.thesis.service.GuestbookStore;
import com.thesis.service.UserStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * 门户留言：列表可读；发表需登录；删除/回复仅平台超管。
 * 多店：channel=user（买家↔平台）/ merchant（商家↔平台）。
 */
@RestController
@RequestMapping("/api/guestbook")
public class GuestbookController {

    @GetMapping
    public R<Map<String, Object>> page(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String channel,
            HttpSession session) {
        if (!GuestbookStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通留言功能");
        }
        int p = GuestTeaser.clampPage(session, page);
        int s = GuestTeaser.clampSize(session, size);
        boolean mp = ArchiveStore.shopMarketplaceEnabled() && GuestbookStore.hasChannel();
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
        boolean superAdmin = AdminAuth.isSuperAdmin(session);
        String uid = session.getAttribute("username") == null
                ? ""
                : String.valueOf(session.getAttribute("username"));
        if (mp) {
            if (superAdmin) {
                // 平台：按通道筛选；未传 channel 时默认用户留言
                String ch = (channel == null || channel.isBlank()) ? "user" : channel;
                return R.ok(GuestbookStore.page(p, s, ch, null));
            }
            if (admin) {
                // 商家：只看自己发给平台的留言
                return R.ok(GuestbookStore.page(p, s, "merchant", uid));
            }
            // 买家门户：只看买家通道（公开板）
            return R.ok(GuestbookStore.page(p, s, "user", null));
        }
        return R.ok(GuestbookStore.page(p, s));
    }

    @PostMapping
    public R<Map<String, Object>> create(@RequestBody Map<String, String> body, HttpSession session) {
        if (!GuestbookStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通留言功能");
        }
        String uid = AdminAuth.requireLogin(session);
        UserStore.Profile p = UserStore.get(uid);
        if (p == null) throw new BizException(ErrorCode.UNAUTHORIZED, "用户不存在");
        String text = body == null ? "" : body.getOrDefault("body", "");
        if (text == null || text.isBlank()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "留言内容不能为空");
        }
        String channel = "user";
        if (ArchiveStore.shopMarketplaceEnabled() && GuestbookStore.hasChannel()) {
            boolean merchant = "admin".equals(p.role)
                    && !p.superAdmin
                    && "shop_merchant".equals(p.staffPost == null ? "" : p.staffPost.trim());
            channel = merchant ? "merchant" : "user";
            // 平台超管不在此板自说自话
            if (p.superAdmin) {
                throw new BizException(ErrorCode.BAD_REQUEST, "平台管理员请在后台回复留言，勿自助发表");
            }
        }
        Map<String, Object> row = GuestbookStore.add(p.username, p.nickname, text, channel);
        if (row == null) throw new BizException(ErrorCode.BAD_REQUEST, "留言失败");
        return R.ok(row);
    }

    @PutMapping("/{id}/reply")
    public R<Map<String, Object>> reply(
            @PathVariable long id,
            @RequestBody Map<String, String> body,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        if (!GuestbookStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通留言功能");
        }
        String uid = AdminAuth.requireLogin(session);
        String reply = body == null ? "" : body.getOrDefault("reply", "");
        if (reply == null || reply.isBlank()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "回复不能为空");
        }
        Map<String, Object> row = GuestbookStore.reply(id, reply, uid);
        if (row == null) throw new BizException(ErrorCode.NOT_FOUND, "留言不存在");
        return R.ok(row);
    }

    @DeleteMapping("/{id}")
    public R<Void> delete(@PathVariable long id, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        if (!GuestbookStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通留言功能");
        }
        if (!GuestbookStore.delete(id)) throw new BizException(ErrorCode.NOT_FOUND, "留言不存在");
        return R.ok(null);
    }
}
