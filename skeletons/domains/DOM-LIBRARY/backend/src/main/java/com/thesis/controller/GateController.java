package com.thesis.controller;

import com.thesis.capability.TicketStore;
import com.thesis.common.R;
import com.thesis.service.LibraryStore;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

/** 工厂门禁探测：主路径自检 */
@RestController
@RequestMapping("/api/gate")
public class GateController {

    @GetMapping("/library-main-path")
    public R<Map<String, Object>> libraryMainPath() {
        boolean ok = LibraryStore.runMainPathSelfCheck();
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("ok", ok);
        m.put("flow", "申请借阅 → 审核 → 归还");
        m.put("message", ok ? "主路径通过" : "主路径未通过");
        return R.ok(m);
    }

    @GetMapping("/ticket-main-path")
    public R<Map<String, Object>> ticketMainPath() {
        boolean ok = TicketStore.runMainPathSelfCheck();
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("ok", ok);
        m.put("mode", TicketStore.mode().name().toLowerCase());
        m.put("flow", "申请借阅 → 审核 → 归还");
        m.put("message", ok ? "主路径通过" : "主路径未通过");
        return R.ok(m);
    }
}
