package com.thesis.controller;

import com.thesis.capability.ParcelShelfStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
public class ParcelShelfController {

    @GetMapping("/api/admin/parcel-shelf")
    public R<?> list(HttpSession session) {
        requireEnabled();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(ParcelShelfStore.list());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/api/admin/parcel-shelf")
    public R<?> create(@RequestBody Map<String, Object> body, HttpSession session) {
        requireEnabled();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(ParcelShelfStore.create(str(body.get("code")), str(body.get("remark"))));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PutMapping("/api/admin/parcel-shelf/{id}")
    public R<?> update(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        requireEnabled();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(ParcelShelfStore.update(id, str(body.get("code")), str(body.get("remark"))));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @DeleteMapping("/api/admin/parcel-shelf/{id}")
    public R<?> delete(@PathVariable long id, HttpSession session) {
        requireEnabled();
        AdminAuth.requireAdmin(session);
        try {
            ParcelShelfStore.delete(id);
            return R.ok(null);
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    private static void requireEnabled() {
        if (!ParcelShelfStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "货架管理暂不可用");
        }
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }
}
