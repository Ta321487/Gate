package com.thesis.controller;

import com.thesis.capability.ArchiveLogStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.Map;

@RestController
@RequestMapping("/api/archive-logs")
public class ArchiveLogController {

    private static void require() {
        if (!ArchiveLogStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "监测记录暂不可用");
        }
    }

    @GetMapping
    public R<?> pageByItem(
            @RequestParam long itemId,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        require();
        AdminAuth.requireLogin(session);
        return R.ok(ArchiveLogStore.pageByItem(itemId, page, size));
    }

    @PostMapping
    public R<?> submit(@RequestBody Map<String, Object> body, HttpSession session) {
        require();
        String uid = AdminAuth.requireLogin(session);
        long itemId = toLong(body.get("itemId"));
        String logType = str(body.get("logType"));
        LocalDate logDate = parseDay(body.get("logDate"));
        @SuppressWarnings("unchecked")
        Map<String, Object> payload =
                body.get("payload") instanceof Map<?, ?> m
                        ? (Map<String, Object>) m
                        : Map.of();
        boolean abnormal = Boolean.TRUE.equals(body.get("abnormal"))
                || "1".equals(String.valueOf(body.get("abnormal")));
        String remark = str(body.get("remark"));
        try {
            return R.ok(ArchiveLogStore.submit(uid, itemId, logType, logDate, payload, abnormal, remark));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    private static long toLong(Object v) {
        if (v instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(String.valueOf(v));
        } catch (Exception e) {
            return 0L;
        }
    }

    private static String str(Object v) {
        return v == null ? "" : String.valueOf(v).trim();
    }

    private static LocalDate parseDay(Object v) {
        if (v == null || String.valueOf(v).isBlank()) return LocalDate.now();
        try {
            return LocalDate.parse(String.valueOf(v).trim().substring(0, 10));
        } catch (Exception e) {
            return LocalDate.now();
        }
    }
}
