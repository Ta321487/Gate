package com.thesis.controller;

import com.thesis.capability.StaffRosterStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
public class StaffRosterController {

    /** 当日当班（登录用户可查；预约页弱展示）。 */
    @GetMapping("/api/staff-roster/on-duty")
    public R<List<Map<String, Object>>> onDuty(
            @RequestParam(required = false) String date,
            HttpSession session) {
        if (session.getAttribute("uid") == null) {
            throw new BizException(ErrorCode.UNAUTHORIZED, "请先登录");
        }
        if (!StaffRosterStore.enabled()) {
            return R.ok(List.of());
        }
        List<Map<String, Object>> rows = StaffRosterStore.onDuty(date);
        for (Map<String, Object> row : rows) {
            String un = row.get("username") == null ? "" : String.valueOf(row.get("username"));
            try {
                var p = com.thesis.service.UserStore.get(un);
                if (p != null && p.nickname != null && !p.nickname.isBlank()) {
                    row.put("nickname", p.nickname);
                } else {
                    row.put("nickname", un);
                }
            } catch (Exception e) {
                row.put("nickname", un);
            }
        }
        return R.ok(rows);
    }

    @GetMapping("/api/admin/staff-roster")
    public R<?> page(
            @RequestParam(required = false) String username,
            @RequestParam(required = false) String from,
            @RequestParam(required = false) String to,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            HttpSession session) {
        requireEnabled();
        AdminAuth.requireSuperAdmin(session);
        try {
            return R.ok(StaffRosterStore.page(username, from, to, page, size));
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/api/admin/staff-roster")
    public R<?> create(@RequestBody Map<String, Object> body, HttpSession session) {
        requireEnabled();
        AdminAuth.requireSuperAdmin(session);
        try {
            return R.ok(StaffRosterStore.create(
                    str(body.get("username")),
                    str(body.get("workDate")),
                    str(body.get("shiftLabel")),
                    str(body.get("note"))));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PutMapping("/api/admin/staff-roster/{id}")
    public R<?> update(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        requireEnabled();
        AdminAuth.requireSuperAdmin(session);
        try {
            return R.ok(StaffRosterStore.update(
                    id, str(body.get("shiftLabel")), str(body.get("note"))));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @DeleteMapping("/api/admin/staff-roster/{id}")
    public R<?> delete(@PathVariable long id, HttpSession session) {
        requireEnabled();
        AdminAuth.requireSuperAdmin(session);
        try {
            StaffRosterStore.delete(id);
            return R.ok(Map.of("ok", true));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    private static void requireEnabled() {
        if (!StaffRosterStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "排班功能暂不可用");
        }
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }
}
