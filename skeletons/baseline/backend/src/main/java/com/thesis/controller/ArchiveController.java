package com.thesis.controller;

import com.thesis.capability.ArchiveStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.GuestTeaser;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** 通用档案 API：/api/archive（设备 / 物资等；LIBRARY 另保留 /api/books） */
@RestController
@RequestMapping("/api/archive")
public class ArchiveController {

    @GetMapping
    public R<Map<String, Object>> page(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) Long categoryId,
            @RequestParam(required = false) String tagIds,
            @RequestParam(required = false, defaultValue = "false") boolean includeDeleted,
            HttpSession session) {
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
        boolean showDeleted = includeDeleted && admin && AdminAuth.isSuperAdmin(session);
        int p = GuestTeaser.clampPage(session, page);
        int s = GuestTeaser.clampSize(session, size);
        Map<String, Object> data = ArchiveStore.pageItems(keyword, categoryId, parseTagIds(tagIds), showDeleted, p, s);
        if (!admin) ArchiveStore.redactSensitiveListForPublic(data);
        return R.ok(data);
    }

    @GetMapping("/{id:\\d+}")
    public R<Map<String, Object>> detail(@PathVariable long id, HttpSession session) {
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
        Map<String, Object> item = admin ? ArchiveStore.getItemAdmin(id) : ArchiveStore.getItem(id);
        if (item == null) throw new BizException(ErrorCode.NOT_FOUND, "对象不存在");
        if (!admin) ArchiveStore.redactSensitiveForPublic(item);
        return R.ok(item);
    }

    /** CSV 批量导入：body.csv 为全文；表头为英文字段键（前端会把领域中文列名映射过来），含扩展列 */
    @PostMapping("/import")
    public R<Map<String, Object>> importCsv(@RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        String csv = body.get("csv") == null ? "" : String.valueOf(body.get("csv"));
        if (csv.isBlank()) throw new BizException(ErrorCode.BAD_REQUEST, "CSV 内容为空");
        return R.ok(ArchiveStore.importRows(parseArchiveCsv(csv)));
    }

    @PostMapping
    public R<Map<String, Object>> create(@RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        String title = str(body.get("title"));
        if (title.isBlank()) throw new BizException(ErrorCode.BAD_REQUEST, "名称不能为空");
        return R.ok(ArchiveStore.addItem(
                title,
                str(body.get("author")),
                str(body.get("isbn")),
                body.get("categoryId") == null ? 1L : Long.parseLong(String.valueOf(body.get("categoryId"))),
                body.get("stock") == null ? 1 : Integer.parseInt(String.valueOf(body.get("stock"))),
                str(body.get("coverUrl")),
                body
        ));
    }

    @PutMapping("/{id:\\d+}")
    public R<Map<String, Object>> update(
            @PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        Map<String, Object> updated = ArchiveStore.updateItem(id, body);
        if (updated == null) throw new BizException(ErrorCode.NOT_FOUND, "对象不存在");
        return R.ok(updated);
    }

    @DeleteMapping("/{id:\\d+}")
    public R<Void> delete(@PathVariable long id, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        if (!ArchiveStore.deleteItem(id)) throw new BizException(ErrorCode.NOT_FOUND, "对象不存在");
        return R.ok(null);
    }

    @PostMapping("/{id:\\d+}/restore")
    public R<Map<String, Object>> restore(@PathVariable long id, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        if (!ArchiveStore.restoreItem(id)) throw new BizException(ErrorCode.NOT_FOUND, "对象不存在或未下架");
        Map<String, Object> item = ArchiveStore.getItemAdmin(id);
        return R.ok(item);
    }

    private static List<Long> parseTagIds(String raw) {
        List<Long> out = new ArrayList<>();
        if (raw == null || raw.isBlank()) return out;
        for (String part : raw.split("[,\\s]+")) {
            try {
                long id = Long.parseLong(part.trim());
                if (id > 0) out.add(id);
            } catch (Exception ignored) {
            }
        }
        return out;
    }

    private static java.util.List<Map<String, String>> parseArchiveCsv(String csv) {
        String text = csv.replace("\uFEFF", "").replace("\r\n", "\n").replace('\r', '\n');
        String[] lines = text.split("\n");
        java.util.List<Map<String, String>> rows = new java.util.ArrayList<>();
        if (lines.length < 2) return rows;
        String[] headers = splitCsvLine(lines[0]);
        for (int i = 0; i < headers.length; i++) {
            headers[i] = canonArchiveHeader(headers[i]);
        }
        for (int i = 1; i < lines.length; i++) {
            if (lines[i].isBlank()) continue;
            String[] cols = splitCsvLine(lines[i]);
            Map<String, String> row = new java.util.LinkedHashMap<>();
            for (int c = 0; c < headers.length && c < cols.length; c++) {
                String key = headers[c];
                if (key == null || key.isBlank()) continue;
                row.put(key, cols[c].trim());
            }
            rows.add(row);
        }
        return rows;
    }

    /** 表头规范为 ArchiveStore 使用的 camelCase 键（兼容 start_at / StartAt 等）。 */
    private static String canonArchiveHeader(String raw) {
        String t = raw == null ? "" : raw.trim();
        if (t.isEmpty()) return t;
        String compact = t.replace("_", "").replace("-", "").toLowerCase(java.util.Locale.ROOT);
        return switch (compact) {
            case "title" -> "title";
            case "author" -> "author";
            case "isbn" -> "isbn";
            case "category", "categoryname" -> "category";
            case "stock" -> "stock";
            case "startat" -> "startAt";
            case "endat" -> "endAt";
            case "applydeadlineat" -> "applyDeadlineAt";
            case "mutexcode" -> "mutexCode";
            case "checkincode" -> "checkinCode";
            case "publisher" -> "publisher";
            case "callno" -> "callNo";
            case "conditiongrade" -> "conditionGrade";
            case "sellernote" -> "sellerNote";
            case "spicylevel" -> "spicyLevel";
            case "isvegetarian" -> "isVegetarian";
            case "requirestraining" -> "requiresTraining";
            case "ownername" -> "ownerName";
            case "stage" -> "stage";
            case "credit" -> "credit";
            case "servicehours" -> "serviceHours";
            case "seatcapacity" -> "seatCapacity";
            case "feerule" -> "feeRule";
            case "stylistname" -> "stylistName";
            case "durationsec" -> "durationSec";
            case "releaseyear" -> "releaseYear";
            case "region" -> "region";
            case "summary" -> "summary";
            case "itemkind" -> "itemKind";
            case "foundat" -> "foundAt";
            case "coverurl" -> "coverUrl";
            case "tags", "tag", "tagnames" -> "tags";
            default -> t;
        };
    }

    private static String[] splitCsvLine(String line) {
        java.util.List<String> cells = new java.util.ArrayList<>();
        StringBuilder cur = new StringBuilder();
        boolean inQuote = false;
        for (int i = 0; i < line.length(); i++) {
            char ch = line.charAt(i);
            if (ch == '"') {
                inQuote = !inQuote;
            } else if ((ch == ',' && !inQuote) || ch == '\t') {
                cells.add(cur.toString());
                cur.setLength(0);
            } else {
                cur.append(ch);
            }
        }
        cells.add(cur.toString());
        return cells.toArray(new String[0]);
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }
}
