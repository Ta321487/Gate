package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.ExamStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * 在线考试 API：管理端录题组卷；用户开考作答与成绩。
 */
@RestController
@RequestMapping("/api/exam")
public class ExamController {

    private static void requireExam() {
        if (!ExamStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通考试功能");
        }
    }

    // --- admin questions ---

    @GetMapping("/admin/questions")
    public R<Map<String, Object>> adminQuestions(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) Long subjectId,
            HttpSession session) {
        requireExam();
        AdminAuth.requireAdmin(session);
        return R.ok(ExamStore.pageQuestionsAdmin(page, size, subjectId));
    }

    @PostMapping("/admin/questions")
    public R<Map<String, Object>> adminCreateQuestion(
            @RequestBody Map<String, Object> body, HttpSession session) {
        requireExam();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(ExamStore.createQuestion(body == null ? Map.of() : body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PutMapping("/admin/questions/{id}")
    public R<Map<String, Object>> adminUpdateQuestion(
            @PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        requireExam();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(ExamStore.updateQuestion(id, body == null ? Map.of() : body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @DeleteMapping("/admin/questions/{id}")
    public R<Void> adminDeleteQuestion(@PathVariable long id, HttpSession session) {
        requireExam();
        AdminAuth.requireAdmin(session);
        try {
            if (!ExamStore.deleteQuestion(id)) {
                throw new BizException(ErrorCode.NOT_FOUND, "题目不存在");
            }
            return R.ok(null);
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    // --- admin papers ---

    @GetMapping("/admin/papers")
    public R<Map<String, Object>> adminPapers(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        requireExam();
        AdminAuth.requireAdmin(session);
        return R.ok(ExamStore.pagePapersAdmin(page, size));
    }

    @PostMapping("/admin/papers")
    public R<Map<String, Object>> adminCreatePaper(
            @RequestBody Map<String, Object> body, HttpSession session) {
        requireExam();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(ExamStore.createPaper(body == null ? Map.of() : body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PutMapping("/admin/papers/{id}")
    public R<Map<String, Object>> adminUpdatePaper(
            @PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        requireExam();
        AdminAuth.requireAdmin(session);
        try {
            return R.ok(ExamStore.updatePaper(id, body == null ? Map.of() : body));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @DeleteMapping("/admin/papers/{id}")
    public R<Void> adminDeletePaper(@PathVariable long id, HttpSession session) {
        requireExam();
        AdminAuth.requireAdmin(session);
        try {
            if (!ExamStore.deletePaper(id)) {
                throw new BizException(ErrorCode.NOT_FOUND, "试卷不存在");
            }
            return R.ok(null);
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/admin/papers/{id}/questions")
    public R<List<Map<String, Object>>> adminPaperQuestions(@PathVariable long id, HttpSession session) {
        requireExam();
        AdminAuth.requireAdmin(session);
        return R.ok(ExamStore.listPaperQuestionsAdmin(id));
    }

    @PutMapping("/admin/papers/{id}/questions")
    public R<Void> adminSetPaperQuestions(
            @PathVariable long id, @RequestBody List<Map<String, Object>> body, HttpSession session) {
        requireExam();
        AdminAuth.requireAdmin(session);
        try {
            ExamStore.setPaperQuestions(id, body);
            return R.ok(null);
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/admin/attempts")
    public R<Map<String, Object>> adminAttempts(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) Long paperId,
            HttpSession session) {
        requireExam();
        AdminAuth.requireAdmin(session);
        return R.ok(ExamStore.pageAttemptsAdmin(page, size, paperId));
    }

    // --- user papers & attempts ---

    @GetMapping("/papers")
    public R<List<Map<String, Object>>> listPapers(HttpSession session) {
        requireExam();
        AdminAuth.requireLogin(session);
        return R.ok(ExamStore.listPublishedPapers());
    }

    @PostMapping("/papers/{paperId}/start")
    public R<Map<String, Object>> start(
            @PathVariable long paperId,
            @RequestBody(required = false) Map<String, String> body,
            HttpSession session) {
        requireExam();
        String uid = AdminAuth.requireLogin(session);
        String mode = body == null ? "exam" : body.getOrDefault("mode", "exam");
        try {
            return R.ok(ExamStore.startAttempt(uid, paperId, mode));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/attempts/{attemptId}/questions")
    public R<List<Map<String, Object>>> attemptQuestions(
            @PathVariable long attemptId, HttpSession session) {
        requireExam();
        String uid = AdminAuth.requireLogin(session);
        try {
            Map<String, Object> attempt = ExamStore.getAttempt(attemptId);
            if (attempt == null) throw new BizException(ErrorCode.NOT_FOUND, "答卷不存在");
            boolean submitted = "submitted".equals(String.valueOf(attempt.get("status")));
            return R.ok(ExamStore.listAttemptQuestions(attemptId, uid, submitted));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.FORBIDDEN, e.getMessage());
        }
    }

    @PostMapping("/attempts/{attemptId}/submit")
    public R<Map<String, Object>> submit(
            @PathVariable long attemptId,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        requireExam();
        String uid = AdminAuth.requireLogin(session);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> answers = body == null
                ? List.of()
                : (List<Map<String, Object>>) body.get("answers");
        try {
            return R.ok(ExamStore.submitAttempt(attemptId, uid, answers));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/attempts/mine")
    public R<Map<String, Object>> myAttempts(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        requireExam();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(ExamStore.pageMyAttempts(uid, page, size));
    }

    @GetMapping("/papers/{paperId}/rank")
    public R<Map<String, Object>> rank(
            @PathVariable long paperId,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        requireExam();
        AdminAuth.requireLogin(session);
        try {
            return R.ok(ExamStore.pageRank(paperId, page, size));
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/wrongbook")
    public R<Map<String, Object>> wrongbook(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        requireExam();
        String uid = AdminAuth.requireLogin(session);
        try {
            return R.ok(ExamStore.pageWrongbook(uid, page, size));
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @DeleteMapping("/wrongbook/{id}")
    public R<Void> deleteWrongbook(@PathVariable long id, HttpSession session) {
        requireExam();
        String uid = AdminAuth.requireLogin(session);
        try {
            if (!ExamStore.deleteWrongbook(uid, id)) {
                throw new BizException(ErrorCode.NOT_FOUND, "记录不存在");
            }
            return R.ok(null);
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
