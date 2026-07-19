package com.thesis.controller;

import com.thesis.capability.TicketLookupStore;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/** standalone 报修：楼栋 / 房间 / 类型下拉。 */
@RestController
@RequestMapping("/api/lookups")
public class LookupController {

    @GetMapping("/meta")
    public R<Map<String, Object>> meta(HttpSession session) {
        requireLogin(session);
        return R.ok(TicketLookupStore.meta());
    }

    @GetMapping("/sites")
    public R<List<Map<String, Object>>> sites(HttpSession session) {
        requireLogin(session);
        return R.ok(TicketLookupStore.listSites());
    }

    @GetMapping("/units")
    public R<List<Map<String, Object>>> units(
            @RequestParam(required = false) Long siteId,
            HttpSession session) {
        requireLogin(session);
        return R.ok(TicketLookupStore.listUnits(siteId));
    }

    @GetMapping("/types")
    public R<List<Map<String, Object>>> types(HttpSession session) {
        requireLogin(session);
        return R.ok(TicketLookupStore.listTypes());
    }

    private static void requireLogin(HttpSession session) {
        if (session.getAttribute("uid") == null) {
            throw new BizException(ErrorCode.UNAUTHORIZED, "未登录");
        }
    }
}
