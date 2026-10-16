package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.HelpStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
public class HelpController {

    @GetMapping("/api/help")
    public R<Map<String, Object>> get() {
        return R.ok(HelpStore.get());
    }

    @PutMapping("/api/admin/help")
    public R<Map<String, Object>> save(@RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        String title = body == null || body.get("title") == null ? "" : String.valueOf(body.get("title"));
        String text = body == null || body.get("body") == null ? "" : String.valueOf(body.get("body"));
        try {
            return R.ok(HelpStore.save(title, text));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
