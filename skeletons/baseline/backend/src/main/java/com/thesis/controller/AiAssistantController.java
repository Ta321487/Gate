package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.GuestTeaser;
import com.thesis.common.R;
import com.thesis.service.AiAssistantStore;
import com.thesis.service.DeepSeekClient;
import jakarta.servlet.http.HttpSession;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * AI 助手：对话问答、热门知识、满意度；管理端维护知识条目。
 */
@RestController
@RequestMapping("/api/ai-assistant")
public class AiAssistantController {

    @Value("${thesis.title:本系统}")
    private String appTitle;

    private void requireReady() {
        if (!AiAssistantStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通 AI 助手功能");
        }
    }

    @GetMapping("/status")
    public R<Map<String, Object>> status() {
        requireReady();
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("ready", true);
        m.put("deepseekConfigured", DeepSeekClient.configured());
        return R.ok(m);
    }

    @GetMapping("/hot")
    public R<Map<String, Object>> hot(
            @RequestParam(defaultValue = "8") int limit,
            HttpSession session) {
        requireReady();
        int n = GuestTeaser.clampSize(session, limit);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", AiAssistantStore.hotKnowledge(n));
        out.put("deepseekConfigured", DeepSeekClient.configured());
        return R.ok(out);
    }

    @GetMapping("/stats")
    public R<Map<String, Object>> stats(HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        requireReady();
        return R.ok(AiAssistantStore.stats());
    }

    @GetMapping("/messages")
    public R<Map<String, Object>> messages(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            HttpSession session) {
        requireReady();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(AiAssistantStore.pageMessages(uid, page, size));
    }

    @PostMapping("/ask")
    public R<Map<String, Object>> ask(@RequestBody Map<String, Object> body, HttpSession session) {
        requireReady();
        String uid = AdminAuth.requireLogin(session);
        String question = body == null ? "" : String.valueOf(body.getOrDefault("question", ""));
        if (question == null || question.isBlank() || "null".equals(question)) {
            throw new BizException(ErrorCode.BAD_REQUEST, "请输入问题");
        }
        String category = body == null ? "" : String.valueOf(body.getOrDefault("category", ""));
        if ("null".equals(category)) category = "";
        Map<String, Object> out = AiAssistantStore.ask(uid, question, category, appTitle);
        if (out == null) throw new BizException(ErrorCode.BAD_REQUEST, "问答失败");
        return R.ok(out);
    }

    /** 上传图片：按文件名映射品类后问答（非 CNN / 非以图搜图引擎） */
    @PostMapping("/ask-image")
    public R<Map<String, Object>> askImage(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "question", required = false) String question,
            @RequestParam(value = "category", required = false) String category,
            HttpSession session) {
        requireReady();
        String uid = AdminAuth.requireLogin(session);
        String filename = file == null ? "" : file.getOriginalFilename();
        String cat = AiAssistantStore.resolveCategoryHint(category, filename);
        String q = question == null || question.isBlank()
                ? ("请介绍一下" + (cat.isBlank() ? "这类商品" : cat) + "的挑选与保存要点")
                : question;
        if (cat.isBlank()) {
            cat = "通用";
        }
        Map<String, Object> out = AiAssistantStore.ask(uid, q, cat, appTitle);
        if (out == null) throw new BizException(ErrorCode.BAD_REQUEST, "问答失败");
        out.put("resolvedCategory", cat);
        out.put("filename", filename == null ? "" : filename);
        out.put("imageDemo", true);
        return R.ok(out);
    }

    @PostMapping("/feedback")
    public R<Map<String, Object>> feedback(@RequestBody Map<String, Object> body, HttpSession session) {
        requireReady();
        String uid = AdminAuth.requireLogin(session);
        if (body == null) throw new BizException(ErrorCode.BAD_REQUEST, "参数无效");
        Object sat = body.get("satisfied");
        boolean satisfied = sat instanceof Boolean b ? b
                : !"0".equals(String.valueOf(sat)) && !"false".equalsIgnoreCase(String.valueOf(sat));
        Long messageId = null;
        Object mid = body.get("messageId");
        if (mid instanceof Number n) messageId = n.longValue();
        else if (mid != null && !String.valueOf(mid).isBlank()) {
            try {
                messageId = Long.parseLong(String.valueOf(mid));
            } catch (NumberFormatException ignored) {
                messageId = null;
            }
        }
        String comment = String.valueOf(body.getOrDefault("comment", ""));
        if ("null".equals(comment)) comment = "";
        Map<String, Object> row = AiAssistantStore.addFeedback(uid, messageId, satisfied, comment);
        if (row == null) throw new BizException(ErrorCode.BAD_REQUEST, "反馈失败");
        return R.ok(row);
    }

    @GetMapping("/knowledge")
    public R<Map<String, Object>> knowledgePage(
            @RequestParam(required = false) String category,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        requireReady();
        return R.ok(AiAssistantStore.pageKnowledge(category, page, size));
    }

    @PostMapping("/knowledge")
    public R<Map<String, Object>> knowledgeCreate(@RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        requireReady();
        Map<String, Object> row = AiAssistantStore.saveKnowledge(null, body);
        if (row == null) throw new BizException(ErrorCode.BAD_REQUEST, "标题与内容不能为空");
        return R.ok(row);
    }

    @PutMapping("/knowledge/{id}")
    public R<Map<String, Object>> knowledgeUpdate(
            @PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        requireReady();
        Map<String, Object> row = AiAssistantStore.saveKnowledge(id, body);
        if (row == null) throw new BizException(ErrorCode.NOT_FOUND, "知识条目不存在或参数无效");
        return R.ok(row);
    }

    @DeleteMapping("/knowledge/{id}")
    public R<Void> knowledgeDelete(@PathVariable long id, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        requireReady();
        if (!AiAssistantStore.deleteKnowledge(id)) {
            throw new BizException(ErrorCode.NOT_FOUND, "知识条目不存在");
        }
        return R.ok(null);
    }
}
