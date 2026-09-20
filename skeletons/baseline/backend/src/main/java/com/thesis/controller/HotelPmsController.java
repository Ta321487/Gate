package com.thesis.controller;

import com.thesis.capability.FrontDeskStore;
import com.thesis.capability.RoomBoardStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.Map;

@RestController
@RequestMapping("/api/hotel-pms")
public class HotelPmsController {

    private void requireRoomBoard() {
        if (!RoomBoardStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "未开启房态板");
        }
    }

    private void requireFrontDesk() {
        if (!FrontDeskStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "未开启前台登记");
        }
    }

    private String staffPost(HttpSession session) {
        Object p = session.getAttribute("staffPost");
        return p == null ? "" : String.valueOf(p);
    }

    /** 清洁工只能做清洁；前台/总管可管房态与登记。 */
    private void forbidCleanerWriteFront(HttpSession session) {
        String post = staffPost(session);
        if ("housekeeping".equals(post)) {
            throw new BizException(ErrorCode.FORBIDDEN, "清洁岗不能办理登记或退房");
        }
    }

    @GetMapping("/rooms")
    public R<?> rooms(HttpSession session) {
        requireRoomBoard();
        AdminAuth.requireAdmin(session);
        return R.ok(RoomBoardStore.listRooms());
    }

    @GetMapping("/clean-tasks")
    public R<?> cleanTasks(HttpSession session) {
        requireRoomBoard();
        AdminAuth.requireAdmin(session);
        return R.ok(RoomBoardStore.dirtyRooms());
    }

    @PostMapping("/rooms/{id}/status")
    public R<?> setStatus(@PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        requireRoomBoard();
        AdminAuth.requireAdmin(session);
        String op = AdminAuth.requireLogin(session);
        try {
            String status = body == null ? "" : String.valueOf(body.getOrDefault("status", ""));
            String note = body == null ? "" : String.valueOf(body.getOrDefault("note", ""));
            if ("housekeeping".equals(staffPost(session)) && !RoomBoardStore.VACANT.equals(status)) {
                throw new BizException(ErrorCode.FORBIDDEN, "清洁岗只能将房间标为空房");
            }
            return R.ok(RoomBoardStore.setStatus(id, status, op, note));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/rooms/{id}/clean-done")
    public R<?> cleanDone(@PathVariable long id, HttpSession session) {
        requireRoomBoard();
        AdminAuth.requireAdmin(session);
        String op = AdminAuth.requireLogin(session);
        try {
            return R.ok(RoomBoardStore.completeClean(id, op));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/checkin/pending")
    public R<?> pendingCheckin(HttpSession session) {
        requireFrontDesk();
        AdminAuth.requireAdmin(session);
        forbidCleanerWriteFront(session);
        return R.ok(FrontDeskStore.pendingCheckin());
    }

    @GetMapping("/checkout/pending")
    public R<?> pendingCheckout(HttpSession session) {
        requireFrontDesk();
        AdminAuth.requireAdmin(session);
        forbidCleanerWriteFront(session);
        return R.ok(FrontDeskStore.pendingCheckout());
    }

    @PostMapping("/checkin")
    public R<?> checkin(@RequestBody Map<String, Object> body, HttpSession session) {
        requireFrontDesk();
        AdminAuth.requireAdmin(session);
        forbidCleanerWriteFront(session);
        String op = AdminAuth.requireLogin(session);
        try {
            long orderId = lng(body, "orderId");
            long roomId = lng(body, "roomId");
            String guest = str(body, "guestName");
            String idNo = str(body, "idNo");
            BigDecimal deposit = dec(body, "depositYuan");
            return R.ok(FrontDeskStore.checkin(orderId, roomId, guest, idNo, deposit, op));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/checkout/{checkinId}")
    public R<?> checkout(@PathVariable long checkinId, @RequestBody(required = false) Map<String, Object> body, HttpSession session) {
        requireFrontDesk();
        AdminAuth.requireAdmin(session);
        forbidCleanerWriteFront(session);
        String op = AdminAuth.requireLogin(session);
        try {
            String note = body == null ? "" : str(body, "note");
            return R.ok(FrontDeskStore.checkout(checkinId, note, op));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/consumption/{checkinId}")
    public R<?> listConsumption(@PathVariable long checkinId, HttpSession session) {
        requireFrontDesk();
        AdminAuth.requireAdmin(session);
        return R.ok(FrontDeskStore.consumptions(checkinId));
    }

    @PostMapping("/consumption/{checkinId}")
    public R<?> addConsumption(@PathVariable long checkinId, @RequestBody Map<String, Object> body, HttpSession session) {
        requireFrontDesk();
        AdminAuth.requireAdmin(session);
        forbidCleanerWriteFront(session);
        try {
            return R.ok(FrontDeskStore.addConsumption(checkinId, str(body, "title"), dec(body, "amountYuan")));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    private static String str(Map<String, Object> body, String key) {
        if (body == null || body.get(key) == null) return "";
        return String.valueOf(body.get(key));
    }

    private static long lng(Map<String, Object> body, String key) {
        if (body == null || body.get(key) == null) return 0L;
        Object v = body.get(key);
        if (v instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(String.valueOf(v));
        } catch (Exception e) {
            return 0L;
        }
    }

    private static BigDecimal dec(Map<String, Object> body, String key) {
        if (body == null || body.get(key) == null) return BigDecimal.ZERO;
        try {
            return new BigDecimal(String.valueOf(body.get(key)));
        } catch (Exception e) {
            return BigDecimal.ZERO;
        }
    }
}
