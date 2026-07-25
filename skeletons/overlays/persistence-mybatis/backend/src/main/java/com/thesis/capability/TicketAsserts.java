package com.thesis.capability;

import com.thesis.config.MybatisSupport;
import com.thesis.mapper.TicketMapper;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Apply-time guards / normalize helpers (package-private). */
final class TicketAsserts {

    private TicketAsserts() {}

    private static TicketMapper mapper() {
        return MybatisSupport.mapper(TicketMapper.class);
    }

    static String normalizeAttach(String attachUrl) {
        String attach = attachUrl == null ? "" : attachUrl.trim();
        if (TicketStore.requireAttach && attach.isBlank()) {
            throw new IllegalStateException("请上传附件后再提交");
        }
        if (attach.length() > 255) attach = attach.substring(0, 255);
        return attach;
    }

    static void assertUnderActiveLimit(String username) {
        int active = mapper().countActiveByUser(TicketStore.TICKET, username, TicketStore.allowMultiTicket);
        if (active >= TicketStore.maxActive()) {
            int lim = TicketStore.maxActive();
            throw new IllegalStateException(
                    TicketStore.allowMultiTicket
                            ? "待审核回复不得超过 " + lim + " 条，请稍后再发"
                            : "同时进行中的单据不得超过 " + lim + " 条");
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
        Map<String, Object> q = new LinkedHashMap<>();
        q.put("ticketTable", TicketStore.TICKET);
        q.put("itemTable", ArchiveStore.itemTable());
        q.put("itemFk", TicketStore.itemFkColumn());
        q.put("username", username);
        q.put("itemId", itemId);
        q.put("mutexCode", code);
        List<String> titles = mapper().selectMutexConflictTitles(q);
        if (titles != null && !titles.isEmpty()) {
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
        Map<String, Object> q = new LinkedHashMap<>();
        q.put("ticketTable", TicketStore.TICKET);
        q.put("itemTable", ArchiveStore.itemTable());
        q.put("itemFk", TicketStore.itemFkColumn());
        q.put("username", username);
        q.put("categoryId", categoryId);
        int n = mapper().countCategoryActive(q);
        if (n >= TicketStore.categoryLimit) {
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
        Map<String, Object> q = new LinkedHashMap<>();
        q.put("ticketTable", TicketStore.TICKET);
        q.put("itemTable", ArchiveStore.itemTable());
        q.put("itemFk", TicketStore.itemFkColumn());
        q.put("username", username);
        q.put("itemId", itemId);
        List<Map<String, Object>> occupied = mapper().selectTimeConflictOccupied(q);
        if (occupied == null) return;
        for (Map<String, Object> row : occupied) {
            Object startObj = first(row, "start_at", "startAt");
            Object endObj = first(row, "end_at", "endAt");
            if (startObj == null || endObj == null) continue;
            LocalDateTime oldStart = toLdt(startObj);
            LocalDateTime oldEnd = toLdt(endObj);
            if (oldStart == null || oldEnd == null) continue;
            if (newStart.isBefore(oldEnd) && oldStart.isBefore(newEnd)) {
                throw new IllegalStateException(
                        "时间冲突：与「" + first(row, "title") + "」（"
                                + oldStart.format(TicketSql.FMT) + " ~ " + oldEnd.format(TicketSql.FMT) + "）重叠");
            }
        }
    }

    private static Object first(Map<String, Object> raw, String... keys) {
        for (String k : keys) {
            if (raw.containsKey(k) && raw.get(k) != null) return raw.get(k);
        }
        return null;
    }

    private static LocalDateTime toLdt(Object o) {
        if (o instanceof Timestamp ts) return ts.toLocalDateTime();
        if (o instanceof LocalDateTime ldt) return ldt;
        try {
            String s = String.valueOf(o);
            if (s.length() >= 19) return LocalDateTime.parse(s.substring(0, 19), TicketSql.FMT);
        } catch (Exception ignored) {
        }
        return null;
    }
}
