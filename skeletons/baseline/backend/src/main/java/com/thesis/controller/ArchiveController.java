package com.thesis.controller;

import com.thesis.capability.ArchiveStore;
import com.thesis.capability.AuditLogStore;
import com.thesis.capability.ExcelBook;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.config.AppPolicy;
import com.thesis.common.ErrorCode;
import com.thesis.common.GuestTeaser;
import com.thesis.common.R;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
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
            @RequestParam(required = false) String categoryIds,
            @RequestParam(required = false) String tagIds,
            @RequestParam(required = false) String artist,
            @RequestParam(required = false) String album,
            @RequestParam(required = false) String city,
            @RequestParam(required = false) Integer ageMin,
            @RequestParam(required = false) Integer ageMax,
            @RequestParam(required = false) String listStatus,
            @RequestParam(required = false) String createdFrom,
            @RequestParam(required = false) String createdTo,
            @RequestParam(required = false, defaultValue = "false") boolean deletedOnly,
            @RequestParam(required = false) Integer year,
            @RequestParam(required = false) Integer month,
            /** 为 true 时只返回窗内活动价商品（需挂 flash_price）；门户限时特价区用 */
            @RequestParam(required = false, defaultValue = "false") boolean promoActive,
            @RequestParam(required = false, defaultValue = "false") boolean includeDeleted,
            HttpSession session) {
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
        boolean showDeleted = includeDeleted && admin && AdminAuth.isSuperAdmin(session);
        int p = GuestTeaser.clampPage(session, page);
        int s = GuestTeaser.clampSize(session, size);
        Map<String, Object> data;
        if (promoActive && !admin) {
            data = ArchiveStore.pagePromoActive(p, s);
        } else if (admin && ArchiveStore.shopMarketplaceEnabled() && !AdminAuth.isSuperAdmin(session)) {
            String uid = AdminAuth.requireLogin(session);
            data = ArchiveStore.pageItemsForMerchant(uid, keyword, categoryId, p, s);
        } else if (!admin && year != null && year > 0) {
            data = ArchiveStore.pageByYearMonth(year, month, keyword, categoryId, p, s);
        } else {
            data = ArchiveStore.pageItems(
                    keyword,
                    categoryId,
                    parseTagIds(categoryIds),
                    parseTagIds(tagIds),
                    showDeleted,
                    p,
                    s,
                    !admin,
                    null,
                    artist,
                    album,
                    city,
                    ageMin,
                    ageMax,
                    listStatus,
                    createdFrom,
                    createdTo,
                    deletedOnly);
        }
        if (!admin) ArchiveStore.redactSensitiveListForPublic(data);
        return R.ok(data);
    }

    /** 作者主页 */
    @GetMapping("/by-author")
    public R<Map<String, Object>> byAuthor(
            @RequestParam String username,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        int p = GuestTeaser.clampPage(session, page);
        int s = GuestTeaser.clampSize(session, size);
        Map<String, Object> data = ArchiveStore.pageByAuthor(username, p, s);
        ArchiveStore.redactSensitiveListForPublic(data);
        return R.ok(data);
    }

    /** 系列文上一篇/下一篇 */
    @GetMapping("/{id:\\d+}/series-neighbors")
    public R<Map<String, Object>> seriesNeighbors(@PathVariable long id) {
        return R.ok(ArchiveStore.seriesNeighbors(id));
    }

    /** 口令解锁正文；会话内记住 */
    @PostMapping("/{id:\\d+}/unlock")
    public R<Map<String, Object>> unlock(
            @PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        String pw = body == null || body.get("password") == null ? "" : String.valueOf(body.get("password"));
        if (!ArchiveStore.checkAccessPassword(id, pw)) {
            throw new BizException(ErrorCode.BAD_REQUEST, "口令不正确");
        }
        session.setAttribute("archiveUnlock:" + id, Boolean.TRUE);
        Map<String, Object> item = ArchiveStore.getItem(id);
        if (item == null) throw new BizException(ErrorCode.NOT_FOUND, "对象不存在");
        ArchiveStore.redactSensitiveForPublic(item);
        ArchiveStore.restoreContentIfUnlocked(item, true);
        return R.ok(item);
    }

    @GetMapping("/suggest")
    public R<?> suggest(
            @RequestParam(required = false) String q,
            @RequestParam(defaultValue = "8") int limit) {
        return R.ok(ArchiveStore.suggestTitles(q, limit));
    }

    /** 内容组热门排行：按阅读数 / 下载数排序。 */
    @GetMapping("/hot")
    public R<Map<String, Object>> hot(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String sortBy,
            HttpSession session) {
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
        int p = GuestTeaser.clampPage(session, page);
        int s = GuestTeaser.clampSize(session, size);
        Map<String, Object> data = ArchiveStore.pageHot(sortBy, p, s);
        if (!admin) ArchiveStore.redactSensitiveListForPublic(data);
        return R.ok(data);
    }

    /** 我的主帖：登录用户按 owner/author 列表（含已下架）；status=draft 筛草稿箱 */
    @GetMapping("/mine")
    public R<Map<String, Object>> mine(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String status,
            HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        if (!ArchiveStore.userPublishEnabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "当前领域未开放用户发帖");
        }
        return R.ok(ArchiveStore.pageMine(uid, page, size, status));
    }

    /** 用户发布档案：即时可见，或开启「先审后发」 */
    @PostMapping("/publish")
    public R<Map<String, Object>> publish(@RequestBody Map<String, Object> body, HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        if (!ArchiveStore.userPublishEnabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "当前领域未开放用户发布");
        }
        String title = str(body.get("title"));
        String content = str(body.get("isbn"));
        if (content.isBlank()) content = str(body.get("body"));
        long categoryId = 1L;
        if (body.get("categoryId") != null && !String.valueOf(body.get("categoryId")).isBlank()) {
            try {
                categoryId = Long.parseLong(String.valueOf(body.get("categoryId")).trim());
            } catch (Exception e) {
                throw new BizException(ErrorCode.BAD_REQUEST, "分类无效");
            }
            if (categoryId <= 0) {
                throw new BizException(ErrorCode.BAD_REQUEST, "分类无效");
            }
        }
        String author = str(body.get("author"));
        Integer stock = null;
        if (body.get("stock") != null && !String.valueOf(body.get("stock")).isBlank()) {
            try {
                stock = Integer.parseInt(String.valueOf(body.get("stock")).trim());
            } catch (Exception e) {
                throw new BizException(ErrorCode.BAD_REQUEST, "数量无效");
            }
            if (stock < 0) {
                throw new BizException(ErrorCode.BAD_REQUEST, "数量无效");
            }
        }
        boolean asDraft = "1".equals(str(body.get("draft")))
                || "true".equalsIgnoreCase(str(body.get("draft")))
                || "draft".equalsIgnoreCase(str(body.get("status")));
        long draftId = 0L;
        if (asDraft && body.get("id") != null && !String.valueOf(body.get("id")).isBlank()) {
            try {
                draftId = Long.parseLong(String.valueOf(body.get("id")).trim());
            } catch (Exception ignored) {
                draftId = 0L;
            }
        }
        try {
            // 同一出发时间与路线的行程只保留一条（非拼车域自动放行）
            if (!asDraft && ArchiveStore.isDuplicateTrip(uid, title, str(body.get("startAt")))) {
                throw new BizException(ErrorCode.BAD_REQUEST, "你已发布过相同出发时间与路线的行程，请勿重复发布。");
            }
            Map<String, Object> item;
            if (asDraft && draftId > 0) {
                item = ArchiveStore.updateUserDraft(draftId, uid, title, content, categoryId);
            } else if (asDraft) {
                item = ArchiveStore.saveUserDraft(uid, title, content, categoryId);
            } else {
                item = ArchiveStore.addUserPost(
                        uid, title, content, categoryId, author.isBlank() ? null : author, stock);
            }
            if (item == null) throw new BizException(ErrorCode.BAD_REQUEST, asDraft ? "存草稿失败" : "发布失败");
            long id = ((Number) item.get("id")).longValue();
            Map<String, Object> patch = new LinkedHashMap<>();
            String startAt = str(body.get("startAt"));
            if (!asDraft && !startAt.isBlank() && ArchiveStore.hasStartAt()) {
                patch.put("startAt", startAt);
            }
            String originKind = str(body.get("originKind"));
            if (!originKind.isBlank()) patch.put("originKind", originKind);
            String accessPassword = str(body.get("accessPassword"));
            if (!accessPassword.isBlank()) patch.put("accessPassword", accessPassword);
            // 行程加厚字段（空值不写入；非法数字忽略）
            String viaPoints = str(body.get("viaPoints"));
            if (!viaPoints.isBlank()) patch.put("viaPoints", viaPoints);
            String shareNote = str(body.get("shareNote"));
            if (!shareNote.isBlank()) patch.put("shareNote", shareNote);
            String prefNote = str(body.get("prefNote"));
            if (!prefNote.isBlank()) patch.put("prefNote", prefNote);
            String luggageRaw = str(body.get("luggageCount"));
            if (!luggageRaw.isBlank()) {
                try {
                    patch.put("luggageCount", Integer.parseInt(luggageRaw));
                } catch (NumberFormatException ignored) {
                    // 行李件数非法则忽略
                }
            }
            String startCampus = str(body.get("startCampus"));
            if (!startCampus.isBlank()) patch.put("startCampus", startCampus);
            String endCampus = str(body.get("endCampus"));
            if (!endCampus.isBlank()) patch.put("endCampus", endCampus);
            String remindRaw = str(body.get("remindBeforeMinutes"));
            if (!remindRaw.isBlank()) {
                try {
                    patch.put("remindBeforeMinutes", Integer.parseInt(remindRaw));
                } catch (NumberFormatException ignored) {
                    // 提前提醒分钟数非法则忽略
                }
            }
            String fareRaw = str(body.get("fareTotalYuan"));
            if (!fareRaw.isBlank()) {
                try {
                    patch.put("fareTotalYuan", Double.parseDouble(fareRaw));
                } catch (NumberFormatException ignored) {
                    // 总费用非法则忽略
                }
            }
            if (!patch.isEmpty()) {
                item = ArchiveStore.updateItem(id, patch);
            }
            if (!asDraft && item != null) {
                ArchiveStore.notifyCategoryFollowersIfPublic(id);
            }
            return R.ok(item);
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 草稿发布：进入待审或直接上架 */
    @PostMapping("/{id:\\d+}/publish-draft")
    public R<Map<String, Object>> publishDraft(@PathVariable long id, HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        try {
            Map<String, Object> item = ArchiveStore.publishDraft(id, uid);
            if (item == null) throw new BizException(ErrorCode.BAD_REQUEST, "发布失败");
            return R.ok(item);
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/{id:\\d+}")
    public R<Map<String, Object>> detail(@PathVariable long id, HttpSession session) {
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
        Map<String, Object> item = admin ? ArchiveStore.getItemAdmin(id) : ArchiveStore.getItem(id);
        // 本人草稿/待审/驳回：公开目录不可见，但「我的」详情仍可看
        if (item == null && !admin) {
            Object uidAttr = session.getAttribute("uid");
            String uid = uidAttr == null ? "" : uidAttr.toString().trim();
            Map<String, Object> raw = ArchiveStore.getItemAdmin(id);
            if (raw != null && !uid.isBlank()
                    && (uid.equals(str(raw.get("ownerUsername"))) || uid.equals(str(raw.get("author"))))) {
                String st = str(raw.get("status"));
                if ("draft".equals(st) || "pending_review".equals(st) || "rejected".equals(st)
                        || ArchiveStore.publishReviewEnabled()) {
                    item = raw;
                }
            }
        }
        if (item == null) throw new BizException(ErrorCode.NOT_FOUND, "对象不存在");
        if (admin && ArchiveStore.shopMarketplaceEnabled() && !AdminAuth.isSuperAdmin(session)) {
            String uid = AdminAuth.requireLogin(session);
            if (!uid.equals(str(item.get("ownerUsername")))) {
                throw new BizException(ErrorCode.FORBIDDEN, "无权查看");
            }
        }
        if (!admin) {
            ArchiveStore.bumpViewCount(id);
            ArchiveStore.redactSensitiveForPublic(item);
            boolean unlocked = Boolean.TRUE.equals(session.getAttribute("archiveUnlock:" + id));
            if (unlocked) ArchiveStore.restoreContentIfUnlocked(item, true);
            // 回读最新浏览计数（失败不影响详情）
            try {
                Map<String, Object> refreshed = ArchiveStore.getItem(id);
                if (refreshed != null && refreshed.get("viewCount") != null) {
                    item.put("viewCount", refreshed.get("viewCount"));
                }
            } catch (Exception ignored) {
            }
        }
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

    /** 下载 xlsx 导入模板。表头为中文，字段键写在隐藏表。 */
    @PostMapping("/import-template")
    public void importTemplate(@RequestBody Map<String, Object> body, HttpServletResponse response, HttpSession session)
            throws IOException {
        AdminAuth.requireSuperAdmin(session);
        List<String> labels = new ArrayList<>();
        List<String> keys = new ArrayList<>();
        List<String> samples = new ArrayList<>();
        Object raw = body.get("columns");
        if (raw instanceof List<?> cols) {
            for (Object item : cols) {
                if (!(item instanceof Map<?, ?> col)) continue;
                String key = str(col.get("key"));
                String label = str(col.get("label"));
                if (key.isBlank()) continue;
                keys.add(key);
                labels.add(label.isBlank() ? key : label);
                samples.add(str(col.get("sample")));
            }
        }
        if (keys.isEmpty()) throw new BizException(ErrorCode.BAD_REQUEST, "没有可导入的列");
        byte[] bytes = ExcelBook.template(labels, keys, samples);
        writeXlsx(response, "import-template.xlsx", bytes);
    }

    /** 导入 xlsx。空行跳过；返回成功条数与行错误（行号按 Excel）。 */
    @PostMapping("/import-xlsx")
    public R<Map<String, Object>> importXlsx(@RequestParam("file") MultipartFile file, HttpSession session)
            throws IOException {
        AdminAuth.requireSuperAdmin(session);
        if (file == null || file.isEmpty()) throw new BizException(ErrorCode.BAD_REQUEST, "请选择 xlsx 文件");
        String name = file.getOriginalFilename() == null ? "" : file.getOriginalFilename().toLowerCase();
        if (!name.endsWith(".xlsx")) throw new BizException(ErrorCode.BAD_REQUEST, "请上传 xlsx 文件（先下载导入模板）");
        List<Map<String, String>> rows;
        try {
            rows = canonImportRows(ExcelBook.readImport(file.getInputStream()));
        } catch (Exception e) {
            throw new BizException(ErrorCode.BAD_REQUEST, "无法读取该文件，请使用导入模板（xlsx）");
        }
        if (rows.isEmpty()) throw new BizException(ErrorCode.BAD_REQUEST, "没有可导入的数据，请从第 2 行填写");
        boolean hasTitle = rows.stream().anyMatch(r -> r.containsKey("title"));
        if (!hasTitle) throw new BizException(ErrorCode.BAD_REQUEST, "模板缺少名称列");
        return R.ok(ArchiveStore.importRows(rows));
    }

    /** 当前列表导出为 xlsx。 */
    @PostMapping("/export-xlsx")
    public void exportXlsx(@RequestBody Map<String, Object> body, HttpServletResponse response, HttpSession session)
            throws IOException {
        AdminAuth.requireSuperAdmin(session);
        List<String> labels = stringList(body.get("headers"));
        List<List<String>> rows = new ArrayList<>();
        Object raw = body.get("rows");
        if (raw instanceof List<?> list) {
            for (Object item : list) {
                rows.add(stringList(item));
            }
        }
        if (labels.isEmpty()) throw new BizException(ErrorCode.BAD_REQUEST, "没有可导出的列");
        byte[] bytes = ExcelBook.table("导出", labels, rows);
        writeXlsx(response, "archive.xlsx", bytes);
    }

    private static void writeXlsx(HttpServletResponse response, String filename, byte[] bytes) throws IOException {
        response.setContentType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
        response.setHeader("Content-Disposition", "attachment; filename=\"" + filename + "\"");
        response.getOutputStream().write(bytes);
    }

    private static List<Map<String, String>> canonImportRows(List<Map<String, String>> raw) {
        List<Map<String, String>> out = new ArrayList<>();
        for (Map<String, String> row : raw) {
            Map<String, String> mapped = new LinkedHashMap<>();
            for (Map.Entry<String, String> e : row.entrySet()) {
                if ("__line".equals(e.getKey())) {
                    mapped.put("__line", e.getValue());
                    continue;
                }
                String key = canonArchiveHeader(e.getKey());
                if (key.isBlank()) continue;
                mapped.put(key, e.getValue());
            }
            out.add(mapped);
        }
        return out;
    }

    private static List<String> stringList(Object raw) {
        List<String> out = new ArrayList<>();
        if (!(raw instanceof List<?> list)) return out;
        for (Object item : list) out.add(item == null ? "" : String.valueOf(item));
        return out;
    }

    /** 档案批量删除（软删开启时进入回收站）。 */
    @PostMapping("/batch-delete")
    public R<Map<String, Object>> batchDelete(@RequestBody Map<String, Object> body, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        if (AppPolicy.SENSITIVE_CONFIRM) {
            Object mark = body == null ? null : body.get("confirm");
            boolean ok = Boolean.TRUE.equals(mark) || "true".equalsIgnoreCase(String.valueOf(mark));
            if (!ok) throw new BizException(ErrorCode.BAD_REQUEST, "请再次确认后再删除");
        }
        int ok = 0;
        Object raw = body == null ? null : body.get("ids");
        if (raw instanceof java.util.Collection<?> col) {
            for (Object o : col) {
                if (o == null) continue;
                try {
                    if (ArchiveStore.deleteItem(Long.parseLong(String.valueOf(o)))) ok++;
                } catch (Exception ignored) {
                }
            }
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("ok", ok);
        return R.ok(out);
    }

    @PostMapping
    public R<Map<String, Object>> create(@RequestBody Map<String, Object> body, HttpSession session) {
        Map<String, Object> payload = body == null ? new LinkedHashMap<>() : new LinkedHashMap<>(body);
        if (ArchiveStore.shopMarketplaceEnabled()) {
            AdminAuth.requireAdmin(session);
            if (!AdminAuth.isSuperAdmin(session)) {
                String uid = AdminAuth.requireLogin(session);
                payload.put("ownerUsername", uid);
                payload.put("status", "pending_review");
            }
        } else {
            AdminAuth.requireSuperAdmin(session);
        }
        String title = str(payload.get("title"));
        if (title.isBlank()) throw new BizException(ErrorCode.BAD_REQUEST, "名称不能为空");
        return R.ok(ArchiveStore.addItem(
                title,
                str(payload.get("author")),
                str(payload.get("isbn")),
                payload.get("categoryId") == null ? 1L : Long.parseLong(String.valueOf(payload.get("categoryId"))),
                payload.get("stock") == null ? 1 : Integer.parseInt(String.valueOf(payload.get("stock"))),
                str(payload.get("coverUrl")),
                payload
        ));
    }

    @PutMapping("/{id:\\d+}")
    public R<Map<String, Object>> update(
            @PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        Map<String, Object> payload = body == null ? new LinkedHashMap<>() : new LinkedHashMap<>(body);
        if (ArchiveStore.shopMarketplaceEnabled()) {
            AdminAuth.requireAdmin(session);
            if (!AdminAuth.isSuperAdmin(session)) {
                String uid = AdminAuth.requireLogin(session);
                Map<String, Object> existing = ArchiveStore.getItemAdmin(id);
                if (existing == null) throw new BizException(ErrorCode.NOT_FOUND, "对象不存在");
                if (!uid.equals(str(existing.get("ownerUsername")))) {
                    throw new BizException(ErrorCode.FORBIDDEN, "只能修改本店商品");
                }
                payload.put("ownerUsername", uid);
                // 商家改商品不得自改审核态；公开上架只走 approve
                payload.remove("status");
            }
        } else {
            AdminAuth.requireSuperAdmin(session);
        }
        Map<String, Object> updated = ArchiveStore.updateItem(id, payload);
        if (updated == null) throw new BizException(ErrorCode.NOT_FOUND, "对象不存在");
        String op = AdminAuth.requireLogin(session);
        if (payload.containsKey("pinTop") || payload.containsKey("essence")) {
            AuditLogStore.record(op, "archive_pin_essence", "archive", String.valueOf(id), "置顶/精华标记变更");
        } else {
            AuditLogStore.record(op, "archive_update", "archive", String.valueOf(id), "更新档案");
        }
        return R.ok(updated);
    }

    @DeleteMapping("/{id:\\d+}")
    public R<Void> delete(
            @PathVariable long id,
            @RequestBody(required = false) Map<String, Object> body,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        if (AppPolicy.SENSITIVE_CONFIRM) {
            Object mark = body == null ? null : body.get("confirm");
            boolean ok = Boolean.TRUE.equals(mark) || "true".equalsIgnoreCase(String.valueOf(mark));
            if (!ok) throw new BizException(ErrorCode.BAD_REQUEST, "请再次确认后再删除");
        }
        String reason = body == null || body.get("offShelfReason") == null
                ? "" : String.valueOf(body.get("offShelfReason"));
        if (!ArchiveStore.deleteItem(id, reason)) throw new BizException(ErrorCode.NOT_FOUND, "对象不存在");
        String op = AdminAuth.requireLogin(session);
        AuditLogStore.record(op, "archive_delete", "archive", String.valueOf(id), "删除档案");
        return R.ok(null);
    }

    /** 片单分享码只读打开 */
    @GetMapping("/by-share-code")
    public R<Map<String, Object>> byShareCode(@RequestParam String code) {
        Map<String, Object> item = ArchiveStore.getByShareCode(code);
        if (item == null) throw new BizException(ErrorCode.NOT_FOUND, "分享码无效");
        ArchiveStore.redactSensitiveForPublic(item);
        return R.ok(item);
    }

    @PostMapping("/{id:\\d+}/restore")
    public R<Map<String, Object>> restore(@PathVariable long id, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        if (!ArchiveStore.restoreItem(id)) throw new BizException(ErrorCode.NOT_FOUND, "对象不存在或未下架");
        Map<String, Object> item = ArchiveStore.getItemAdmin(id);
        return R.ok(item);
    }

    /** 多店 / 投稿先审：超管审核上架 */
    @PostMapping("/{id:\\d+}/approve")
    public R<Map<String, Object>> approve(@PathVariable long id, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        if (!ArchiveStore.shopMarketplaceEnabled() && !ArchiveStore.publishReviewEnabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "当前未开启审核上架");
        }
        try {
            Map<String, Object> m = ArchiveStore.approveMarketplaceItem(id);
            if (m == null) throw new BizException(ErrorCode.NOT_FOUND, "对象不存在");
            String op = AdminAuth.requireLogin(session);
            AuditLogStore.record(op, "archive_approve", "archive", String.valueOf(id), "审核上架");
            return R.ok(m);
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 多店 / 投稿先审：超管驳回（ 可带 rejectReason） */
    @PostMapping("/{id:\\d+}/reject")
    public R<Map<String, Object>> reject(
            @PathVariable long id,
            @RequestBody(required = false) Map<String, Object> body,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        if (AppPolicy.SENSITIVE_CONFIRM) {
            Object mark = body == null ? null : body.get("confirm");
            boolean ok = Boolean.TRUE.equals(mark) || "true".equalsIgnoreCase(String.valueOf(mark));
            if (!ok) throw new BizException(ErrorCode.BAD_REQUEST, "请再次确认后再驳回");
        }
        if (!ArchiveStore.shopMarketplaceEnabled() && !ArchiveStore.publishReviewEnabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "当前未开启审核上架");
        }
        try {
            String reason = "";
            if (body != null && body.get("rejectReason") != null) {
                reason = String.valueOf(body.get("rejectReason"));
            } else if (body != null && body.get("reason") != null) {
                reason = String.valueOf(body.get("reason"));
            }
            Map<String, Object> m = ArchiveStore.rejectPublishItem(id, reason);
            if (m == null) throw new BizException(ErrorCode.NOT_FOUND, "对象不存在");
            String op = AdminAuth.requireLogin(session);
            AuditLogStore.record(op, "archive_reject", "archive", String.valueOf(id), "审核驳回");
            return R.ok(m);
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 资料相册审核 */
    @PostMapping("/{id:\\d+}/album-audit")
    public R<Map<String, Object>> albumAudit(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        String status = body == null || body.get("status") == null ? "" : String.valueOf(body.get("status"));
        try {
            Map<String, Object> m = ArchiveStore.setAlbumAuditStatus(id, status);
            if (m == null) throw new BizException(ErrorCode.NOT_FOUND, "对象不存在");
            String op = AdminAuth.requireLogin(session);
            AuditLogStore.record(op, "archive_album_audit", "archive", String.valueOf(id), "相册审核:" + status);
            return R.ok(m);
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
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
        if ("名称".equals(t) || "标题".equals(t) || "书名".equals(t)) return "title";
        if ("分类".equals(t)) return "category";
        if ("库存".equals(t) || "数量".equals(t)) return "stock";
        if ("标签".equals(t)) return "tags";
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
            case "harveston" -> "harvestOn";
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
