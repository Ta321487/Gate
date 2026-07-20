package com.thesis.controller;

import com.thesis.capability.LoyaltyStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
public class LoyaltyController {

    @GetMapping("/api/loyalty/me")
    public R<?> me(HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        return R.ok(LoyaltyStore.getAccount(uid));
    }

    @GetMapping("/api/loyalty/ledger")
    public R<?> ledger(
            @RequestParam(defaultValue = "30") int limit,
            HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        return R.ok(LoyaltyStore.listLedger(uid, limit));
    }

    @PostMapping("/api/loyalty/preview")
    public R<?> preview(@RequestBody Map<String, Object> body, HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        double subtotal = toDouble(body == null ? null : body.get("subtotalYuan"));
        return R.ok(LoyaltyStore.previewPrice(subtotal, uid));
    }

    /** 管理端：仅演示余额可充值；积分不可充值 */
    @PostMapping("/api/admin/loyalty/recharge")
    public R<?> recharge(@RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireAdmin(session);
        if (!LoyaltyStore.isWalletEnabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "未开启演示余额");
        }
        String username = str(body == null ? null : body.get("username"));
        if (username.isBlank()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "请指定用户名");
        }
        double amount = toDouble(body.get("amount"));
        String operator = String.valueOf(session.getAttribute("username"));
        try {
            return R.ok(LoyaltyStore.adminRecharge(username, amount, operator));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static double toDouble(Object o) {
        if (o == null) return 0;
        if (o instanceof Number n) return n.doubleValue();
        try {
            return Double.parseDouble(String.valueOf(o).trim());
        } catch (Exception e) {
            return 0;
        }
    }
}
