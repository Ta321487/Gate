package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.TimebankStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/timebank")
public class TimebankController {

    private static void requireTb() {
        if (!TimebankStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通时间银行功能");
        }
    }

    @GetMapping("/account")
    public R<Map<String, Object>> account(HttpSession session) {
        requireTb();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(TimebankStore.getAccount(uid));
    }

    @GetMapping("/ledger/mine")
    public R<Map<String, Object>> ledgerMine(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        requireTb();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(TimebankStore.pageLedgerMine(uid, page, size));
    }

    @GetMapping("/services")
    public R<List<Map<String, Object>>> services(HttpSession session) {
        requireTb();
        AdminAuth.requireLogin(session);
        return R.ok(TimebankStore.listOpenServices());
    }

    /** 用户自助存入（选服务事项 + 小时数，演示即时入账）。 */
    @PostMapping("/earn")
    public R<Map<String, Object>> earn(@RequestBody Map<String, Object> body, HttpSession session) {
        requireTb();
        String uid = AdminAuth.requireLogin(session);
        try {
            boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
            return R.ok(TimebankStore.creditFromBody(uid, body == null ? Map.of() : body, admin));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/admin/accounts")
    public R<Map<String, Object>> adminAccounts(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            HttpSession session) {
        requireTb();
        AdminAuth.requireAdmin(session);
        return R.ok(TimebankStore.pageAccounts(page, size));
    }

    @GetMapping("/admin/ledger")
    public R<Map<String, Object>> adminLedger(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String username,
            HttpSession session) {
        requireTb();
        AdminAuth.requireAdmin(session);
        return R.ok(TimebankStore.pageLedgerAdmin(page, size, username));
    }

    @PostMapping("/admin/earn")
    public R<Map<String, Object>> adminEarn(@RequestBody Map<String, Object> body, HttpSession session) {
        requireTb();
        AdminAuth.requireAdmin(session);
        try {
            String uid = AdminAuth.requireLogin(session);
            return R.ok(TimebankStore.creditFromBody(uid, body == null ? Map.of() : body, true));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
