package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.GradeScoreStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/grade-scores")
public class GradeScoreController {

    private static void requireOn() {
        if (!GradeScoreStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通成绩登记");
        }
    }

    @GetMapping("/meta")
    public R<Map<String, Object>> meta(HttpSession session) {
        requireOn();
        AdminAuth.requireLogin(session);
        return R.ok(GradeScoreStore.meta());
    }

    @GetMapping("/mine")
    public R<List<Map<String, Object>>> mine(HttpSession session) {
        requireOn();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(GradeScoreStore.listMine(uid));
    }

    @GetMapping("/admin")
    public R<List<Map<String, Object>>> admin(
            @RequestParam(required = false) Long courseId,
            @RequestParam(required = false) Long termId,
            HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        return R.ok(GradeScoreStore.listAdmin(courseId, termId));
    }

    @PostMapping("/admin")
    public R<Map<String, Object>> save(@RequestBody Map<String, Object> body, HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        if (body == null) body = Map.of();
        String username = body.get("username") == null ? "" : String.valueOf(body.get("username"));
        long courseId = Long.parseLong(String.valueOf(body.getOrDefault("courseId", "0")));
        long termId = Long.parseLong(String.valueOf(body.getOrDefault("termId", "0")));
        Object raw = body.get("score");
        if (raw == null || String.valueOf(raw).isBlank()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "请填写分数");
        }
        BigDecimal score;
        try {
            score = new BigDecimal(String.valueOf(raw).trim());
        } catch (NumberFormatException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, "分数格式不正确");
        }
        try {
            return R.ok(GradeScoreStore.save(username, courseId, termId, score));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @DeleteMapping("/admin/{id}")
    public R<Void> delete(@PathVariable long id, HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        try {
            GradeScoreStore.delete(id);
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        }
        return R.ok(null);
    }
}
