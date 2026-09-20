package com.thesis.controller;

import com.thesis.capability.WeighSaleStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/weigh")
public class WeighSaleController {

    private static void require() {
        if (!WeighSaleStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "按重量未开启");
        }
    }

    private static String username(HttpSession session) {
        AdminAuth.requireLogin(session);
        Object user = session.getAttribute("username");
        return user == null ? "" : String.valueOf(user);
    }

    private static long idOf(Map<String, Object> body) {
        if (body != null && body.get("id") instanceof Number n) return n.longValue();
        if (body != null && body.get("orderId") instanceof Number n) return n.longValue();
        return 0;
    }

    @GetMapping("/policy")
    public R<?> policy(HttpSession session) {
        require();
        AdminAuth.requireLogin(session);
        return R.ok(WeighSaleStore.policy());
    }

    @PostMapping("/policy")
    public R<?> savePolicy(@RequestBody Map<String, Object> body, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        boolean on = body != null && Boolean.TRUE.equals(body.get("enabled"));
        if (body != null && body.get("enabled") instanceof Number n) on = n.intValue() != 0;
        return R.ok(WeighSaleStore.savePolicy(on, body == null ? null : body.get("capYuan")));
    }

    @GetMapping("/mine")
    public R<?> mine(HttpSession session) {
        require();
        return R.ok(WeighSaleStore.mine(username(session)));
    }

    @PostMapping("/claims")
    public R<?> submit(@RequestBody Map<String, Object> body, HttpSession session) {
        require();
        long orderId = body != null && body.get("orderId") instanceof Number n ? n.longValue() : 0;
        return R.ok(WeighSaleStore.submit(
                username(session),
                orderId,
                body == null ? null : body.get("amountYuan"),
                body == null ? "" : String.valueOf(body.getOrDefault("reason", ""))));
    }

    @GetMapping("/claims")
    public R<?> list(HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        return R.ok(WeighSaleStore.listAdmin());
    }

    @PostMapping("/pass")
    public R<?> pass(@RequestBody Map<String, Object> body, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        return R.ok(WeighSaleStore.approve(idOf(body)));
    }

    @PostMapping("/reject")
    public R<?> reject(@RequestBody Map<String, Object> body, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        String reason = body == null ? "" : String.valueOf(body.getOrDefault("reason", ""));
        return R.ok(WeighSaleStore.reject(idOf(body), reason));
    }
}
