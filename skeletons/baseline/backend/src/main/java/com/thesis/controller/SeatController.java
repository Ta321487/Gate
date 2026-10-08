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

    private static boolean truthy(Object o) {
        if (o == null) return false;
        if (o instanceof Boolean b) return b;
        String s = String.valueOf(o).trim();
        return "1".equals(s) || "true".equalsIgnoreCase(s) || "yes".equalsIgnoreCase(s);
    }

    private static long parseShowId(Map<String, Object> body) {
        long showId = 0L;
        Object sid = body == null ? null : body.get("showId");
        if (sid == null && body != null) sid = body.get("show_id");
        if (sid != null && !String.valueOf(sid).isBlank()) {
            showId = Long.parseLong(String.valueOf(sid));
        }
        return showId;
    }

    @SuppressWarnings("unchecked")
    private static List<String> parseSeats(Map<String, Object> body) {
        List<String> seats = body == null ? List.of() : (List<String>) body.get("seats");
        return seats == null ? List.of() : seats;
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> parseSnacks(Map<String, Object> body) {
        Object raw = body == null ? null : body.get("snacks");
        if (!(raw instanceof List<?> list) || list.isEmpty()) return List.of();
        List<Map<String, Object>> out = new java.util.ArrayList<>();
        for (Object o : list) {
            if (o instanceof Map<?, ?> m) {
                Map<String, Object> row = new java.util.LinkedHashMap<>();
                for (Map.Entry<?, ?> e : m.entrySet()) {
                    if (e.getKey() != null) row.put(String.valueOf(e.getKey()), e.getValue());
                }
                out.add(row);
            }
        }
        return out;
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
        String uid = AdminAuth.requireLogin(session);
        try {
            return R.ok(SeatStore.getMap(id, uid));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/hold")
    public R<Map<String, Object>> hold(@RequestBody Map<String, Object> body, HttpSession session) {
        requireSeat();
        String uid = AdminAuth.requireLogin(session);
        try {
            return R.ok(SeatStore.holdSeats(uid, parseShowId(body), parseSeats(body)));
        } catch (ClassCastException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, "seats 须为座位号数组");
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/purchase")
    public R<Map<String, Object>> purchase(@RequestBody Map<String, Object> body, HttpSession session) {
        requireSeat();
        String uid = AdminAuth.requireLogin(session);
        try {
            boolean notice = truthy(body == null ? null : body.get("noticeAgreed"));
            return R.ok(SeatStore.purchase(uid, parseShowId(body), parseSeats(body), notice, parseSnacks(body)));
        } catch (ClassCastException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, "seats 须为座位号数组");
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/snacks")
    public R<List<Map<String, Object>>> snacks(HttpSession session) {
        requireSeat();
        AdminAuth.requireLogin(session);
        return R.ok(SeatStore.listOpenSnacks());
    }

    @GetMapping("/snacks/all")
    public R<List<Map<String, Object>>> snacksAll(HttpSession session) {
        requireSeat();
        AdminAuth.requireAdmin(session);
        return R.ok(SeatStore.listAllSnacks());
    }

    @PutMapping("/snacks")
    public R<Map<String, Object>> saveSnack(@RequestBody Map<String, Object> body, HttpSession session) {
        requireSeat();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(SeatStore.saveSnack(body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PutMapping("/shows/{id}/attrs")
    public R<Map<String, Object>> updateAttrs(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        requireSeat();
        AdminAuth.requireAdmin(session);
        try {
            Map<String, String> attrs = new java.util.LinkedHashMap<>();
            Object raw = body == null ? null : body.get("attrs");
            if (raw instanceof Map<?, ?> m) {
                for (Map.Entry<?, ?> e : m.entrySet()) {
                    if (e.getKey() == null) continue;
                    attrs.put(String.valueOf(e.getKey()), e.getValue() == null ? "" : String.valueOf(e.getValue()));
                }
            }
            SeatStore.updateSeatAttrs(id, attrs);
            return R.ok(SeatStore.getMap(id, AdminAuth.requireLogin(session)));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
