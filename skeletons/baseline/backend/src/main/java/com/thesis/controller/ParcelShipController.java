package com.thesis.controller;

import com.thesis.capability.ParcelShipStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
public class ParcelShipController {

    @PostMapping("/api/parcel-ship")
    public R<?> submit(@RequestBody Map<String, Object> body, HttpSession session) {
        requireEnabled();
        String uid = AdminAuth.requireLogin(session);
        try {
            return R.ok(ParcelShipStore.submit(
                    uid,
                    str(body.get("receiverName")),
                    str(body.get("receiverPhone")),
                    str(body.get("destAddress")),
                    str(body.get("itemDesc"))));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/api/parcel-ship/mine")
    public R<?> mine(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        requireEnabled();
        String uid = AdminAuth.requireLogin(session);
        try {
            return R.ok(ParcelShipStore.pageMine(uid, page, size));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/api/admin/parcel-ship")
    public R<?> adminPage(
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String username,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            HttpSession session) {
        requireEnabled();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(ParcelShipStore.page(username, status, page, size));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/api/admin/parcel-ship/{id}/resolve")
    public R<?> resolve(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        requireEnabled();
        AdminAuth.requireAdmin(session);
        String op = AdminAuth.requireLogin(session);
        try {
            return R.ok(ParcelShipStore.resolve(
                    id,
                    str(body.get("action")),
                    op,
                    str(body.get("note")),
                    str(body.get("trackingNo"))));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    private static void requireEnabled() {
        if (!ParcelShipStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "寄件功能暂不可用");
        }
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }
}
