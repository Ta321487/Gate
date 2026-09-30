package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.FundPublicityStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * 资助公示旁路岛：管理端登记/结束，用户端查阅本人申请的公示。
 * 挂在申请单之后，不改 ticket 状态机。
 */
@RestController
@RequestMapping("/api/fund-publicity")
public class FundPublicityController {

    private static void requireOn() {
        if (!FundPublicityStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通资助公示");
        }
    }

    private static String asStr(Object v) {
        return v == null ? "" : String.valueOf(v).trim();
    }

    private static long asLong(Object v) {
        String s = asStr(v);
        if (s.isEmpty()) return 0L;
        try {
            return Long.parseLong(s);
        } catch (NumberFormatException e) {
            return 0L;
        }
    }

    /** 用户端：本人申请的公示。 */
    @GetMapping("/mine")
    public R<List<Map<String, Object>>> mine(HttpSession session) {
        requireOn();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(FundPublicityStore.listMine(uid));
    }

    @GetMapping("/admin")
    public R<List<Map<String, Object>>> admin(HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        return R.ok(FundPublicityStore.listAdmin());
    }

    @PostMapping("/admin")
    public R<Map<String, Object>> save(@RequestBody Map<String, Object> body, HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        String operator = AdminAuth.requireLogin(session);
        if (body == null) body = Map.of();
        try {
            return R.ok(FundPublicityStore.save(
                    asLong(body.get("ticketId")),
                    asStr(body.get("title")),
                    asStr(body.get("startAt")),
                    asStr(body.get("endAt")),
                    operator));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 用户端：对本人公示登记异议（窗口内可写，超期/未开拒绝）。 */
    @PostMapping("/{id}/objection")
    public R<Map<String, Object>> objection(
            @PathVariable long id,
            @RequestBody(required = false) Map<String, Object> body,
            HttpSession session) {
        requireOn();
        String uid = AdminAuth.requireLogin(session);
        Map<String, Object> in = body == null ? Map.of() : body;
        try {
            return R.ok(FundPublicityStore.submitObjection(id, uid, asStr(in.get("note"))));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 结束公示。 */
    @PostMapping("/admin/{id}/close")
    public R<Void> close(@PathVariable long id, HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        String operator = AdminAuth.requireLogin(session);
        try {
            FundPublicityStore.close(id, operator);
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        }
        return R.ok(null);
    }

    @DeleteMapping("/admin/{id}")
    public R<Void> remove(@PathVariable long id, HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        try {
            FundPublicityStore.remove(id);
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        }
        return R.ok(null);
    }
}
