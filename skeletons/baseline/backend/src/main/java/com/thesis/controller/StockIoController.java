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
}
