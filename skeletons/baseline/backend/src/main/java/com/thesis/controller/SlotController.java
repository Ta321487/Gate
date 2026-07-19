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
        if (!SlotStore.enabled()) throw new BizException(ErrorCode.BAD_REQUEST, "预约能力未启用");
    }

    @GetMapping
    public R<?> list(
            @RequestParam(required = false) Long itemId,
            @RequestParam(required = false) String day,
            HttpSession session) {
        requireSlot();
        AdminAuth.requireLogin(session);
        return R.ok(SlotStore.listSlots(itemId, day));
    }

    @PostMapping("/reserve")
    public R<?> reserve(@RequestBody Map<String, Object> body, HttpSession session) {
        requireSlot();
        String uid = AdminAuth.requireLogin(session);
        long slotId = Long.parseLong(String.valueOf(body.get("slotId")));
        String remark = String.valueOf(body.getOrDefault("remark", ""));
        try {
            return R.ok(SlotStore.reserve(uid, slotId, remark));
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
