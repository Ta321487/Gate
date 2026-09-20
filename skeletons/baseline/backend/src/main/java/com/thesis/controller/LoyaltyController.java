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
        String coupon = str(body == null ? null : body.get("couponCode"));
        Integer offsetPts = null;
        if (body != null && body.get("offsetPoints") != null && !str(body.get("offsetPoints")).isBlank()) {
            try {
                offsetPts = Integer.parseInt(str(body.get("offsetPoints")));
            } catch (Exception ignored) {
                offsetPts = 0;
            }
        }
        return R.ok(LoyaltyStore.previewPrice(subtotal, uid, coupon, offsetPts));
    }

    /** 买家端充值（固定档位）；商家/管理岗禁止自充 */
    @PostMapping("/api/loyalty/demo-recharge")
    public R<?> demoRecharge(@RequestBody Map<String, Object> body, HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        if ("admin".equals(String.valueOf(session.getAttribute("role")))) {
            throw new BizException(ErrorCode.FORBIDDEN, "商家与管理账号不可充值买家余额");
        }
        if (!LoyaltyStore.isWalletEnabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "未开启账户余额");
        }
        double amount = toDouble(body == null ? null : body.get("amount"));
        try {
            return R.ok(LoyaltyStore.demoRecharge(uid, amount));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 管理端：仅账户余额可充值；积分不可充值 */
    @PostMapping("/api/admin/loyalty/recharge")
    public R<?> recharge(@RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireAdmin(session);
        if (!LoyaltyStore.isWalletEnabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "未开启账户余额");
        }
        String username = str(body == null ? null : body.get("username"));
        if (username.isBlank()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "请指定用户名");
        }
        double amount = toDouble(body.get("amount"));
        String operator = AdminAuth.requireLogin(session);
        try {
            return R.ok(LoyaltyStore.adminRecharge(username, amount, operator));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 管理端：给买家加积分（开题写了管理充积分时开放） */
    @PostMapping("/api/admin/loyalty/credit-points")
    public R<?> creditPoints(@RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireAdmin(session);
        if (!LoyaltyStore.isPointsEnabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "未开启积分");
        }
        String username = str(body == null ? null : body.get("username"));
        if (username.isBlank()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "请指定用户名");
        }
        int points = toInt(body == null ? null : body.get("points"));
        String remark = str(body == null ? null : body.get("remark"));
        String operator = AdminAuth.requireLogin(session);
        try {
            return R.ok(LoyaltyStore.adminCreditPoints(username, points, operator, remark));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static int toInt(Object o) {
        if (o == null) return 0;
        if (o instanceof Number n) return n.intValue();
        try {
            return Integer.parseInt(String.valueOf(o).trim());
        } catch (Exception e) {
            return 0;
        }
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
