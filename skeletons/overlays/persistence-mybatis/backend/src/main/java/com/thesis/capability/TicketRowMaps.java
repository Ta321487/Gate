package com.thesis.capability;

import com.thesis.config.MybatisSupport;
import com.thesis.mapper.TicketMapper;

import java.util.LinkedHashMap;
import java.util.Map;

final class TicketRowMaps {

    private TicketRowMaps() {}

    private static TicketMapper mapper() {
        return MybatisSupport.mapper(TicketMapper.class);
    }

    static Map<String, Object> load(long id) {
        Map<String, Object> raw = mapper().selectById(TicketStore.ticketTable(), id);
        return raw == null ? null : shape(raw);
    }

    /** MyBatis Map（snake / camel）→ API camelCase。 */
    static Map<String, Object> shape(Map<String, Object> raw) {
        if (raw == null) return null;
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", num(raw.get("id")));
        m.put("username", str(raw.get("username")));
        m.put("status", str(raw.get("status")));
        m.put("applyAt", fmt(first(raw, "applyAt", "apply_at")));
        m.put("approveAt", fmt(first(raw, "approveAt", "approve_at")));
        m.put("returnAt", fmt(first(raw, "returnAt", "return_at")));
        m.put("remark", str(first(raw, "remark")));
        m.put("assigneeUsername", str(first(raw, "assigneeUsername", "assignee_username")));
        m.put("attachUrl", str(first(raw, "attachUrl", "attach_url")));
        Integer rating = null;
        Object ratingObj = first(raw, "rating");
        if (ratingObj != null && !"".equals(String.valueOf(ratingObj))) {
            try {
                rating = (int) num(ratingObj);
            } catch (Exception ignored) {
            }
        }
        m.put("rating", rating);
        m.put("ratingRemark", str(first(raw, "ratingRemark", "rating_remark")));
        m.put("ratedAt", fmt(first(raw, "ratedAt", "rated_at")));
        m.put("ratingDimsJson", str(first(raw, "ratingDimsJson", "rating_dims_json")));
        Object anonObj = first(raw, "ratingAnonymous", "rating_anonymous");
        boolean anon = false;
        if (anonObj != null) {
            String a = String.valueOf(anonObj);
            anon = "1".equals(a) || "true".equalsIgnoreCase(a);
        }
        m.put("ratingAnonymous", anon);
        if (anon && rating != null) {
            m.put("displayUsername", "匿名同学");
        }
        m.put("checkedInAt", fmt(first(raw, "checkedInAt", "checked_in_at")));

        if (TicketStore.mode() == TicketStore.Mode.STANDALONE) {
            m.put("title", str(first(raw, "title")));
            m.put("location", str(first(raw, "location")));
            long typeId = num(first(raw, "typeId", "type_id"));
            long roomId = num(first(raw, "roomId", "room_id"));
            m.put("typeId", typeId);
            m.put("roomId", roomId);
            m.put("priority", str(first(raw, "priority")));
            m.put("contactPhone", str(first(raw, "contactPhone", "contact_phone")));
            m.put("typeName", typeId > 0 ? TicketLookupStore.typeName(typeId) : "");
            m.put("itemTitle", str(first(raw, "title")));
            m.put("bookTitle", str(first(raw, "title")));
            m.put("bookId", 0L);
            m.put("itemId", 0L);
            m.put("dueAt", null);
            m.put("fineYuan", 0.0);
            m.put("remindedAt", null);
            m.put("remindMsg", "");
        } else {
            Object fk = raw.get(TicketStore.itemFkColumn());
            if (fk == null) fk = first(raw, "bookId", "itemId", "book_id", "item_id");
            long bookId = num(fk);
            m.put("bookId", bookId);
            m.put("itemId", bookId);
            m.put("dueAt", fmt(first(raw, "dueAt", "due_at")));
            m.put("fineYuan", toDouble(first(raw, "fineYuan", "fine_yuan")));
            m.put("fineStatus", str(first(raw, "fineStatus", "fine_status")));
            m.put("remindedAt", fmt(first(raw, "remindedAt", "reminded_at")));
            m.put("remindMsg", str(first(raw, "remindMsg", "remind_msg")));
            m.put("pickupAt", fmt(first(raw, "pickupAt", "pickup_at")));
            m.put("pickupPlace", str(first(raw, "pickupPlace", "pickup_place")));
            m.put("contactChannel", str(first(raw, "contactChannel", "contact_channel")));
            m.put("nextFollowAt", fmt(first(raw, "nextFollowAt", "next_follow_at")));
            Object aq = first(raw, "actualQty", "actual_qty");
            if (aq != null && !"".equals(String.valueOf(aq))) {
                m.put("actualQty", (int) num(aq));
            }
            int qty = 1;
            Object q = first(raw, "qty");
            if (q != null) {
                int n = (int) num(q);
                if (n > 0) qty = n;
            }
            m.put("qty", qty);
            Map<String, Object> item = ArchiveStore.getItemRaw(bookId);
            m.put("bookTitle", item == null ? "" : item.get("title"));
            m.put("itemTitle", item == null ? "" : item.get("title"));
            m.put("title", item == null ? "" : TicketSql.str(item.get("title")));
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
            String periodStart = fmt(first(raw, "periodStart", "period_start"));
            String periodEnd = fmt(first(raw, "periodEnd", "period_end"));
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

    private static Object first(Map<String, Object> raw, String... keys) {
        for (String k : keys) {
            if (raw.containsKey(k) && raw.get(k) != null) return raw.get(k);
        }
        return null;
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o);
    }

    private static String fmt(Object o) {
        return TicketSql.fmt(o);
    }

    private static long num(Object o) {
        return TicketSql.toLong(o);
    }

    private static double toDouble(Object o) {
        return TicketSql.toDouble(o);
    }
}
