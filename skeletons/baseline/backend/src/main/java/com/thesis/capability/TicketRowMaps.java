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
        m.put("checkedInAt", TicketSql.fmt(TicketSql.safeTs(rs, "checked_in_at")));

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
            } else if (item != null) {
                m.put("startAt", item.get("startAt"));
                m.put("endAt", item.get("endAt"));
                m.put("applyDeadlineAt", item.get("applyDeadlineAt"));
            }
        }
        return m;
    }
}
