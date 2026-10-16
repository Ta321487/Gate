package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.R;
import com.thesis.service.CommissionStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
public class CommissionController {

    @GetMapping("/api/admin/commissions")
    public R<List<Map<String, Object>>> list(HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        return R.ok(CommissionStore.list());
    }
}
