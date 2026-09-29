package com.thesis.capability;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

final class TicketRowMaps {

    private TicketRowMaps() {}

    static Map<String, Object> load(long id) {
        List<Map<String, Object>> list = TicketSql.db().query(
                "SELECT * FROM " + TicketStore.ticketTable() + " WHERE id=?", (rs, i) -> mapRow(rs), id);
        return list.isEmpty() ? null : list.get(0);
    }

    static Map<String, Object> mapRow(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("status", rs.getString("status"));
        m.put("applyAt", TicketSql.fmt(rs.getTimestamp("apply_at")));
        m.put("approveAt", TicketSql.fmt(TicketSql.safeTs(rs, "approve_at")));
        m.put("returnAt", TicketSql.fmt(TicketSql.safeTs(rs, "return_at")));
        m.put("remark", TicketSql.safeStr(rs, "remark"));
        m.put("assigneeUsername", TicketSql.safeStr(rs, "assignee_username"));
        m.put("attachUrl", TicketSql.safeStr(rs, "attach_url"));
        Integer rating = null;
        try {
            int r = rs.getInt("rating");
            if (!rs.wasNull()) rating = r;
        } catch (Exception ignored) {
        }
        m.put("rating", rating);
        m.put("ratingRemark", TicketSql.safeStr(rs, "rating_remark"));
        m.put("ratedAt", TicketSql.fmt(TicketSql.safeTs(rs, "rated_at")));
        m.put("ratingDimsJson", TicketSql.safeStr(rs, "rating_dims_json"));
        try {
            int anon = rs.getInt("rating_anonymous");
            m.put("ratingAnonymous", !rs.wasNull() && anon == 1);
        } catch (Exception ignored) {
            m.put("ratingAnonymous", false);
        }
        // 演示匿名：管理端列表隐藏提交人用户名
        if (Boolean.TRUE.equals(m.get("ratingAnonymous")) && rating != null) {
            m.put("displayUsername", "匿名同学");
        }
        m.put("checkedInAt", TicketSql.fmt(TicketSql.safeTs(rs, "checked_in_at")));
        m.put("passCode", TicketSql.safeStr(rs, "pass_code"));
        int renewCount = 0;
        try {
            renewCount = rs.getInt("renew_count");
            if (rs.wasNull()) renewCount = 0;
        } catch (Exception ignored) {
            renewCount = 0;
        }
        m.put("renewCount", renewCount);
        m.put("holdExpireAt", TicketSql.fmt(TicketSql.safeTs(rs, "hold_expire_at")));
        m.put("dueSoonNotifiedAt", TicketSql.fmt(TicketSql.safeTs(rs, "due_soon_notified_at")));
        int everOverdue = 0;
        try {
            everOverdue = rs.getInt("ever_overdue");
            if (rs.wasNull()) everOverdue = 0;
        } catch (Exception ignored) {
            everOverdue = 0;
        }
        m.put("everOverdue", everOverdue);

        if (TicketStore.mode() == TicketStore.Mode.STANDALONE) {
            m.put("title", TicketSql.safeStr(rs, "title"));
            m.put("location", TicketSql.safeStr(rs, "location"));
            m.put("typeId", TicketSql.safeLong(rs, "type_id"));
            m.put("roomId", TicketSql.safeLong(rs, "room_id"));
            m.put("priority", TicketSql.safeStr(rs, "priority"));
            m.put("contactPhone", TicketSql.safeStr(rs, "contact_phone"));
            long typeId = TicketSql.safeLong(rs, "type_id");
            m.put("typeName", typeId > 0 ? TicketLookupStore.typeName(typeId) : "");
            m.put("itemTitle", TicketSql.safeStr(rs, "title"));
            m.put("bookTitle", TicketSql.safeStr(rs, "title"));
            m.put("bookId", 0L);
            m.put("itemId", 0L);
            m.put("dueAt", null);
            m.put("fineYuan", 0.0);
            m.put("remindedAt", null);
            m.put("remindMsg", "");
        } else {
            long bookId = rs.getLong(TicketStore.itemFkColumn());
            m.put("bookId", bookId);
            m.put("itemId", bookId);
            m.put("dueAt", TicketSql.fmt(TicketSql.safeTs(rs, "due_at")));
            m.put("fineYuan", TicketSql.safeDouble(rs, "fine_yuan"));
            m.put("fineStatus", TicketSql.safeStr(rs, "fine_status"));
            m.put("remindedAt", TicketSql.fmt(TicketSql.safeTs(rs, "reminded_at")));
            m.put("remindMsg", TicketSql.safeStr(rs, "remind_msg"));
            m.put("pickupAt", TicketSql.fmt(TicketSql.safeTs(rs, "pickup_at")));
            m.put("pickupPlace", TicketSql.safeStr(rs, "pickup_place"));
            m.put("contactChannel", TicketSql.safeStr(rs, "contact_channel"));
            m.put("nextFollowAt", TicketSql.fmt(TicketSql.safeTs(rs, "next_follow_at")));
            try {
                int aq = rs.getInt("actual_qty");
                if (!rs.wasNull()) m.put("actualQty", aq);
            } catch (Exception ignored) {
            }
            int qty = 1;
            try {
                int q = rs.getInt("qty");
                if (!rs.wasNull() && q > 0) qty = q;
            } catch (Exception ignored) {
            }
            m.put("qty", qty);
            Map<String, Object> item = ArchiveStore.getItemRaw(bookId);
            m.put("bookTitle", item == null ? "" : item.get("title"));
            m.put("itemTitle", item == null ? "" : item.get("title"));
            m.put("title", item == null ? "" : TicketSql.str(item.get("title")));
            // archive 域：列表「类型/地点」列复用启事字段（失物 itemKind+isbn；图书则为分类+ISBN 等）
            if (item != null) {
                String kind = TicketSql.str(item.get("itemKind")).trim();
                String cat = TicketSql.str(item.get("categoryName")).trim();
                m.put("typeName", !kind.isBlank() ? kind : cat);
                m.put("location", TicketSql.str(item.get("isbn")));
                m.put("author", TicketSql.str(item.get("author")));
                m.put("categoryName", cat);
                m.put("itemKind", kind);
                m.put("isbn", TicketSql.str(item.get("isbn")));
            } else {
                m.put("typeName", "");
                m.put("location", "");
            }
            String periodStart = TicketSql.fmt(TicketSql.safeTs(rs, "period_start"));
            String periodEnd = TicketSql.fmt(TicketSql.safeTs(rs, "period_end"));
            if (periodStart != null || periodEnd != null) {
                m.put("periodStart", periodStart);
                m.put("periodEnd", periodEnd);
                m.put("startAt", periodStart);
                m.put("endAt", periodEnd);
                int leaveDays = 0;
                try {
                    Object rawLeaveDays = rs.getObject("leave_days");
                    if (rawLeaveDays instanceof Number num) leaveDays = num.intValue();
                } catch (Exception ignored) {
                    // 旧库无 leave_days 列：按起止回算
                }
                if (leaveDays <= 0) leaveDays = daysBetweenInclusive(periodStart, periodEnd);
                if (leaveDays > 0) m.put("leaveDays", leaveDays);
            } else if (item != null) {
                m.put("startAt", item.get("startAt"));
                m.put("endAt", item.get("endAt"));
                m.put("applyDeadlineAt", item.get("applyDeadlineAt"));
            }
        }
        int weekNo = 0;
        try {
            Object rawWeek = rs.getObject("week_no");
            if (rawWeek instanceof Number num) weekNo = num.intValue();
        } catch (Exception ignored) {
            // 旧库无 week_no 列：不展示周次
        }
        if (weekNo > 0) m.put("weekNo", weekNo);
        try {
            Object rawPlace = rs.getObject("interview_place");
            if (rawPlace != null) {
                String place = String.valueOf(rawPlace).trim();
                if (!place.isEmpty()) m.put("interviewPlace", place);
            }
        } catch (Exception ignored) {
            // 旧库无 interview_place 列：不展示面试地点
        }
        try {
            String pn = TicketSql.safeStr(rs, "proxy_name");
            if (pn != null && !pn.isBlank()) m.put("proxyName", pn);
        } catch (Exception ignored) {
        }
        try {
            String pp = TicketSql.safeStr(rs, "proxy_phone");
            if (pp != null && !pp.isBlank()) m.put("proxyPhone", pp);
        } catch (Exception ignored) {
        }
        try {
            String er = TicketSql.safeStr(rs, "exception_reason");
            if (er != null && !er.isBlank()) m.put("exceptionReason", er);
        } catch (Exception ignored) {
        }
        try {
            String dn = TicketSql.safeStr(rs, "damage_claim_note");
            if (dn != null && !dn.isBlank()) m.put("damageClaimNote", dn);
        } catch (Exception ignored) {
        }
        try {
            double dep = TicketSql.safeDouble(rs, "deposit_yuan");
            if (dep > 0) m.put("depositYuan", dep);
        } catch (Exception ignored) {
        }
        try {
            int ack = rs.getInt("notice_ack");
            if (!rs.wasNull()) m.put("noticeAck", ack == 1);
        } catch (Exception ignored) {
        }
        try {
            String peer = TicketSql.safeStr(rs, "peer_username");
            if (peer != null && !peer.isBlank()) m.put("peerUsername", peer);
        } catch (Exception ignored) {
        }
        try {
            int pack = rs.getInt("peer_ack");
            if (!rs.wasNull()) m.put("peerAck", pack == 1);
        } catch (Exception ignored) {
        }
        try {
            String pno = TicketSql.safeStr(rs, "project_no");
            if (pno != null && !pno.isBlank()) m.put("projectNo", pno);
        } catch (Exception ignored) {
        }
        try {
            String pref = TicketSql.safeStr(rs, "procure_ref_no");
            if (pref != null && !pref.isBlank()) m.put("procureRefNo", pref);
        } catch (Exception ignored) {
        }
        return m;
    }

    /** 请假等起止（含首尾）的自然日天数；解析失败返回 0。 */
    private static int daysBetweenInclusive(String start, String end) {
        if (start == null || end == null) return 0;
        try {
            java.time.LocalDate a = java.time.LocalDate.parse(start.substring(0, 10));
            java.time.LocalDate b = java.time.LocalDate.parse(end.substring(0, 10));
            return (int) (java.time.temporal.ChronoUnit.DAYS.between(a, b) + 1);
        } catch (Exception e) {
            return 0;
        }
    }
}
