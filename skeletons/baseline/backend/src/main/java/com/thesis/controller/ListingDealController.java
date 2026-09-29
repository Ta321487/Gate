package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.ListingDealStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

/**
 * 房源成交台账旁路岛：管理端登记成交与查看台账/总额。
 * 只记成交事实，不接管交易与支付。
 */
@RestController
@RequestMapping("/api/listing-deal")
public class ListingDealController {

    private static void requireOn() {
        if (!ListingDealStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通成交登记");
        }
    }

    private static String asStr(Object v) {
        return v == null ? "" : String.valueOf(v).trim();
    }

    private static long asLong(Object v) {
        String s = asStr(v);
        if (s.isEmpty()) return 0L;
        try {
            return Long.parseLong(s);
        } catch (NumberFormatException e) {
            return 0L;
        }
    }

    private static BigDecimal asMoney(Object v) {
        String s = asStr(v);
        if (s.isEmpty()) return null;
        try {
            return new BigDecimal(s);
        } catch (NumberFormatException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, "成交价格式不正确：" + s);
        }
    }

    @GetMapping("/admin")
    public R<List<Map<String, Object>>> admin(HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        return R.ok(ListingDealStore.listAdmin());
    }

    /** 成交总额。 */
    @GetMapping("/admin/total")
    public R<String> total(HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        return R.ok(ListingDealStore.total());
    }

    @PostMapping("/admin")
    public R<Map<String, Object>> save(@RequestBody Map<String, Object> body, HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        String operator = AdminAuth.requireLogin(session);
        if (body == null) body = Map.of();
        try {
            return R.ok(ListingDealStore.save(
                    asLong(body.get("ticketId")),
                    asMoney(body.get("dealPrice")),
                    asStr(body.get("dealAt")),
                    operator,
                    asStr(body.get("remark"))));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @DeleteMapping("/admin/{id}")
    public R<Void> remove(@PathVariable long id, HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        try {
            ListingDealStore.remove(id);
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        }
        return R.ok(null);
    }
}
