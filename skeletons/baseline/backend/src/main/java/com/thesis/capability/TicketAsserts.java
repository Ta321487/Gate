package com.thesis.capability;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Apply-time guards / normalize helpers (package-private). */
final class TicketAsserts {

    private TicketAsserts() {}

    static String normalizeAttach(String attachUrl) {
        String attach = attachUrl == null ? "" : attachUrl.trim();
        if (TicketStore.requireAttach && attach.isBlank()) {
            throw new IllegalStateException("请上传附件后再提交");
        }
        if (attach.length() > 255) attach = attach.substring(0, 255);
        return attach;
    }

    static void assertUnderActiveLimit(String username) {
        // 多开单（跟帖）：只限制待审数量，已展示的回复不占额度
        String statuses = TicketStore.allowMultiTicket
                ? "('pending','pending_final')"
                : "('pending','pending_final','approved','overdue')";
        Integer active = TicketSql.db().queryForObject(
                "SELECT COUNT(*) FROM " + TicketStore.TICKET + " WHERE username=? AND status IN " + statuses,
                Integer.class, username);
        if (active != null && active >= TicketStore.MAX_ACTIVE) {
            throw new IllegalStateException(
                    TicketStore.allowMultiTicket
                            ? "待审核回复不得超过 " + TicketStore.MAX_ACTIVE + " 条，请稍后再发"
                            : "同时进行中的单据不得超过 " + TicketStore.MAX_ACTIVE + " 条");
        }
    }

    static void assertApplyDeadline(Map<String, Object> item) {
        if (!ArchiveStore.hasApplyDeadline()) return;
        Object raw = item.get("applyDeadlineAt");
        if (raw == null || String.valueOf(raw).isBlank()) return;
        try {
            LocalDateTime deadline = LocalDateTime.parse(String.valueOf(raw).substring(0, 19), TicketSql.FMT);
            if (LocalDateTime.now().isAfter(deadline)) {
                throw new IllegalStateException("已过" + TicketCopy.APPLY_DEADLINE_LABEL + "时间");
            }
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception ignored) {
            // 解析失败则不拦截
        }
    }

    /** 同互斥码的其它进行中单据不可并存 */
    static void assertNoMutexConflict(String username, long itemId, Map<String, Object> item) {
        if (!TicketStore.checkMutex || !ArchiveStore.hasMutexCode()) return;
        String code = TicketSql.str(item.get("mutexCode")).trim();
        if (code.isBlank()) return;
        String itemTable = ArchiveStore.itemTable();
        List<String> titles = TicketSql.db().query(
                "SELECT i.title FROM " + TicketStore.TICKET + " t "
                        + "JOIN " + itemTable + " i ON t." + TicketStore.itemFkColumn() + "=i.id "
                        + "WHERE t.username=? AND t." + TicketStore.itemFkColumn() + "<>? "
                        + "AND t.status IN ('pending','pending_final','approved','overdue') "
                        + "AND i.mutex_code=? AND i.mutex_code<>''",
                (rs, i) -> rs.getString(1),
                username, itemId, code);
        if (!titles.isEmpty()) {
            throw new IllegalStateException(
                    "互斥冲突：与「" + titles.get(0) + "」同属互斥组「" + code + "」，不可同时选择");
        }
    }

    /** 同一分类下进行中单据不得超过 TicketStore.categoryLimit */
    static void assertCategoryLimit(String username, Map<String, Object> item) {
        if (TicketStore.categoryLimit <= 0) return;
        long categoryId = 0L;
        Object cid = item.get("categoryId");
        if (cid instanceof Number n) categoryId = n.longValue();
        else {
            try {
                categoryId = Long.parseLong(TicketSql.str(cid));
            } catch (Exception ignored) {
                return;
            }
        }
        if (categoryId <= 0) return;
        String itemTable = ArchiveStore.itemTable();
        Integer n = TicketSql.db().queryForObject(
                "SELECT COUNT(*) FROM " + TicketStore.TICKET + " t "
                        + "JOIN " + itemTable + " i ON t." + TicketStore.itemFkColumn() + "=i.id "
                        + "WHERE t.username=? AND t.status IN ('pending','pending_final','approved','overdue') "
                        + "AND i.category_id=?",
                Integer.class, username, categoryId);
        if (n != null && n >= TicketStore.categoryLimit) {
            String catName = TicketSql.str(item.get("categoryName"));
            String hint = catName.isBlank() ? "该分类" : ("分类「" + catName + "」");
            throw new IllegalStateException(
                    hint + "最多可选 " + TicketStore.categoryLimit + " 门，请先退选后再申请");
        }
    }

    /** 区间相交：newStart < oldEnd && oldStart < newEnd */
    static void assertNoTimeConflict(String username, long itemId, Map<String, Object> item) {
        if (!TicketStore.checkTimeConflict || !ArchiveStore.hasScheduleColumns()) return;
        Object ns = item.get("startAt");
        Object ne = item.get("endAt");
        if (ns == null || ne == null || String.valueOf(ns).isBlank() || String.valueOf(ne).isBlank()) return;
        LocalDateTime newStart;
        LocalDateTime newEnd;
        try {
            newStart = LocalDateTime.parse(String.valueOf(ns).substring(0, 19), TicketSql.FMT);
            newEnd = LocalDateTime.parse(String.valueOf(ne).substring(0, 19), TicketSql.FMT);
        } catch (Exception e) {
            return;
        }
        if (!newEnd.isAfter(newStart)) {
            throw new IllegalStateException("时段配置无效：结束时间须晚于开始时间");
        }
        String itemTable = ArchiveStore.itemTable();
        List<Map<String, Object>> occupied = TicketSql.db().query(
                "SELECT i.title AS title, i.start_at AS start_at, i.end_at AS end_at FROM " + TicketStore.TICKET + " t "
                        + "JOIN " + itemTable + " i ON t." + TicketStore.itemFkColumn() + "=i.id "
                        + "WHERE t.username=? AND t." + TicketStore.itemFkColumn()
                        + "<>? AND t.status IN ('pending','pending_final','approved','overdue') "
                        + "AND i.start_at IS NOT NULL AND i.end_at IS NOT NULL",
                (rs, i) -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("title", rs.getString("title"));
                    row.put("start", rs.getTimestamp("start_at").toLocalDateTime());
                    row.put("end", rs.getTimestamp("end_at").toLocalDateTime());
                    return row;
                },
                username, itemId);
        for (Map<String, Object> row : occupied) {
            LocalDateTime oldStart = (LocalDateTime) row.get("start");
            LocalDateTime oldEnd = (LocalDateTime) row.get("end");
            if (newStart.isBefore(oldEnd) && oldStart.isBefore(newEnd)) {
                throw new IllegalStateException(
                        "时间冲突：与「" + row.get("title") + "」（"
                                + oldStart.format(TicketSql.FMT) + " ~ " + oldEnd.format(TicketSql.FMT) + "）重叠");
            }
        }
    }


}
