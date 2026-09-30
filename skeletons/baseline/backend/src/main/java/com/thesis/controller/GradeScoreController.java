package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.GradeScoreStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/grade-scores")
public class GradeScoreController {

    private static void requireOn() {
        if (!GradeScoreStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通成绩登记");
        }
    }

    @GetMapping("/meta")
    public R<Map<String, Object>> meta(HttpSession session) {
        requireOn();
        AdminAuth.requireLogin(session);
        return R.ok(GradeScoreStore.meta());
    }

    @GetMapping("/mine")
    public R<List<Map<String, Object>>> mine(HttpSession session) {
        requireOn();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(GradeScoreStore.listMine(uid));
    }

    /** 用户端：成绩异议申请时限（入口按时限关的前端依据）。 */
    @GetMapping("/objection-window")
    public R<Map<String, Object>> objectionWindow(
            @RequestParam long courseId, HttpSession session) {
        requireOn();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(GradeScoreStore.objectionWindow(uid, courseId));
    }

    @GetMapping("/admin")
    public R<List<Map<String, Object>>> admin(
            @RequestParam(required = false) Long courseId,
            @RequestParam(required = false) Long termId,
            HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        return R.ok(GradeScoreStore.listAdmin(courseId, termId));
    }

    @PostMapping("/admin")
    public R<Map<String, Object>> save(@RequestBody Map<String, Object> body, HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        if (body == null) body = Map.of();
        String username = body.get("username") == null ? "" : String.valueOf(body.get("username"));
        long courseId = Long.parseLong(String.valueOf(body.getOrDefault("courseId", "0")));
        long termId = Long.parseLong(String.valueOf(body.getOrDefault("termId", "0")));
        Object raw = body.get("score");
        if (raw == null || String.valueOf(raw).isBlank()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "请填写分数");
        }
        BigDecimal score;
        try {
            score = new BigDecimal(String.valueOf(raw).trim());
        } catch (NumberFormatException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, "分数格式不正确");
        }
        try {
            return R.ok(GradeScoreStore.save(username, courseId, termId, score));
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @DeleteMapping("/admin/{id}")
    public R<Void> delete(@PathVariable long id, HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        try {
            GradeScoreStore.delete(id);
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.NOT_FOUND, e.getMessage());
        }
        return R.ok(null);
    }

    /** 分布与及格率（按课程/学期筛选；及格线 60）。 */
    @GetMapping("/admin/stats")
    public R<Map<String, Object>> stats(
            @RequestParam(required = false) Long courseId,
            @RequestParam(required = false) Long termId,
            HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        return R.ok(GradeScoreStore.stats(courseId, termId));
    }

    /** 单条成绩的改分记录（删除也留痕）。 */
    @GetMapping("/admin/history")
    public R<List<Map<String, Object>>> history(@RequestParam long scoreId, HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        return R.ok(GradeScoreStore.history(scoreId));
    }

    /** CSV 批量导入：表头 学生账号,课程ID,学期ID,分数（无表头则按此顺序）。 */
    @PostMapping("/admin/import")
    public R<Map<String, Object>> importCsv(@RequestBody Map<String, Object> body, HttpSession session) {
        requireOn();
        AdminAuth.requireAdmin(session);
        String operator = AdminAuth.requireLogin(session);
        Object raw = body == null ? null : body.get("csv");
        List<Map<String, Object>> rows = parseCsv(raw == null ? "" : String.valueOf(raw));
        if (rows.isEmpty()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "没有可导入的数据行");
        }
        if (rows.size() > 500) {
            throw new BizException(ErrorCode.BAD_REQUEST, "单次最多导入 500 行，请拆分后再导入");
        }
        return R.ok(GradeScoreStore.importRows(rows, operator));
    }

    private static final List<String> CSV_USER_KEYS =
            List.of("username", "studentaccount", "学生账号", "账号", "学号");
    private static final List<String> CSV_COURSE_KEYS =
            List.of("courseid", "course", "课程id", "课程");
    private static final List<String> CSV_TERM_KEYS =
            List.of("termid", "term", "学期id", "学期");
    private static final List<String> CSV_SCORE_KEYS =
            List.of("score", "成绩", "分数");

    /** 解析 CSV 模板：首条非空行是表头（认中英文列名），认不出则按位置取列。 */
    private static List<Map<String, Object>> parseCsv(String csv) {
        String text = csv == null ? "" : csv.replace("\uFEFF", "");
        String[] lines = text.split("\\r?\\n");
        List<Map<String, Object>> rows = new java.util.ArrayList<>();
        int userIdx = 0;
        int courseIdx = 1;
        int termIdx = 2;
        int scoreIdx = 3;
        boolean headerSeen = false;
        for (int i = 0; i < lines.length; i++) {
            String raw = lines[i] == null ? "" : lines[i];
            if (raw.trim().isEmpty()) continue;
            List<String> cells = splitCsvLine(raw);
            if (!headerSeen) {
                headerSeen = true;
                int u = headerIndex(cells, CSV_USER_KEYS);
                int s = headerIndex(cells, CSV_SCORE_KEYS);
                if (u >= 0 && s >= 0) {
                    userIdx = u;
                    scoreIdx = s;
                    courseIdx = headerIndex(cells, CSV_COURSE_KEYS);
                    termIdx = headerIndex(cells, CSV_TERM_KEYS);
                    continue;
                }
            }
            Map<String, Object> row = new java.util.LinkedHashMap<>();
            row.put("line", i + 1);
            row.put("username", csvCell(cells, userIdx));
            row.put("courseId", csvCell(cells, courseIdx));
            row.put("termId", csvCell(cells, termIdx));
            row.put("score", csvCell(cells, scoreIdx));
            rows.add(row);
        }
        return rows;
    }

    private static int headerIndex(List<String> cells, List<String> keys) {
        for (int i = 0; i < cells.size(); i++) {
            String h = normalizeHeader(cells.get(i));
            if (h.isEmpty()) continue;
            for (String k : keys) {
                if (h.equals(normalizeHeader(k))) return i;
            }
        }
        return -1;
    }

    private static String normalizeHeader(String s) {
        return s == null
                ? ""
                : s.trim().replace("_", "").replace(" ", "").replace("\u3000", "").toLowerCase();
    }

    private static String csvCell(List<String> cells, int idx) {
        return idx >= 0 && idx < cells.size() ? cells.get(idx).trim() : "";
    }

    /** RFC4180 简化版：支持双引号包裹与 "" 转义。 */
    private static List<String> splitCsvLine(String line) {
        List<String> out = new java.util.ArrayList<>();
        StringBuilder cur = new StringBuilder();
        boolean quoted = false;
        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);
            if (quoted) {
                if (c == '"') {
                    if (i + 1 < line.length() && line.charAt(i + 1) == '"') {
                        cur.append('"');
                        i++;
                    } else {
                        quoted = false;
                    }
                } else {
                    cur.append(c);
                }
            } else if (c == '"') {
                quoted = true;
            } else if (c == ',') {
                out.add(cur.toString());
                cur.setLength(0);
            } else {
                cur.append(c);
            }
        }
        out.add(cur.toString());
        return out;
    }
}
