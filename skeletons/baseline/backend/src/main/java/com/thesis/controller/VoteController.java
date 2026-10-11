package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.VoteStore;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/vote")
public class VoteController {

    private static void requireVote() {
        if (!VoteStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通投票功能");
        }
    }

    private static String clientIp(HttpServletRequest request) {
        if (request == null) return "";
        String xff = request.getHeader("X-Forwarded-For");
        if (xff != null && !xff.isBlank()) {
            return xff.split(",")[0].trim();
        }
        String real = request.getHeader("X-Real-IP");
        if (real != null && !real.isBlank()) return real.trim();
        return request.getRemoteAddr() == null ? "" : request.getRemoteAddr();
    }

    @GetMapping("/campaigns")
    public R<List<Map<String, Object>>> campaigns(HttpSession session) {
        requireVote();
        AdminAuth.requireLogin(session);
        return R.ok(VoteStore.listOpenCampaigns());
    }

    @GetMapping("/campaigns/{id}")
    public R<Map<String, Object>> campaign(@PathVariable long id, HttpSession session) {
        requireVote();
        AdminAuth.requireLogin(session);
        Map<String, Object> c = VoteStore.getCampaign(id);
        if (c == null) throw new BizException(ErrorCode.NOT_FOUND, "评选不存在");
        return R.ok(c);
    }

    @GetMapping("/campaigns/{id}/candidates")
    public R<List<Map<String, Object>>> candidates(@PathVariable long id, HttpSession session) {
        requireVote();
        AdminAuth.requireLogin(session);
        return R.ok(VoteStore.listCandidates(id));
    }

    @PostMapping("/campaigns/{id}/cast")
    public R<Map<String, Object>> cast(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request,
            HttpSession session) {
        requireVote();
        String uid = AdminAuth.requireLogin(session);
        boolean abstain = body != null && (
                Boolean.TRUE.equals(body.get("abstain"))
                        || "true".equalsIgnoreCase(String.valueOf(body.get("abstain"))));
        List<Long> ids = new ArrayList<>();
        Object raw = body == null ? null : body.get("candidateIds");
        if (raw instanceof List<?> list) {
            for (Object o : list) {
                if (o != null && !String.valueOf(o).isBlank()) {
                    ids.add(Long.parseLong(String.valueOf(o)));
                }
            }
        } else if (body != null && body.get("candidateId") != null) {
            ids.add(Long.parseLong(String.valueOf(body.get("candidateId"))));
        }
        try {
            return R.ok(VoteStore.cast(uid, id, ids, abstain, clientIp(request)));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/campaigns/{id}/results")
    public R<List<Map<String, Object>>> results(@PathVariable long id, HttpSession session) {
        requireVote();
        AdminAuth.requireLogin(session);
        try {
            return R.ok(VoteStore.results(id, false));
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/ballots/mine")
    public R<Map<String, Object>> mine(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        requireVote();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(VoteStore.pageMine(uid, page, size));
    }

    @GetMapping("/admin/campaigns/{campaignId}/candidates")
    public R<Map<String, Object>> adminCandidates(
            @PathVariable long campaignId,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            HttpSession session) {
        requireVote();
        AdminAuth.requireAdmin(session);
        return R.ok(VoteStore.pageCandidatesAdmin(campaignId, page, size));
    }

    @PostMapping("/admin/candidates")
    public R<Map<String, Object>> createCandidate(@RequestBody Map<String, Object> body, HttpSession session) {
        requireVote();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(VoteStore.createCandidate(body == null ? Map.of() : body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @DeleteMapping("/admin/candidates/{id}")
    public R<Void> deleteCandidate(@PathVariable long id, HttpSession session) {
        requireVote();
        AdminAuth.requireAdmin(session);
        try {
            if (!VoteStore.deleteCandidate(id)) {
                throw new BizException(ErrorCode.NOT_FOUND, "候选人不存在");
            }
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
        return R.ok(null);
    }

    @GetMapping("/admin/campaigns/{campaignId}/ballots")
    public R<Map<String, Object>> adminBallots(
            @PathVariable long campaignId,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        requireVote();
        AdminAuth.requireAdmin(session);
        return R.ok(VoteStore.pageBallotsAdmin(campaignId, page, size));
    }

    @GetMapping("/admin/campaigns/{campaignId}/results")
    public R<List<Map<String, Object>>> adminResults(@PathVariable long campaignId, HttpSession session) {
        requireVote();
        AdminAuth.requireAdmin(session);
        return R.ok(VoteStore.results(campaignId, true));
    }

    @PutMapping("/admin/campaigns/{campaignId}/settings")
    public R<Map<String, Object>> updateSettings(
            @PathVariable long campaignId,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        requireVote();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(VoteStore.updateCampaignSettings(campaignId, body == null ? Map.of() : body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/admin/campaigns/{campaignId}/export")
    public void exportResults(
            @PathVariable long campaignId,
            HttpSession session,
            HttpServletResponse response) {
        requireVote();
        AdminAuth.requireAdmin(session);
        try {
            String csv = VoteStore.exportResultsCsv(campaignId);
            response.setCharacterEncoding(StandardCharsets.UTF_8.name());
            response.setContentType("text/csv;charset=UTF-8");
            response.setHeader("Content-Disposition", "attachment; filename=vote_results.csv");
            response.getOutputStream().write(new byte[] {(byte) 0xEF, (byte) 0xBB, (byte) 0xBF});
            response.getOutputStream().write(csv.getBytes(StandardCharsets.UTF_8));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (Exception e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
