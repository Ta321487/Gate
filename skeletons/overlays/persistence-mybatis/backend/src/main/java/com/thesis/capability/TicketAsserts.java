package com.thesis.capability;

import com.thesis.config.MybatisSupport;
import com.thesis.mapper.TicketMapper;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Apply-time guards / normalize helpers (package-private). */
final class TicketAsserts {

    private TicketAsserts() {}

    /** MyBatis 叠层统一走 Mapper；不得回退 JDBC 直连入口。 */
    private static TicketMapper mapper() {
        return MybatisSupport.mapper(TicketMapper.class);
    }

    /** 行值可能是 Timestamp / LocalDateTime / 字符串，统一成 LocalDateTime。 */
    private static LocalDateTime asDateTime(Object raw) {
        if (raw == null) return null;
        if (raw instanceof LocalDateTime ldt) return ldt;
        if (raw instanceof Timestamp ts) return ts.toLocalDateTime();
        String s = String.valueOf(raw).trim();
        if (s.isBlank() || "null".equalsIgnoreCase(s)) return null;
        if (s.contains("T")) s = s.replace('T', ' ');
        return LocalDateTime.parse(s.substring(0, Math.min(19, s.length())), TicketSql.FMT);
    }

    private static Map<String, Object> ticketQuery(long itemId) {
        Map<String, Object> q = new HashMap<>();
        q.put("ticketTable", TicketStore.TICKET);
        q.put("itemTable", ArchiveStore.itemTable());
        q.put("itemFk", TicketStore.itemFkColumn());
        q.put("itemId", itemId);
        return q;
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
        // 多开单（跟帖）：只限制待审数量，已展示的回复不占额度
        int active = mapper().countActiveByUser(
                TicketStore.TICKET, username, TicketStore.allowMultiTicket);
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
            String s = String.valueOf(raw).trim();
            if (s.contains("T")) s = s.replace('T', ' ');
            LocalDateTime deadline;
            if (s.length() == 10) {
                // 纯日期：当日仍可报，过了当天才拦
                deadline = LocalDateTime.parse(s + "T23:59:59");
            } else {
                deadline = LocalDateTime.parse(s.substring(0, Math.min(19, s.length())), TicketSql.FMT);
            }
            if (LocalDateTime.now().isAfter(deadline)) {
                throw new IllegalStateException("已过" + TicketCopy.APPLY_DEADLINE_LABEL + "时间");
            }
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("报名/申请截止时间无效", e);
        }
    }

    /** 评教开放窗口：仅在档案 evalOpenOn～evalCloseOn 内可提交。 */
    static void assertEvalOpenWindow(Map<String, Object> item) {
        if (!TicketStore.allowEvalOpenWindow || item == null) return;
        String openRaw = TicketSql.str(item.get("evalOpenOn")).trim();
        String closeRaw = TicketSql.str(item.get("evalCloseOn")).trim();
        if (openRaw.isBlank() && closeRaw.isBlank()) return;
        try {
            java.time.LocalDate today = java.time.LocalDate.now();
            if (!openRaw.isBlank()) {
                String s = openRaw.length() >= 10 ? openRaw.substring(0, 10) : openRaw;
                java.time.LocalDate open = java.time.LocalDate.parse(s);
                if (today.isBefore(open)) {
                    String deny = TicketStore.evalOpenWindowDenyMessage;
                    throw new IllegalStateException(
                            deny == null || deny.isBlank() ? "当前不在评教开放时间内，暂不可提交。" : deny);
                }
            }
            if (!closeRaw.isBlank()) {
                String s = closeRaw.length() >= 10 ? closeRaw.substring(0, 10) : closeRaw;
                java.time.LocalDate close = java.time.LocalDate.parse(s);
                if (today.isAfter(close)) {
                    String deny = TicketStore.evalOpenWindowDenyMessage;
                    throw new IllegalStateException(
                            deny == null || deny.isBlank() ? "当前不在评教开放时间内，暂不可提交。" : deny);
                }
            }
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("评教开放日/截止日无效", e);
        }
    }

    /** 通行码过期后不可再出示或签到（软闸，不改审批状态）。 */
    static void assertPassNotExpired(Map<String, Object> ticket) {
        if (!TicketStore.allowPassExpire || ticket == null) return;
        Object raw = ticket.get("passExpireAt");
        if (raw == null || String.valueOf(raw).isBlank()) return;
        try {
            String s = String.valueOf(raw).trim().replace('T', ' ');
            LocalDateTime expire;
            if (s.length() == 10) {
                expire = LocalDateTime.parse(s + "T23:59:59");
            } else {
                expire = LocalDateTime.parse(s.substring(0, Math.min(19, s.length())), TicketSql.FMT);
            }
            if (LocalDateTime.now().isAfter(expire)) {
                throw new IllegalStateException("通行码已失效，不可再出示或签到");
            }
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("通行码有效期无效", e);
        }
    }

    /** 已下架或已过开始时间不可再申请（拼车出发、活动开场等）。 */
    static void assertItemOpen(Map<String, Object> item) {
        if (item == null) return;
        String st = String.valueOf(item.get("status"));
        if ("unavailable".equals(st)) {
            throw new IllegalStateException("该对象已下架或不可申请");
        }
        // 线路报名等：档案 stage 已关闭时禁止再报（与 status 双保险）
        // 设备借用：维修中/下架不可借；驿站：异常件不可取
        Object stageObj = item.get("stage");
        if (stageObj != null) {
            String stage = String.valueOf(stageObj).trim();
            if ("满员".equals(stage) || "已出团".equals(stage) || "下架".equals(stage)) {
                throw new IllegalStateException(
                        "满员".equals(stage) ? "该线路已满员，不可再报名"
                                : ("已出团".equals(stage) ? "该线路已出团，不可再报名"
                                : "该线路已下架，不可再报名"));
            }
            if ("维修中".equals(stage)) {
                throw new IllegalStateException("该设备维修中，暂不可借用");
            }
            if ("损坏".equals(stage) || "误领".equals(stage) || "拒收".equals(stage)) {
                throw new IllegalStateException("该包裹为异常件（" + stage + "），不可办理取件");
            }
        }
        if (!ArchiveStore.hasStartAt() && !ArchiveStore.hasEndAt()) return;
        if (ArchiveStore.isScheduleClosed(item)) {
            throw new IllegalStateException(
                    ArchiveStore.hasEndAt() ? "查寝/办理窗口已结束，不可再申请" : "已过开始时间，不可再申请");
        }
    }

    /** 同互斥码的其它进行中单据不可并存 */
    static void assertNoMutexConflict(String username, long itemId, Map<String, Object> item) {
        if (!TicketStore.checkMutex || !ArchiveStore.hasMutexCode()) return;
        String code = TicketSql.str(item.get("mutexCode")).trim();
        if (code.isBlank()) return;
        Map<String, Object> q = ticketQuery(itemId);
        q.put("username", username);
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
            String raw = TicketSql.str(cid).trim();
            if (raw.isBlank() || "null".equalsIgnoreCase(raw)) return;
            try {
                categoryId = Long.parseLong(raw);
            } catch (Exception e) {
                throw new IllegalStateException("分类无效，无法校验门数上限", e);
            }
        }
        if (categoryId <= 0) return;
        Map<String, Object> q = new HashMap<>();
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
            throw new IllegalStateException("时段时间无效，无法校验冲突", e);
        }
        if (!newEnd.isAfter(newStart)) {
            throw new IllegalStateException("时段配置无效：结束时间须晚于开始时间");
        }
        Map<String, Object> q = ticketQuery(itemId);
        q.put("username", username);
        List<Map<String, Object>> occupied = mapper().selectTimeConflictOccupied(q);
        for (Map<String, Object> row : (occupied == null ? List.<Map<String, Object>>of() : occupied)) {
            LocalDateTime oldStart = asDateTime(
                    row.get("start_at") != null ? row.get("start_at") : row.get("startAt"));
            LocalDateTime oldEnd = asDateTime(
                    row.get("end_at") != null ? row.get("end_at") : row.get("endAt"));
            if (oldStart == null || oldEnd == null) continue;
            if (newStart.isBefore(oldEnd) && oldStart.isBefore(newEnd)) {
                throw new IllegalStateException(
                        "时间冲突：与「" + row.get("title") + "」（"
                                + oldStart.format(TicketSql.FMT) + " ~ " + oldEnd.format(TicketSql.FMT) + "）重叠");
            }
        }
    }


}
