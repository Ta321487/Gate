package com.thesis.controller;

import com.thesis.capability.RentalBondStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/rental-bond")
public class RentalBondController {

    private void requireOn() {
        if (!RentalBondStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "未开启租赁押金验损");
        }
    }

    @GetMapping("/inspect")
    public R<?> pending(HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        return R.ok(RentalBondStore.pendingInspect());
    }

    @PostMapping("/inspect/{id}")
    public R<?> inspect(@PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        try {
            String note = body == null ? "" : String.valueOf(body.getOrDefault("note", ""));
            Object deduct = body == null ? 0 : body.get("deductYuan");
            boolean repair = body != null && Boolean.TRUE.equals(body.get("repair"));
            return R.ok(RentalBondStore.inspect(id, note, deduct, repair));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
