package com.thesis.controller;

import com.thesis.capability.DeliveryWindowStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/delivery-windows")
public class DeliveryWindowController {

    private static void require() {
        if (!DeliveryWindowStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "配送时段未开启");
        }
    }

    @GetMapping("/options")
    public R<?> options(@RequestParam(required = false) String day, HttpSession session) {
        require();
        AdminAuth.requireLogin(session);
        try {
            return R.ok(DeliveryWindowStore.options(day));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/slots")
    public R<?> slots(HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        return R.ok(DeliveryWindowStore.listSlots());
    }

    @PostMapping("/slots")
    public R<?> saveSlot(@RequestBody(required = false) Map<String, Object> body, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(DeliveryWindowStore.saveSlot(body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/spans")
    public R<?> spans(HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        return R.ok(DeliveryWindowStore.listSpans());
    }

    @PostMapping("/spans")
    public R<?> saveSpan(@RequestBody(required = false) Map<String, Object> body, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(DeliveryWindowStore.saveSpan(body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
