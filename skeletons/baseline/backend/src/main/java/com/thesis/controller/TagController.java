package com.thesis.controller;

import com.thesis.capability.ArchiveStore;
import com.thesis.common.R;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/** L1 标签列表（FORUM 等） */
@RestController
@RequestMapping("/api/tags")
public class TagController {

    @GetMapping
    public R<List<Map<String, Object>>> list() {
        return R.ok(ArchiveStore.listTags());
    }
}
