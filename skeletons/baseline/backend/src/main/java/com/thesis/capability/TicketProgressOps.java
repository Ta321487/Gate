package com.thesis.capability;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Ticket progress timeline helpers (package-private). */
final class TicketProgressOps {

    private TicketProgressOps() {}

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
            return TicketSql.db().query(
                    "SELECT * FROM `" + TicketStore.PROGRESS + "` WHERE ticket_id=? ORDER BY id",
                    (rs, i) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("id", rs.getLong("id"));
                        row.put("ticketId", rs.getLong("ticket_id"));
                        row.put("status", rs.getString("status"));
                        row.put("operator", rs.getString("operator"));
                        row.put("remark", rs.getString("remark"));
                        row.put("createdAt", TicketSql.fmt(rs.getTimestamp("created_at")));
                        return row;
                    },
                    ticketId);
        } catch (Exception e) {
            return List.of();
        }
    }

    /** 旧数据无流水时，按单据时间戳回填一次（各域同一套列，无分支）。 */
    static void backfillProgressFromTicket(long ticketId) {
        if (ticketId <= 0 || TicketStore.PROGRESS == null || TicketStore.PROGRESS.isBlank()) return;
        try {
            String cols = "username, status, apply_at, approve_at, return_at, assignee_username";
            boolean withRating = TicketStore.hasColumn("rating");
            if (withRating) cols += ", rating, rating_remark, rated_at";
            List<Map<String, Object>> tickets = TicketSql.db().query(
                    "SELECT " + cols + " FROM " + TicketStore.TICKET + " WHERE id=?",
                    (rs, i) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("username", rs.getString("username"));
                        row.put("status", rs.getString("status"));
                        row.put("applyAt", rs.getTimestamp("apply_at"));
                        row.put("approveAt", TicketSql.safeTs(rs, "approve_at"));
                        row.put("returnAt", TicketSql.safeTs(rs, "return_at"));
                        row.put("assignee", TicketSql.safeStr(rs, "assignee_username"));
                        if (withRating) {
                            Integer rating = null;
                            int r = rs.getInt("rating");
                            if (!rs.wasNull()) rating = r;
                            row.put("rating", rating);
                            row.put("ratingRemark", TicketSql.safeStr(rs, "rating_remark"));
                            row.put("ratedAt", TicketSql.safeTs(rs, "rated_at"));
                        }
                        return row;
                    },
                    ticketId);
            if (tickets.isEmpty()) return;
            Map<String, Object> t = tickets.get(0);
            String user = String.valueOf(t.getOrDefault("username", ""));
            String st = String.valueOf(t.getOrDefault("status", ""));
            String assignee = String.valueOf(t.getOrDefault("assignee", ""));
            Timestamp applyAt = (Timestamp) t.get("applyAt");
            Timestamp approveAt = (Timestamp) t.get("approveAt");
            Timestamp returnAt = (Timestamp) t.get("returnAt");
            if (applyAt != null) {
                insertProgressRow(ticketId, "pending", user, "用户提交", applyAt);
            }
            if (approveAt != null) {
                if ("rejected".equals(st)) {
                    insertProgressRow(ticketId, "rejected", TicketSql.blankTo(assignee, "admin"),
                            TicketCopy.stateLabel("rejected", "已驳回"), approveAt);
                } else if (!"pending".equals(st) && !"pending_final".equals(st)) {
                    insertProgressRow(ticketId, "approved", TicketSql.blankTo(assignee, "admin"),
                            TicketCopy.stateLabel("approved", "审核通过"), approveAt);
                } else if ("pending_final".equals(st)) {
                    insertProgressRow(ticketId, "pending_final", TicketSql.blankTo(assignee, "admin"),
                            TicketCopy.stateLabel("pending_final", "初审通过"), approveAt);
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
            Object ratingObj = t.get("rating");
            if (ratingObj instanceof Number rn && rn.intValue() > 0) {
                String tip = rn.intValue() + " 分";
                String note = TicketSql.str(t.get("ratingRemark"));
                if (!note.isBlank()) tip = tip + " · " + note;
                Timestamp ratedAt = (Timestamp) t.get("ratedAt");
                if (ratedAt == null) ratedAt = Timestamp.valueOf(LocalDateTime.now());
                insertProgressRow(ticketId, "rated", user, tip, ratedAt);
            }
        } catch (Exception ignored) {
        }
    }

    static void insertProgressRow(
            long ticketId, String status, String operator, String remark, Timestamp at) {
        if (at == null) at = Timestamp.valueOf(LocalDateTime.now());
        TicketSql.db().update(
                "INSERT INTO `" + TicketStore.PROGRESS + "` (ticket_id,status,operator,remark,created_at) VALUES (?,?,?,?,?)",
                ticketId,
                status == null ? "" : status,
                operator == null ? "" : operator,
                remark == null ? "" : remark,
                at);
    }

    /** 认领/领用：登记领取 */

}
