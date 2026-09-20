package com.thesis.controller;

import com.thesis.capability.BuybackStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.Map;

@RestController
@RequestMapping("/api/buybacks")
public class BuybackController {

    private static void require() {
        if (!BuybackStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "回收未开启");
        }
    }

    private static String username(HttpSession session) {
        return AdminAuth.requireLogin(session);
    }

    @GetMapping("/slots")
    public R<?> slots(HttpSession session) {
        require();
        username(session);
        return R.ok(BuybackStore.slots(true));
    }

    @GetMapping("/slots/all")
    public R<?> allSlots(HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        return R.ok(BuybackStore.slots(false));
    }

    @PostMapping("/slots")
    public R<?> saveSlot(@RequestBody Map<String, Object> body, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(BuybackStore.saveSlot(body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/mine")
    public R<?> mine(HttpSession session) {
        require();
        return R.ok(BuybackStore.mine(username(session)));
    }

    @PostMapping
    public R<?> submit(@RequestBody Map<String, Object> body, HttpSession session) {
        require();
        try {
            return R.ok(BuybackStore.submit(username(session), body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{id}/decide")
    public R<?> decide(@PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        require();
        boolean agree = body != null && Boolean.TRUE.equals(body.get("agree"));
        if (body != null && body.get("agree") instanceof Number n) agree = n.intValue() == 1;
        try {
            return R.ok(BuybackStore.decide(id, username(session), agree));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping
    public R<?> all(HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        return R.ok(BuybackStore.all());
    }

    @PostMapping("/{id}/quote")
    public R<?> quote(@PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        BigDecimal price = BigDecimal.ZERO;
        try {
            if (body != null && body.get("quoteYuan") != null) {
                price = new BigDecimal(String.valueOf(body.get("quoteYuan")));
            }
            return R.ok(BuybackStore.quote(id, price));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{id}/pick")
    public R<?> pick(@PathVariable long id, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(BuybackStore.pick(id));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{id}/stock")
    public R<?> stock(@PathVariable long id, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(BuybackStore.stock(id));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{id}/list")
    public R<?> list(@PathVariable long id, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(BuybackStore.listOn(id));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
