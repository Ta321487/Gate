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
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
        // 游客/用户只看未开始时段；管理端可看全日号源
        return R.ok(SlotStore.listSlots(itemId, day, !admin));
    }

    @PostMapping("/reserve")
    public R<?> reserve(@RequestBody Map<String, Object> body, HttpSession session) {
        requireSlot();
        String uid = AdminAuth.requireLogin(session);
        long slotId = 0L;
        Object rawSlot = body.get("slotId");
        if (rawSlot != null && !String.valueOf(rawSlot).isBlank() && !"null".equals(String.valueOf(rawSlot))) {
            slotId = Long.parseLong(String.valueOf(rawSlot));
        }
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

    /** 办结后服务评价：1～5 星 + 短评 */
    @PostMapping("/reservations/{id}/rate")
    public R<?> rate(
            @PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        requireSlot();
        String uid = AdminAuth.requireLogin(session);
        int rating = 0;
        Object ratingRaw = body.get("rating");
        if (ratingRaw != null && !String.valueOf(ratingRaw).isBlank()
                && !"null".equalsIgnoreCase(String.valueOf(ratingRaw))) {
            try {
                rating = Integer.parseInt(String.valueOf(ratingRaw));
            } catch (Exception e) {
                throw new BizException(ErrorCode.BAD_REQUEST, "请选择 1～5 分");
            }
        }
        String note = body.get("remark") == null
                ? (body.get("ratingRemark") == null ? "" : String.valueOf(body.get("ratingRemark")))
                : String.valueOf(body.get("remark"));
        note = note == null ? "" : note.trim();
        try {
            return R.ok(SlotStore.rate(id, uid, rating, note));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 签到（可记迟到；科室口令可选） */
    @PostMapping("/reservations/{id}/checkin")
    public R<?> checkIn(
            @PathVariable long id,
            @RequestBody(required = false) Map<String, Object> body,
            HttpSession session) {
        requireSlot();
        String uid = AdminAuth.requireLogin(session);
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")))
                || "super_admin".equals(String.valueOf(session.getAttribute("role")));
        String code = body == null ? null : String.valueOf(body.getOrDefault("checkinCode", ""));
        try {
            return R.ok(SlotStore.checkIn(id, uid, admin, code));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 车位：登记离场并估算时长费 */
    @PostMapping("/reservations/{id}/exit")
    public R<?> markExit(@PathVariable long id, HttpSession session) {
        requireSlot();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(SlotStore.markExit(id));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 车位：登记超时加收 */
    @PostMapping("/reservations/{id}/overtime-fee")
    public R<?> overtimeFee(
            @PathVariable long id,
            @RequestBody(required = false) Map<String, Object> body,
            HttpSession session) {
        requireSlot();
        AdminAuth.requireAdmin(session);
        try {
            java.math.BigDecimal yuan = null;
            if (body != null && body.get("yuan") != null && !String.valueOf(body.get("yuan")).isBlank()) {
                yuan = new java.math.BigDecimal(String.valueOf(body.get("yuan")));
            }
            return R.ok(SlotStore.registerOvertimeFee(id, yuan));
        } catch (NumberFormatException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, "金额格式不正确");
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 客房：续住改离店日 */
    @PostMapping("/reservations/{id}/extend-stay")
    public R<?> extendStay(
            @PathVariable long id,
            @RequestBody(required = false) Map<String, Object> body,
            HttpSession session) {
        requireSlot();
        String user = AdminAuth.requireLogin(session);
        boolean asAdmin = "admin".equals(String.valueOf(session.getAttribute("role")))
                || "super_admin".equals(String.valueOf(session.getAttribute("role")));
        try {
            String stayTo = body == null ? null : String.valueOf(body.getOrDefault("stayTo", ""));
            return R.ok(SlotStore.extendStay(id, user, asAdmin, stayTo));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 客房：延迟退房加收 */
    @PostMapping("/reservations/{id}/late-checkout-fee")
    public R<?> lateCheckoutFee(
            @PathVariable long id,
            @RequestBody(required = false) Map<String, Object> body,
            HttpSession session) {
        requireSlot();
        AdminAuth.requireAdmin(session);
        try {
            java.math.BigDecimal yuan = null;
            if (body != null && body.get("yuan") != null && !String.valueOf(body.get("yuan")).isBlank()) {
                yuan = new java.math.BigDecimal(String.valueOf(body.get("yuan")));
            }
            return R.ok(SlotStore.registerLateCheckoutFee(id, yuan));
        } catch (NumberFormatException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, "金额格式不正确");
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 客房：定金尾款/早餐券/加床/查房清单等 */
    @PostMapping("/reservations/{id}/hotel-patch")
    public R<?> hotelPatch(
            @PathVariable long id,
            @RequestBody(required = false) Map<String, Object> body,
            HttpSession session) {
        requireSlot();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(SlotStore.patchHotel(id, body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 租车：里程超支加收 */
    @PostMapping("/reservations/{id}/mileage-over-fee")
    public R<?> mileageOverFee(
            @PathVariable long id,
            @RequestBody(required = false) Map<String, Object> body,
            HttpSession session) {
        requireSlot();
        AdminAuth.requireAdmin(session);
        try {
            java.math.BigDecimal yuan = null;
            if (body != null && body.get("yuan") != null && !String.valueOf(body.get("yuan")).isBlank()) {
                yuan = new java.math.BigDecimal(String.valueOf(body.get("yuan")));
            }
            return R.ok(SlotStore.registerMileageOverFee(id, yuan));
        } catch (NumberFormatException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, "金额格式不正确");
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 租车：ETC 通行费 */
    @PostMapping("/reservations/{id}/etc-fee")
    public R<?> etcFee(
            @PathVariable long id,
            @RequestBody(required = false) Map<String, Object> body,
            HttpSession session) {
        requireSlot();
        AdminAuth.requireAdmin(session);
        try {
            java.math.BigDecimal yuan = null;
            if (body != null && body.get("yuan") != null && !String.valueOf(body.get("yuan")).isBlank()) {
                yuan = new java.math.BigDecimal(String.valueOf(body.get("yuan")));
            }
            return R.ok(SlotStore.registerEtcFee(id, yuan));
        } catch (NumberFormatException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, "金额格式不正确");
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 租车：违章预留押/验车/保险/驾照期/附件等 */
    @PostMapping("/reservations/{id}/carrent-patch")
    public R<?> carrentPatch(
            @PathVariable long id,
            @RequestBody(required = false) Map<String, Object> body,
            HttpSession session) {
        requireSlot();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(SlotStore.patchCarrent(id, body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 仪器：耗材领用 / 培训确认等 */
    @PostMapping("/reservations/{id}/instrument-patch")
    public R<?> instrumentPatch(
            @PathVariable long id,
            @RequestBody(required = false) Map<String, Object> body,
            HttpSession session) {
        requireSlot();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(SlotStore.patchInstrument(id, body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 停诊：取消维护期内预约并发信 */
    @PostMapping("/items/{itemId}/stop-notify")
    public R<?> stopNotify(@PathVariable long itemId, HttpSession session) {
        requireSlot();
        AdminAuth.requireAdmin(session);
        try {
            int n = SlotStore.notifyStopAndCancel(itemId);
            return R.ok(Map.of("cancelled", n));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 管理端标记爽约 */
    @PostMapping("/reservations/{id}/no-show")
    public R<?> markNoShow(@PathVariable long id, HttpSession session) {
        requireSlot();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(SlotStore.markNoShow(id));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 资源按日月容量着色 */
    @GetMapping("/day-fill")
    public R<?> dayFill(
            @RequestParam long itemId,
            @RequestParam(required = false) String month,
            HttpSession session) {
        requireSlot();
        AdminAuth.requireLogin(session);
        return R.ok(SlotStore.dayFill(itemId, month));
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
        int weeks = 0;
        if (body.get("weeks") != null && !String.valueOf(body.get("weeks")).isBlank()) {
            weeks = Integer.parseInt(String.valueOf(body.get("weeks")));
        }
        int n = weeks > 1
                ? SlotStore.generateWeeklySlots(itemId, day, weeks, startHour, endHour, minutes, capacity)
                : SlotStore.generateDaySlots(itemId, day, startHour, endHour, minutes, capacity);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("created", n);
        return R.ok(out);
    }

    /** 会议室：时段已约人（冲突说明） */
    @GetMapping("/{slotId}/occupants")
    public R<?> occupants(@PathVariable long slotId, HttpSession session) {
        requireSlot();
        AdminAuth.requireLogin(session);
        return R.ok(SlotStore.listSlotOccupants(slotId));
    }

    /** 美业：本人到店次数（已签到累计） */
    @GetMapping("/my-visit-count")
    public R<?> myVisitCount(HttpSession session) {
        requireSlot();
        String uid = AdminAuth.requireLogin(session);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("visitCount", SlotStore.visitCount(uid));
        return R.ok(out);
    }

    /** 美业：登记改约手续费 */
    @PostMapping("/reservations/{id}/reschedule-fee")
    public R<?> rescheduleFee(
            @PathVariable long id,
            @RequestBody(required = false) Map<String, Object> body,
            HttpSession session) {
        requireSlot();
        AdminAuth.requireSuperAdmin(session);
        try {
            java.math.BigDecimal yuan = null;
            if (body != null && body.get("rescheduleFeeYuan") != null
                    && !String.valueOf(body.get("rescheduleFeeYuan")).isBlank()) {
                yuan = new java.math.BigDecimal(String.valueOf(body.get("rescheduleFeeYuan")));
            }
            return R.ok(SlotStore.registerRescheduleFee(id, yuan));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 会议室：门禁密码 / 录屏 / 视频链接 / 召开中 / 纪要附件 */
    @PostMapping("/reservations/{id}/meeting")
    public R<?> patchMeeting(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        requireSlot();
        String uid = AdminAuth.requireLogin(session);
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")))
                || "super_admin".equals(String.valueOf(session.getAttribute("role")));
        try {
            String minutes = body.containsKey("minutesAttach")
                    ? String.valueOf(body.getOrDefault("minutesAttach", ""))
                    : null;
            if (!admin) {
                // 用户仅可上传本人预约的纪要
                if (minutes == null) {
                    throw new IllegalStateException("无权修改");
                }
                Map<String, Object> mine = SlotStore.getReservation(id);
                if (mine == null) throw new IllegalArgumentException("预约不存在");
                if (!uid.equals(String.valueOf(mine.get("username")))) {
                    throw new IllegalStateException("无权修改他人预约");
                }
                return R.ok(SlotStore.patchMeeting(id, null, null, null, null, minutes));
            }
            String door = body.containsKey("doorCode") ? String.valueOf(body.get("doorCode")) : null;
            String rec = body.containsKey("recordingUrl") ? String.valueOf(body.get("recordingUrl")) : null;
            String video = body.containsKey("videoUrl") ? String.valueOf(body.get("videoUrl")) : null;
            String stage = body.containsKey("meetingStage") ? String.valueOf(body.get("meetingStage")) : null;
            return R.ok(SlotStore.patchMeeting(id, door, rec, video, stage, minutes));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
