package com.thesis.controller;

import com.thesis.capability.ConsignStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/consigns")
public class ConsignController {

    private static void require() {
        if (!ConsignStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "寄卖未开启");
        }
    }

    private static String username(HttpSession session) {
        return AdminAuth.requireLogin(session);
    }

    @GetMapping("/mine")
    public R<?> mine(HttpSession session) {
        require();
        return R.ok(ConsignStore.mine(username(session)));
    }

    @GetMapping("/rate")
    public R<?> rate(HttpSession session) {
        require();
        AdminAuth.requireLogin(session);
        return R.ok(ConsignStore.rate());
    }

    @PostMapping
    public R<?> submit(@RequestBody Map<String, Object> body, HttpSession session) {
        require();
        return R.ok(ConsignStore.submit(
                username(session),
                body == null ? "" : String.valueOf(body.getOrDefault("title", "")),
                body == null ? null : body.get("expectYuan"),
                body == null ? "" : String.valueOf(body.getOrDefault("conditionNote", ""))));
    }

    @PostMapping("/withdraw")
    public R<?> withdraw(@RequestBody Map<String, Object> body, HttpSession session) {
        require();
        long id = 0;
        if (body != null && body.get("id") instanceof Number n) id = n.longValue();
        return R.ok(ConsignStore.withdraw(username(session), id));
    }

    @GetMapping
    public R<?> list(HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        return R.ok(ConsignStore.listAdmin());
    }

    @PostMapping("/rate")
    public R<?> saveRate(@RequestBody Map<String, Object> body, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        int percent = 0;
        if (body != null && body.get("feePercent") instanceof Number n) percent = n.intValue();
        return R.ok(ConsignStore.saveRate(percent));
    }

    @PostMapping("/pass")
    public R<?> pass(@RequestBody Map<String, Object> body, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        long id = body != null && body.get("id") instanceof Number n ? n.longValue() : 0;
        return R.ok(ConsignStore.pass(id));
    }

    @PostMapping("/reject")
    public R<?> reject(@RequestBody Map<String, Object> body, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        long id = body != null && body.get("id") instanceof Number n ? n.longValue() : 0;
        String reason = body == null ? "" : String.valueOf(body.getOrDefault("reason", ""));
        return R.ok(ConsignStore.reject(id, reason));
    }

    @GetMapping("/ledgers")
    public R<?> ledgers(HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        return R.ok(ConsignStore.ledgers());
    }

    @PostMapping("/pay")
    public R<?> pay(@RequestBody Map<String, Object> body, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        long id = body != null && body.get("id") instanceof Number n ? n.longValue() : 0;
        return R.ok(ConsignStore.pay(id));
    }
}
