package com.thesis.controller;

import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.*;
import java.util.*;

@RestController
@RequestMapping("/api")
public class CommonController {

    @Value("${thesis.title:毕设系统}")
    private String title;

    @Value("${thesis.register-role:user}")
    private String registerRole;

    @GetMapping("/meta")
    public R<Map<String, Object>> meta() {
        Map<String, Object> m = new HashMap<>();
        m.put("title", title);
        m.put("baseline", Arrays.asList("captcha", "upload", "page", "errorcode", "profile", "avatar", "register"));
        m.put("registerRole", registerRole);
        return R.ok(m);
    }

    @GetMapping("/items")
    public R<Map<String, Object>> items(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String keyword) {
        List<Map<String, Object>> all = new ArrayList<>();
        for (int i = 1; i <= 23; i++) {
            Map<String, Object> row = new HashMap<>();
            row.put("id", i);
            row.put("name", "示例条目 " + i);
            row.put("status", i % 3 == 0 ? "disabled" : "active");
            all.add(row);
        }
        if (keyword != null && !keyword.isBlank()) {
            all.removeIf(r -> !r.get("name").toString().contains(keyword));
        }
        int from = Math.max(0, (page - 1) * size);
        int to = Math.min(all.size(), from + size);
        List<Map<String, Object>> slice = from >= all.size() ? List.of() : all.subList(from, to);
        return R.page(slice, all.size(), page, size);
    }

    @PostMapping("/upload")
    public R<Map<String, String>> upload(@RequestParam("file") MultipartFile file) throws IOException {
        if (file.isEmpty()) throw new BizException(ErrorCode.BAD_REQUEST, "文件为空");
        Path dir = Paths.get("uploads");
        Files.createDirectories(dir);
        String name = System.currentTimeMillis() + "_" + Objects.requireNonNull(file.getOriginalFilename());
        Path dest = dir.resolve(name);
        Files.copy(file.getInputStream(), dest, StandardCopyOption.REPLACE_EXISTING);
        Map<String, String> m = new HashMap<>();
        m.put("url", "/uploads/" + name);
        m.put("name", name);
        return R.ok(m);
    }
}
