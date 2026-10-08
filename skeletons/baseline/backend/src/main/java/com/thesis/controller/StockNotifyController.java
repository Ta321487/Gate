package com.thesis.controller;

import com.thesis.capability.StockNotifyStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/** T-09：缺货到货订阅。 */
@RestController
@RequestMapping("/api/stock-notify")
public class StockNotifyController {

    @PostMapping
    public R<?> subscribe(@RequestBody Map<String, Object> body, HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        long itemId = 0;
        if (body != null && body.get("itemId") != null) {
            try {
                itemId = Long.parseLong(String.valueOf(body.get("itemId")));
            } catch (Exception ignored) {
            }
        }
        try {
            return R.ok(StockNotifyStore.subscribe(uid, itemId));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/mine")
    public R<?> mine(HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        return R.ok(StockNotifyStore.listMine(uid));
    }

    @GetMapping("/status")
    public R<?> status(@RequestParam long itemId, HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        return R.ok(Map.of(
                "itemId", itemId,
                "subscribed", StockNotifyStore.isSubscribed(uid, itemId)));
    }
}
