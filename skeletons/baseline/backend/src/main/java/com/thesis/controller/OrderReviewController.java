package com.thesis.controller;

import com.thesis.capability.OrderReviewStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/order-reviews")
public class OrderReviewController {

    private static void require() {
        if (!OrderReviewStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "订单评价暂不可用");
        }
    }

    @GetMapping
    public R<?> page(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        require();
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
        if (admin) {
            AdminAuth.requireAdmin(session);
            return R.ok(OrderReviewStore.page(null, page, size));
        }
        String uid = AdminAuth.requireLogin(session);
        return R.ok(OrderReviewStore.page(uid, page, size));
    }

    @GetMapping("/by-order/{orderId}")
    public R<?> byOrder(@PathVariable long orderId, HttpSession session) {
        require();
        AdminAuth.requireLogin(session);
        return R.ok(OrderReviewStore.getByOrder(orderId));
    }

    @PostMapping
    public R<?> submit(@RequestBody Map<String, Object> body, HttpSession session) {
        require();
        String uid = AdminAuth.requireLogin(session);
        long orderId = Long.parseLong(String.valueOf(body.get("orderId")));
        int rating = Integer.parseInt(String.valueOf(body.get("rating")));
        String text = body.get("body") == null ? "" : String.valueOf(body.get("body"));
        try {
            return R.ok(OrderReviewStore.submit(uid, orderId, rating, text));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{id}/reply")
    public R<?> reply(@PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        String text = body == null || body.get("reply") == null ? "" : String.valueOf(body.get("reply"));
        try {
            return R.ok(OrderReviewStore.reply(id, text));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
