package com.thesis.controller;

import com.thesis.capability.RecommendStore;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/** 轻量猜你喜欢：GET /api/recommend */
@RestController
@RequestMapping("/api/recommend")
public class RecommendController {

    @GetMapping
    public R<Map<String, Object>> recommend(
            @RequestParam(defaultValue = "6") int limit,
            HttpSession session) {
        Object uid = session.getAttribute("uid");
        String username = uid == null ? null : uid.toString();
        return R.ok(RecommendStore.recommend(username, limit));
    }
}
