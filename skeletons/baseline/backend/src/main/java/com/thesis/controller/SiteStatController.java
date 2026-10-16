package com.thesis.controller;

import com.thesis.common.R;
import com.thesis.service.SiteStatStore;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 门户浏览计数（同标签页计一次；工作台读取汇总）。
 */
@RestController
@RequestMapping("/api/site-stat")
public class SiteStatController {

    @PostMapping("/pv")
    public R<Map<String, Object>> bumpPv() {
        SiteStatStore.bumpPv();
        return R.ok(SiteStatStore.snapshot());
    }
}
