package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.PatientProfileStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/patient-profiles")
public class PatientProfileController {

    private static void requireReady() {
        if (!PatientProfileStore.ready()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "就诊人功能暂不可用");
        }
    }

    @GetMapping
    public R<?> list(HttpSession session) {
        requireReady();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(PatientProfileStore.listMine(uid));
    }

    @PostMapping
    public R<?> add(@RequestBody Map<String, Object> body, HttpSession session) {
        requireReady();
        String uid = AdminAuth.requireLogin(session);
        try {
            long id = PatientProfileStore.add(
                    uid,
                    String.valueOf(body.getOrDefault("patientName", "")),
                    String.valueOf(body.getOrDefault("relationLabel", "本人")),
                    String.valueOf(body.getOrDefault("idHint", "")));
            return R.ok(Map.of("id", id));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{id}/delete")
    public R<?> delete(@PathVariable long id, HttpSession session) {
        requireReady();
        String uid = AdminAuth.requireLogin(session);
        PatientProfileStore.remove(id, uid);
        return R.ok(Map.of("ok", true));
    }
}
