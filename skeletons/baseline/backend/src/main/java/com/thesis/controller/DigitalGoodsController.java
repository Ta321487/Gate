package com.thesis.controller;

import com.thesis.capability.DigitalGoodsStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/digital")
public class DigitalGoodsController {

    private void requireOn() {
        if (!DigitalGoodsStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "未开启数字商品");
        }
    }

    @GetMapping("/mine")
    public R<?> mine(HttpSession session) {
        requireOn();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(DigitalGoodsStore.mine(uid));
    }

    @GetMapping("/codes")
    public R<?> codes(HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        return R.ok(DigitalGoodsStore.listCodes());
    }

    @PostMapping("/codes")
    public R<?> save(@RequestBody Map<String, Object> body, HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(DigitalGoodsStore.saveCode(body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
