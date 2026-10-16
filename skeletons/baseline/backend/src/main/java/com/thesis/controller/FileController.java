package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.config.AppPolicy;
import com.thesis.config.UploadStorage;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/** 已上传文件列表。开题写到文件管理才挂菜单。 */
@RestController
public class FileController {

    @GetMapping("/api/admin/uploads")
    public R<List<Map<String, Object>>> uploads(HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        return R.ok(UploadStorage.listFiles());
    }

    @DeleteMapping("/api/admin/uploads")
    public R<Void> deleteUpload(
            @RequestParam String name,
            @RequestParam(required = false) String confirm,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        if (AppPolicy.SENSITIVE_CONFIRM) {
            boolean ok = "true".equalsIgnoreCase(String.valueOf(confirm));
            if (!ok) throw new BizException(ErrorCode.BAD_REQUEST, "请再次确认后再删除");
        }
        if (!UploadStorage.deleteFile(name)) {
            throw new BizException(ErrorCode.NOT_FOUND, "文件不存在");
        }
        return R.ok(null);
    }
}
