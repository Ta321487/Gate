package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.BalanceLedgerStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/balance")
public class BalanceLedgerController {

    private static void requireLedger() {
        if (!BalanceLedgerStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通额度台账");
        }
    }

    @GetMapping("/mine")
    public R<Map<String, Object>> mine(HttpSession session) {
        requireLedger();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(BalanceLedgerStore.getAccount(uid));
    }

    @GetMapping("/ledger/mine")
    public R<Map<String, Object>> ledgerMine(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        requireLedger();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(BalanceLedgerStore.pageLedgerMine(uid, page, size));
    }

    @GetMapping("/accounts")
    public R<Map<String, Object>> accounts(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            HttpSession session) {
        requireLedger();
        AdminAuth.requireAdmin(session);
        return R.ok(BalanceLedgerStore.pageAccounts(page, size));
    }

    @GetMapping("/ledger")
    public R<Map<String, Object>> ledger(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String username,
            HttpSession session) {
        requireLedger();
        AdminAuth.requireAdmin(session);
        return R.ok(BalanceLedgerStore.pageLedgerAdmin(page, size, username));
    }

    @PostMapping("/credit")
    public R<Map<String, Object>> credit(@RequestBody Map<String, Object> body, HttpSession session) {
        requireLedger();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(BalanceLedgerStore.creditFromBody(body == null ? Map.of() : body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
