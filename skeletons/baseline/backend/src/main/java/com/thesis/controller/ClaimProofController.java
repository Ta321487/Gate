package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.ClaimProofStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/lost/proof")
public class ClaimProofController {

    private static void requireProof() {
        if (!ClaimProofStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通认领凭证核验");
        }
    }

    @GetMapping
    public R<List<Map<String, Object>>> list(@RequestParam long claimId, HttpSession session) {
        requireProof();
        AdminAuth.requireLogin(session);
        return R.ok(ClaimProofStore.listByClaim(claimId));
    }

    @PostMapping
    public R<Map<String, Object>> submit(@RequestBody Map<String, Object> body, HttpSession session) {
        requireProof();
        String user = AdminAuth.requireLogin(session);
        long claimId = 0L;
        if (body != null && body.get("claimId") instanceof Number n) claimId = n.longValue();
        else if (body != null && body.get("claimId") != null) {
            try {
                claimId = Long.parseLong(String.valueOf(body.get("claimId")).trim());
            } catch (Exception ignored) {
                claimId = 0L;
            }
        }
        String type = body == null || body.get("proofType") == null ? "" : String.valueOf(body.get("proofType"));
        String content = body == null || body.get("proofContent") == null ? "" : String.valueOf(body.get("proofContent"));
        try {
            long id = ClaimProofStore.submit(claimId, type, content, user);
            return R.ok(Map.of("id", id));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{id}/verify")
    public R<Map<String, Object>> verify(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        requireProof();
        AdminAuth.requireAdmin(session);
        String op = AdminAuth.requireLogin(session);
        boolean pass = true;
        if (body != null && body.get("pass") instanceof Boolean b) pass = b;
        try {
            return R.ok(ClaimProofStore.verify(id, pass, op));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
