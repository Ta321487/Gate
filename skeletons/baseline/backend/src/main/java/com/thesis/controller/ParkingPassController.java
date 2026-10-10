package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.ParkingPassStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/parking-passes")
public class ParkingPassController {

    private static void requireReady() {
        if (!ParkingPassStore.ready()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "停车次卡功能暂不可用");
        }
    }

    @GetMapping
    public R<?> listMine(HttpSession session) {
        requireReady();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(ParkingPassStore.listMine(uid));
    }

    @GetMapping("/remain")
    public R<?> remain(HttpSession session) {
        requireReady();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(Map.of("remain", ParkingPassStore.totalRemain(uid)));
    }

    @GetMapping("/admin")
    public R<?> listAdmin(HttpSession session) {
        requireReady();
        AdminAuth.requireAdmin(session);
        return R.ok(ParkingPassStore.listAll(100));
    }

    @PostMapping("/grant")
    public R<?> grant(@RequestBody Map<String, Object> body, HttpSession session) {
        requireReady();
        AdminAuth.requireAdmin(session);
        try {
            String user = String.valueOf(body.getOrDefault("username", "")).trim();
            String pack = String.valueOf(body.getOrDefault("packName", "包月次卡"));
            int count = 0;
            Object c = body.get("remainCount");
            if (c == null) c = body.get("count");
            if (c != null && !String.valueOf(c).isBlank()) {
                count = Integer.parseInt(String.valueOf(c));
            }
            long id = ParkingPassStore.grant(user, pack, count);
            return R.ok(Map.of("id", id));
        } catch (NumberFormatException e) {
            // 须写在 IllegalArgumentException 前：NFE 是其子类，后捕会被判「已捕获」
            throw new BizException(ErrorCode.BAD_REQUEST, "次数格式不正确");
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
