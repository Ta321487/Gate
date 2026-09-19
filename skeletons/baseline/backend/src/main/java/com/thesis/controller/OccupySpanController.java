package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.OccupySpanStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/occupy")
public class OccupySpanController {

    private static void requireOccupy() {
        if (!OccupySpanStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通占用明细");
        }
    }

    @GetMapping("/mine")
    public R<Map<String, Object>> mine(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        requireOccupy();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(OccupySpanStore.pageMine(uid, page, size));
    }

    @GetMapping
    public R<Map<String, Object>> admin(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            HttpSession session) {
        requireOccupy();
        AdminAuth.requireAdmin(session);
        return R.ok(OccupySpanStore.pageAdmin(page, size));
    }
}
