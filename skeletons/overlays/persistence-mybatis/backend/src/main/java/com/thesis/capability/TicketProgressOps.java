package com.thesis.capability;

import com.thesis.config.MybatisSupport;
import com.thesis.mapper.TicketMapper;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Ticket progress timeline helpers (package-private). */
final class TicketProgressOps {

    private TicketProgressOps() {}

    private static TicketMapper mapper() {
        return MybatisSupport.mapper(TicketMapper.class);
    }

    static List<Map<String, Object>> listProgress(long ticketId) {
        TicketStore.ensureProgressTable();
        if (TicketStore.PROGRESS == null || TicketStore.PROGRESS.isBlank()) return List.of();
        List<Map<String, Object>> rows = queryProgress(ticketId);
        if (rows.isEmpty()) {
            backfillProgressFromTicket(ticketId);
            rows = queryProgress(ticketId);
        }
        return rows;
    }

    static List<Map<String, Object>> queryProgress(long ticketId) {
        try {
            List<Map<String, Object>> raw = mapper().selectProgress(TicketStore.PROGRESS, ticketId);
            if (raw == null) return List.of();
            List<Map<String, Object>> out = new ArrayList<>();
            for (Map<String, Object> r : raw) {
                Map<String, Object> row = new LinkedHashMap<>();
                row.put("id", TicketSql.toLong(r.get("id")));
                row.put("ticketId", TicketSql.toLong(first(r, "ticketId", "ticket_id")));
                row.put("status", TicketSql.str(r.get("status")));
                row.put("operator", TicketSql.str(r.get("operator")));
                row.put("remark", TicketSql.str(r.get("remark")));
                row.put("createdAt", TicketSql.fmt(first(r, "createdAt", "created_at")));
                out.add(row);
            }
            return out;
        } catch (Exception e) {
            return List.of();
        }
    }

    /** 旧数据无流水时，按单据时间戳回填一次（各域同一套列，无分支）。 */
    static void backfillProgressFromTicket(long ticketId) {
        if (ticketId <= 0 || TicketStore.PROGRESS == null || TicketStore.PROGRESS.isBlank()) return;
        try {
            boolean withRating = TicketStore.hasColumn("rating");
            Map<String, Object> raw = mapper().selectTicketForBackfill(TicketStore.TICKET, ticketId, withRating);
            if (raw == null) return;
            String user = TicketSql.str(raw.get("username"));
            String st = TicketSql.str(raw.get("status"));
            String assignee = TicketSql.str(first(raw, "assigneeUsername", "assignee_username"));
            Timestamp applyAt = asTs(first(raw, "applyAt", "apply_at"));
            Timestamp approveAt = asTs(first(raw, "approveAt", "approve_at"));
            Timestamp returnAt = asTs(first(raw, "returnAt", "return_at"));
            if (applyAt != null) {
                insertProgressRow(ticketId, "pending", user, "用户提交", applyAt);
            }
            if (approveAt != null) {
                if ("rejected".equals(st)) {
                    insertProgressRow(ticketId, "rejected", TicketSql.blankTo(assignee, "admin"),
                            TicketCopy.stateLabel("rejected", "已驳回"), approveAt);
                } else if ("pending_mid".equals(st)) {
                    insertProgressRow(ticketId, "pending_mid", TicketSql.blankTo(assignee, "admin"),
                            TicketCopy.stateLabel("pending_mid", "初审通过"), approveAt);
                } else if ("pending_final".equals(st)) {
                    insertProgressRow(ticketId, "pending_final", TicketSql.blankTo(assignee, "admin"),
                            TicketCopy.stateLabel("pending_final", "复审通过"), approveAt);
                } else if (!"pending".equals(st)) {
                    insertProgressRow(ticketId, "approved", TicketSql.blankTo(assignee, "admin"),
                            TicketCopy.stateLabel("approved", "审核通过"), approveAt);
                }
            }
            if (returnAt != null) {
                boolean noShow = "overdue".equals(st) && TicketStore.noShowAfterEnd;
                String fin = noShow ? "overdue" : "returned";
                String tip = noShow
                        ? TicketCopy.stateLabel("overdue", "爽约")
                        : TicketCopy.stateLabel("returned", TicketCopy.verbLabel("return", "已完结"));
                insertProgressRow(ticketId, fin, TicketSql.blankTo(assignee, "system"), tip, returnAt);
            } else if ("overdue".equals(st) && TicketStore.noShowAfterEnd) {
                insertProgressRow(ticketId, "overdue", "system",
                        TicketCopy.stateLabel("overdue", "爽约"), Timestamp.valueOf(LocalDateTime.now()));
            } else if ("noshow".equals(st)) {
                insertProgressRow(ticketId, "overdue", "system",
                        TicketCopy.stateLabel("overdue", "爽约"), Timestamp.valueOf(LocalDateTime.now()));
            }
            Object ratingObj = first(raw, "rating");
            if (ratingObj instanceof Number rn && rn.intValue() > 0) {
                String tip = rn.intValue() + " 分";
                String note = TicketSql.str(first(raw, "ratingRemark", "rating_remark"));
                if (!note.isBlank()) tip = tip + " · " + note;
                Timestamp ratedAt = asTs(first(raw, "ratedAt", "rated_at"));
                if (ratedAt == null) ratedAt = Timestamp.valueOf(LocalDateTime.now());
                insertProgressRow(ticketId, "rated", user, tip, ratedAt);
            }
        } catch (Exception ignored) {
        }
    }

    static void insertProgressRow(
            long ticketId, String status, String operator, String remark, Timestamp at) {
        if (at == null) at = Timestamp.valueOf(LocalDateTime.now());
        mapper().insertProgress(
                TicketStore.PROGRESS,
                ticketId,
                status == null ? "" : status,
                operator == null ? "" : operator,
                remark == null ? "" : remark,
                at);
    }

    private static Object first(Map<String, Object> raw, String... keys) {
        for (String k : keys) {
            if (raw.containsKey(k) && raw.get(k) != null) return raw.get(k);
        }
        return null;
    }

    private static Timestamp asTs(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts;
        if (o instanceof LocalDateTime ldt) return Timestamp.valueOf(ldt);
        try {
            String s = String.valueOf(o);
            if (s.isBlank()) return null;
            if (s.length() >= 19) {
                return Timestamp.valueOf(LocalDateTime.parse(s.substring(0, 19), TicketSql.FMT));
            }
        } catch (Exception ignored) {
        }
        return null;
    }
}
