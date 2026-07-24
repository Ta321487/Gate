package com.thesis.controller;

import com.thesis.capability.ArchiveLogStore;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.Map;

@RestController
@RequestMapping("/api/admin/archive-logs")
public class AdminArchiveLogController {

    private static void require() {
        if (!ArchiveLogStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "监测记录暂不可用");
        }
    }

    private static void requireAdmin(HttpSession session) {
        if (!"admin".equals(String.valueOf(session.getAttribute("role")))) {
            throw new BizException(ErrorCode.FORBIDDEN, "需要管理员权限");
        }
    }

    @GetMapping
    public R<?> page(
            @RequestParam(required = false) Long itemId,
            @RequestParam(required = false) String logType,
            @RequestParam(required = false) String logDate,
            @RequestParam(required = false) Boolean abnormalOnly,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        require();
        requireAdmin(session);
        LocalDate day = null;
        if (logDate != null && !logDate.isBlank()) {
            try {
                day = LocalDate.parse(logDate.trim().substring(0, 10));
            } catch (Exception ignored) {
            }
        }
        return R.ok(ArchiveLogStore.pageAdmin(itemId, logType, day, abnormalOnly, page, size));
    }

    @GetMapping("/missing-today")
    public R<?> missingToday(
            @RequestParam(defaultValue = "checkin") String logType,
            HttpSession session) {
        require();
        requireAdmin(session);
        return R.ok(Map.of(
                "list", ArchiveLogStore.missingToday(logType),
                "total", ArchiveLogStore.countMissingToday(logType),
                "logType", logType));
    }
}
