package com.thesis.controller;

import com.thesis.capability.ShootStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/shoot")
public class ShootController {

    private static void require() {
        if (!ShootStore.enabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "约拍未开启");
        }
    }

    private static String username(HttpSession session) {
        AdminAuth.requireLogin(session);
        Object user = session.getAttribute("username");
        return user == null ? "" : String.valueOf(user);
    }

    @GetMapping("/photographers")
    public R<?> photographers(HttpSession session) {
        require();
        AdminAuth.requireLogin(session);
        return R.ok(ShootStore.photographers());
    }

    @GetMapping("/bundles")
    public R<?> bundles(HttpSession session) {
        require();
        AdminAuth.requireLogin(session);
        return R.ok(ShootStore.bundles(true));
    }

    @GetMapping("/bundles/all")
    public R<?> allBundles(HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        return R.ok(ShootStore.bundles(false));
    }

    @PostMapping("/bundles")
    public R<?> saveBundle(@RequestBody Map<String, Object> body, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        return R.ok(ShootStore.saveBundle(body));
    }

    @GetMapping("/mine")
    public R<?> mine(HttpSession session) {
        require();
        return R.ok(ShootStore.mine(username(session)));
    }

    @GetMapping("/files")
    public R<?> files(HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        return R.ok(ShootStore.files());
    }

    @PostMapping("/files")
    public R<?> saveFile(@RequestBody Map<String, Object> body, HttpSession session) {
        require();
        AdminAuth.requireAdmin(session);
        return R.ok(ShootStore.saveFile(body));
    }
}
