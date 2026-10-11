package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.SurveyStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/survey")
public class SurveyController {

    private static void requireSurvey() {
        if (!SurveyStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通问卷功能");
        }
    }

    @GetMapping("/forms")
    public R<List<Map<String, Object>>> forms(HttpSession session) {
        requireSurvey();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(SurveyStore.listOpenForms(uid));
    }

    @GetMapping("/admin/forms")
    public R<List<Map<String, Object>>> adminForms(HttpSession session) {
        requireSurvey();
        AdminAuth.requireAdmin(session);
        return R.ok(SurveyStore.listAdminForms());
    }

    @GetMapping("/forms/{id}")
    public R<Map<String, Object>> form(@PathVariable long id, HttpSession session) {
        requireSurvey();
        AdminAuth.requireLogin(session);
        Map<String, Object> form = SurveyStore.getForm(id);
        if (form == null) throw new BizException(ErrorCode.NOT_FOUND, "问卷不存在");
        return R.ok(form);
    }

    @PatchMapping("/admin/forms/{id}")
    public R<Map<String, Object>> patchForm(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        requireSurvey();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(SurveyStore.updateFormSettings(id, body == null ? Map.of() : body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/forms/{id}/questions")
    public R<List<Map<String, Object>>> questions(@PathVariable long id, HttpSession session) {
        requireSurvey();
        AdminAuth.requireLogin(session);
        return R.ok(SurveyStore.listQuestions(id));
    }

    @GetMapping("/forms/{id}/draft")
    public R<Map<String, Object>> loadDraft(@PathVariable long id, HttpSession session) {
        requireSurvey();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(SurveyStore.loadDraft(uid, id));
    }

    @PutMapping("/forms/{id}/draft")
    public R<Void> saveDraft(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        requireSurvey();
        String uid = AdminAuth.requireLogin(session);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> answers = body == null
                ? List.of()
                : (List<Map<String, Object>>) body.get("answers");
        try {
            SurveyStore.saveDraft(uid, id, answers == null ? List.of() : answers);
            return R.ok(null);
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/forms/{id}/submit")
    public R<Map<String, Object>> submit(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        requireSurvey();
        String uid = AdminAuth.requireLogin(session);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> answers = body == null
                ? List.of()
                : (List<Map<String, Object>>) body.get("answers");
        try {
            return R.ok(SurveyStore.submit(uid, id, answers));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/responses/mine")
    public R<Map<String, Object>> mine(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        requireSurvey();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(SurveyStore.pageMine(uid, page, size));
    }

    @GetMapping("/admin/forms/{formId}/questions")
    public R<Map<String, Object>> adminQuestions(
            @PathVariable long formId,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            HttpSession session) {
        requireSurvey();
        AdminAuth.requireAdmin(session);
        return R.ok(SurveyStore.pageQuestionsAdmin(formId, page, size));
    }

    @PostMapping("/admin/questions")
    public R<Map<String, Object>> createQuestion(@RequestBody Map<String, Object> body, HttpSession session) {
        requireSurvey();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(SurveyStore.createQuestion(body == null ? Map.of() : body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @DeleteMapping("/admin/questions/{id}")
    public R<Void> deleteQuestion(@PathVariable long id, HttpSession session) {
        requireSurvey();
        AdminAuth.requireAdmin(session);
        if (!SurveyStore.deleteQuestion(id)) {
            throw new BizException(ErrorCode.NOT_FOUND, "题目不存在");
        }
        return R.ok(null);
    }

    @GetMapping("/admin/forms/{formId}/responses")
    public R<Map<String, Object>> adminResponses(
            @PathVariable long formId,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        requireSurvey();
        AdminAuth.requireAdmin(session);
        return R.ok(SurveyStore.pageResponsesAdmin(formId, page, size));
    }

    @GetMapping("/admin/forms/{formId}/stats")
    public R<List<Map<String, Object>>> stats(@PathVariable long formId, HttpSession session) {
        requireSurvey();
        AdminAuth.requireAdmin(session);
        return R.ok(SurveyStore.stats(formId));
    }

    @GetMapping("/admin/recycle-cards")
    public R<List<Map<String, Object>>> recycleCards(HttpSession session) {
        requireSurvey();
        AdminAuth.requireAdmin(session);
        return R.ok(SurveyStore.recycleCards());
    }
}
