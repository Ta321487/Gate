package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.SeatStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/seats")
public class SeatController {

    private static void requireSeat() {
        if (!SeatStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通选座功能");
        }
    }

    @GetMapping("/shows")
    public R<List<Map<String, Object>>> shows(HttpSession session) {
        requireSeat();
        AdminAuth.requireLogin(session);
        return R.ok(SeatStore.listOpenShows());
    }

    @GetMapping("/shows/{id}/map")
    public R<Map<String, Object>> map(@PathVariable long id, HttpSession session) {
        requireSeat();
        AdminAuth.requireLogin(session);
        try {
            return R.ok(SeatStore.getMap(id));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/purchase")
    public R<Map<String, Object>> purchase(@RequestBody Map<String, Object> body, HttpSession session) {
        requireSeat();
        String uid = AdminAuth.requireLogin(session);
        try {
            long showId = 0L;
            Object sid = body == null ? null : body.get("showId");
            if (sid == null && body != null) sid = body.get("show_id");
            if (sid != null && !String.valueOf(sid).isBlank()) {
                showId = Long.parseLong(String.valueOf(sid));
            }
            @SuppressWarnings("unchecked")
            List<String> seats = body == null ? List.of() : (List<String>) body.get("seats");
            if (seats == null) seats = List.of();
            return R.ok(SeatStore.purchase(uid, showId, seats));
        } catch (ClassCastException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, "seats 须为座位号数组");
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
