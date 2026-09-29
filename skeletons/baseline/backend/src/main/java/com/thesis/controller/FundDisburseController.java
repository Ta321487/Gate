package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.FundDisburseStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

/**
 * 资助发放台账旁路岛：管理端登记发放与查看台账/合计。
 * 只记发放事实，不做额度扣减（额度台账是 balance_ledger）。
 */
@RestController
@RequestMapping("/api/fund-disburse")
public class FundDisburseController {

    private static void requireOn() {
        if (!FundDisburseStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通发放登记");
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
            throw new BizException(ErrorCode.BAD_REQUEST, "金额格式不正确：" + s);
        }
    }

    @GetMapping("/admin")
    public R<List<Map<String, Object>>> admin(HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        return R.ok(FundDisburseStore.listAdmin());
    }

    /** 某申请单已发放合计。 */
    @GetMapping("/admin/total")
    public R<String> total(@RequestParam long ticketId, HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        return R.ok(FundDisburseStore.totalOf(ticketId));
    }

    @PostMapping("/admin")
    public R<Map<String, Object>> save(@RequestBody Map<String, Object> body, HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        String operator = AdminAuth.requireLogin(session);
        if (body == null) body = Map.of();
        try {
            return R.ok(FundDisburseStore.save(
                    asLong(body.get("ticketId")),
                    asMoney(body.get("amount")),
                    asStr(body.get("paidAt")),
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
            FundDisburseStore.remove(id);
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        }
        return R.ok(null);
    }
}
