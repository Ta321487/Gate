package com.thesis.controller;

import com.thesis.capability.SlotStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/slots")
public class SlotController {

    private static void requireSlot() {
        if (!SlotStore.enabled()) throw new BizException(ErrorCode.BAD_REQUEST, "预约功能暂不可用");
    }

    @GetMapping
    public R<?> list(
            @RequestParam(required = false) Long itemId,
            @RequestParam(required = false) String day,
            HttpSession session) {
        requireSlot();
        // 游客可读时段；未登录由前端限量展示
        return R.ok(SlotStore.listSlots(itemId, day));
    }

    @PostMapping("/reserve")
    public R<?> reserve(@RequestBody Map<String, Object> body, HttpSession session) {
        requireSlot();
        String uid = AdminAuth.requireLogin(session);
        long slotId = Long.parseLong(String.valueOf(body.get("slotId")));
        String remark = String.valueOf(body.getOrDefault("remark", ""));
        try {
            return R.ok(SlotStore.reserve(uid, slotId, remark, body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/reservations/{id}/cancel")
    public R<?> cancel(@PathVariable long id, HttpSession session) {
        requireSlot();
        String uid = AdminAuth.requireLogin(session);
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
        try {
            return R.ok(SlotStore.cancel(id, uid, admin));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/reservations/{id}/confirm")
    public R<?> confirm(@PathVariable long id, HttpSession session) {
        requireSlot();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(SlotStore.confirm(id));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 履约办结：入场 / 就诊 / 到店完成 / 入住离店等 */
    @PostMapping("/reservations/{id}/complete")
    public R<?> complete(@PathVariable long id, HttpSession session) {
        requireSlot();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(SlotStore.complete(id));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 改约：取消原时段并预约新时段 */
    @PostMapping("/reservations/{id}/reschedule")
    public R<?> reschedule(
            @PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        requireSlot();
        String uid = AdminAuth.requireLogin(session);
        long newSlotId = Long.parseLong(String.valueOf(body.get("slotId")));
        try {
            return R.ok(SlotStore.reschedule(id, newSlotId, uid));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/reservations")
    public R<?> page(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String status,
            HttpSession session) {
        requireSlot();
        String uid = AdminAuth.requireLogin(session);
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
        return R.ok(SlotStore.pageReservations(admin ? null : uid, status, page, size));
    }

    @PostMapping("/generate")
    public R<?> generate(@RequestBody Map<String, Object> body, HttpSession session) {
        requireSlot();
        AdminAuth.requireSuperAdmin(session);
        long itemId = Long.parseLong(String.valueOf(body.get("itemId")));
        String day = String.valueOf(body.get("day"));
        int startHour = body.get("startHour") == null ? 9 : Integer.parseInt(String.valueOf(body.get("startHour")));
        int endHour = body.get("endHour") == null ? 17 : Integer.parseInt(String.valueOf(body.get("endHour")));
        int minutes = body.get("slotMinutes") == null ? 60 : Integer.parseInt(String.valueOf(body.get("slotMinutes")));
        int capacity = body.get("capacity") == null ? 1 : Integer.parseInt(String.valueOf(body.get("capacity")));
        int n = SlotStore.generateDaySlots(itemId, day, startHour, endHour, minutes, capacity);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("created", n);
        return R.ok(out);
    }
}
