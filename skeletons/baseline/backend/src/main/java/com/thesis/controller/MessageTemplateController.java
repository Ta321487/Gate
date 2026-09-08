package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.MessageStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/admin/message-templates")
public class MessageTemplateController {

    @GetMapping
    public R<?> page(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            HttpSession session) {
        if (!MessageStore.templateEnabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "消息模板功能暂不可用");
        }
        AdminAuth.requireSuperAdmin(session);
        try {
            return R.ok(MessageStore.pageTemplates(page, size));
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PutMapping("/{id}")
    public R<?> update(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        if (!MessageStore.templateEnabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "消息模板功能暂不可用");
        }
        AdminAuth.requireSuperAdmin(session);
        try {
            String title = body.get("title") == null ? null : String.valueOf(body.get("title"));
            String text = body.get("body") == null ? null : String.valueOf(body.get("body"));
            Boolean enabled = null;
            if (body.get("enabled") != null) {
                enabled = Boolean.parseBoolean(String.valueOf(body.get("enabled")));
            }
            return R.ok(MessageStore.updateTemplate(id, title, text, enabled));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
