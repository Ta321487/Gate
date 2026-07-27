package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.VoteStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

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
            HttpSession session) {
        requireVote();
        String uid = AdminAuth.requireLogin(session);
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
            return R.ok(VoteStore.cast(uid, id, ids));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/campaigns/{id}/results")
    public R<List<Map<String, Object>>> results(@PathVariable long id, HttpSession session) {
        requireVote();
        AdminAuth.requireLogin(session);
        return R.ok(VoteStore.results(id));
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
        return R.ok(VoteStore.results(campaignId));
    }
}
