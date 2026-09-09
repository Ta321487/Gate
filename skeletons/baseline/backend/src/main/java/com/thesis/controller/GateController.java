package com.thesis.controller;

import com.thesis.capability.TicketStore;
import com.thesis.common.R;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

/** 业务主路径自检（开发/演示用） */
@RestController
@RequestMapping("/api/gate")
public class GateController {

    @GetMapping("/ticket-main-path")
    public R<Map<String, Object>> ticketMainPath() {
        boolean ok = TicketStore.runMainPathSelfCheck();
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("ok", ok);
        m.put("mode", TicketStore.mode().name().toLowerCase());
        m.put("flow", TicketStore.mode() == TicketStore.Mode.STANDALONE
                ? "提交报修 → 受理 → 完成"
                : "申请 → 审核 → 完结");
        m.put("message", ok ? "主路径通过" : "主路径未通过");
        return R.ok(m);
    }
}
