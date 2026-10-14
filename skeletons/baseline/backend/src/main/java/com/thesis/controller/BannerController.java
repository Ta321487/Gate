package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.BannerStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * XM-02 广告位：门户可读启用项；增删改仅超管。
 */
@RestController
@RequestMapping("/api/banners")
public class BannerController {

    @GetMapping
    public R<List<Map<String, Object>>> list(
            @RequestParam(defaultValue = "home") String slot,
            @RequestParam(defaultValue = "false") boolean all,
            HttpSession session) {
        if (all) {
            AdminAuth.requireSuperAdmin(session);
            return R.ok(BannerStore.listAll());
        }
        return R.ok(BannerStore.listEnabled(slot));
    }

    @PostMapping
    public R<Map<String, Object>> create(@RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            return R.ok(BannerStore.add(body == null ? Map.of() : body));
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
        Map<String, Object> m = BannerStore.update(id, body == null ? Map.of() : body);
        if (m == null) throw new BizException(ErrorCode.NOT_FOUND, "广告位不存在");
        return R.ok(m);
    }

    @DeleteMapping("/{id}")
    public R<Void> delete(@PathVariable long id, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        if (!BannerStore.delete(id)) throw new BizException(ErrorCode.NOT_FOUND, "广告位不存在");
        return R.ok(null);
    }
}
