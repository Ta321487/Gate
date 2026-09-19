package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.MaterialCheckStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/material")
public class MaterialCheckController {

    private static void requireMaterial() {
        if (!MaterialCheckStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通材料清单");
        }
    }

    @GetMapping("/checklist")
    public R<List<Map<String, Object>>> checklist(HttpSession session) {
        requireMaterial();
        AdminAuth.requireLogin(session);
        return R.ok(MaterialCheckStore.listOpen());
    }

    @PostMapping("/checklist")
    public R<Map<String, Object>> add(@RequestBody Map<String, Object> body, HttpSession session) {
        requireMaterial();
        AdminAuth.requireSuperAdmin(session);
        String title = body == null || body.get("title") == null ? "" : String.valueOf(body.get("title"));
        boolean required = true;
        if (body != null && body.get("required") instanceof Boolean b) required = b;
        try {
            long id = MaterialCheckStore.addItem(title, required);
            return R.ok(Map.of("id", id));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
