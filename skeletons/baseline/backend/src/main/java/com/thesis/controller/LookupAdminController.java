package com.thesis.controller;

import com.thesis.capability.TicketLookupStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/** 领域主数据（楼栋/房间/类型等）：仅总管理员。 */
@RestController
@RequestMapping("/api/admin/lookups")
public class LookupAdminController {

    @GetMapping("/meta")
    public R<Map<String, Object>> meta(HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        return R.ok(TicketLookupStore.meta());
    }

    @GetMapping("/sites")
    public R<List<Map<String, Object>>> sites(HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        return R.ok(TicketLookupStore.listSitesAdmin());
    }

    @PostMapping("/sites")
    public R<Map<String, Object>> createSite(@RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            return R.ok(TicketLookupStore.createSite(
                    str(body.get("name")),
                    str(body.get("remark"))));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PutMapping("/sites/{id}")
    public R<Map<String, Object>> updateSite(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            return R.ok(TicketLookupStore.updateSite(id, str(body.get("name")), str(body.get("remark"))));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @DeleteMapping("/sites/{id}")
    public R<Void> deleteSite(@PathVariable long id, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            TicketLookupStore.deleteSite(id);
            return R.ok(null);
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/units")
    public R<List<Map<String, Object>>> units(
            @RequestParam(required = false) Long siteId,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        return R.ok(TicketLookupStore.listUnitsAdmin(siteId));
    }

    @PostMapping("/units")
    public R<Map<String, Object>> createUnit(@RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            return R.ok(TicketLookupStore.createUnit(
                    toLong(body.get("siteId")),
                    str(body.get("code")),
                    toInt(body.get("capacity"))));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PutMapping("/units/{id}")
    public R<Map<String, Object>> updateUnit(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            Long siteId = body.containsKey("siteId") ? toLong(body.get("siteId")) : null;
            return R.ok(TicketLookupStore.updateUnit(
                    id,
                    siteId,
                    str(body.get("code")),
                    toInt(body.get("capacity"))));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @DeleteMapping("/units/{id}")
    public R<Void> deleteUnit(@PathVariable long id, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            TicketLookupStore.deleteUnit(id);
            return R.ok(null);
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/types")
    public R<List<Map<String, Object>>> types(HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        return R.ok(TicketLookupStore.listTypesAdmin());
    }

    @PostMapping("/types")
    public R<Map<String, Object>> createType(@RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            return R.ok(TicketLookupStore.createType(str(body.get("name")), toInt(body.get("sortNo"))));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PutMapping("/types/{id}")
    public R<Map<String, Object>> updateType(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            return R.ok(TicketLookupStore.updateType(id, str(body.get("name")), toInt(body.get("sortNo"))));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @DeleteMapping("/types/{id}")
    public R<Void> deleteType(@PathVariable long id, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            TicketLookupStore.deleteType(id);
            return R.ok(null);
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o);
    }

    private static long toLong(Object o) {
        if (o == null) return 0L;
        if (o instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(String.valueOf(o));
        } catch (Exception e) {
            return 0L;
        }
    }

    private static Integer toInt(Object o) {
        if (o == null || "".equals(String.valueOf(o))) return null;
        if (o instanceof Number n) return n.intValue();
        try {
            return Integer.parseInt(String.valueOf(o));
        } catch (Exception e) {
            return null;
        }
    }
}
