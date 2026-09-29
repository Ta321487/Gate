package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.StockIoStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/stock-io")
public class StockIoController {

    private static void requireIo() {
        if (!StockIoStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通入出库功能");
        }
    }

    @GetMapping("/moves")
    public R<Map<String, Object>> moves(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String moveType,
            HttpSession session) {
        requireIo();
        AdminAuth.requireAdmin(session);
        return R.ok(StockIoStore.pageMoves(page, size, moveType));
    }

    @PostMapping("/moves")
    public R<Map<String, Object>> post(@RequestBody Map<String, Object> body, HttpSession session) {
        requireIo();
        AdminAuth.requireAdmin(session);
        try {
            String uid = AdminAuth.requireLogin(session);
            return R.ok(StockIoStore.postFromBody(body == null ? Map.of() : body, uid));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/scrap-requests")
    public R<Map<String, Object>> scrapRequests(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String status,
            HttpSession session) {
        requireIo();
        AdminAuth.requireAdmin(session);
        if (!StockIoStore.scrapApproveFlow()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通报废审批");
        }
        return R.ok(StockIoStore.pageScrapRequests(page, size, status));
    }

    @PostMapping("/scrap-requests/{id}/approve")
    public R<Map<String, Object>> approveScrap(
            @PathVariable long id,
            @RequestBody(required = false) Map<String, Object> body,
            HttpSession session) {
        requireIo();
        AdminAuth.requireAdmin(session);
        try {
            String uid = AdminAuth.requireLogin(session);
            String note = body == null || body.get("remark") == null
                    ? ""
                    : String.valueOf(body.get("remark")).trim();
            return R.ok(StockIoStore.approveScrapRequest(id, uid, note));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/scrap-requests/{id}/reject")
    public R<Map<String, Object>> rejectScrap(
            @PathVariable long id,
            @RequestBody(required = false) Map<String, Object> body,
            HttpSession session) {
        requireIo();
        AdminAuth.requireAdmin(session);
        try {
            String uid = AdminAuth.requireLogin(session);
            String note = body == null || body.get("remark") == null
                    ? ""
                    : String.valueOf(body.get("remark")).trim();
            return R.ok(StockIoStore.rejectScrapRequest(id, uid, note));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
