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
        m.put("passCode", str(first(raw, "passCode", "pass_code")));
        int renewCount = 0;
        Object rc = first(raw, "renewCount", "renew_count");
        if (rc != null && !"".equals(String.valueOf(rc))) {
            try {
                renewCount = (int) num(rc);
            } catch (Exception ignored) {
                renewCount = 0;
            }
        }
        m.put("renewCount", renewCount);
        m.put("holdExpireAt", fmt(first(raw, "holdExpireAt", "hold_expire_at")));
        m.put("dueSoonNotifiedAt", fmt(first(raw, "dueSoonNotifiedAt", "due_soon_notified_at")));
        int everOverdue = 0;
        Object eo = first(raw, "everOverdue", "ever_overdue");
        if (eo instanceof Number) everOverdue = ((Number) eo).intValue();
        else if (eo != null && !String.valueOf(eo).isBlank()) {
            try { everOverdue = Integer.parseInt(String.valueOf(eo).trim()); } catch (Exception ignored) {}
        }
        m.put("everOverdue", everOverdue);

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
            m.put("dueAt", fmt(first(raw, "dueAt", "due_at")));
            m.put("fineYuan", toDouble(first(raw, "fineYuan", "fine_yuan")));
            m.put("remindedAt", fmt(first(raw, "remindedAt", "reminded_at")));
            m.put("remindMsg", str(first(raw, "remindMsg", "remind_msg")));
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
                int leaveDays = 0;
                Object rawLeaveDays = first(raw, "leaveDays", "leave_days");
                if (rawLeaveDays instanceof Number num) leaveDays = num.intValue();
                if (leaveDays <= 0) leaveDays = daysBetweenInclusive(periodStart, periodEnd);
                if (leaveDays > 0) m.put("leaveDays", leaveDays);
            } else if (item != null) {
                m.put("startAt", item.get("startAt"));
                m.put("endAt", item.get("endAt"));
                m.put("applyDeadlineAt", item.get("applyDeadlineAt"));
            }
        }
        int weekNo = 0;
        Object rawWeek = first(raw, "weekNo", "week_no");
        if (rawWeek instanceof Number num) weekNo = num.intValue();
        if (weekNo > 0) m.put("weekNo", weekNo);
        Object rawPlace = first(raw, "interviewPlace", "interview_place");
        if (rawPlace != null) {
            String place = String.valueOf(rawPlace).trim();
            if (!place.isEmpty()) m.put("interviewPlace", place);
        }
        putFollowOptStr(m, raw, "interview_result", "interviewResult");
        putFollowOptStr(m, raw, "bg_check_note", "bgCheckNote");
        putFollowOptStr(m, raw, "return_date", "returnDate");
        putFollowOptStr(m, raw, "defense_result", "defenseResult");
        putFollowOptStr(m, raw, "bank_account", "bankAccount");
        putFollowOptStr(m, raw, "disburse_batch", "disburseBatch");
        putFollowOptStr(m, raw, "close_attach_url", "closeAttachUrl");
        putFollowOptStr(m, raw, "assign_dept", "assignDept");
        putFollowOptStr(m, raw, "appraisal_comment", "appraisalComment");
        putFollowOptStr(m, raw, "appraisal_grade", "appraisalGrade");
        putFollowOptStr(m, raw, "company_eval", "companyEval");
        putFollowOptStr(m, raw, "next_action", "nextAction");
        putFollowOptStr(m, raw, "feedback_interest", "feedbackInterest");
        putFollowOptStr(m, raw, "feedback_concern", "feedbackConcern");
        putFollowOptStr(m, raw, "feedback_next", "feedbackNext");
        putFollowOptStr(m, raw, "record_url", "recordUrl");
        Object ws = first(raw, "writtenScore", "written_score");
        if (ws instanceof Number n) m.put("writtenScore", n.doubleValue());
        Object da = first(raw, "dealAmountYuan", "deal_amount_yuan");
        if (da instanceof Number n) m.put("dealAmountYuan", n.doubleValue());
        Object conf = first(raw, "confidential");
        if (conf instanceof Number n) m.put("confidential", n.intValue());
        Object nad = first(raw, "nextActionDone", "next_action_done");
        if (nad instanceof Number n) m.put("nextActionDone", n.intValue());
        Object em = first(raw, "excellentMark", "excellent_mark");
        if (em instanceof Number n) m.put("excellentMark", n.intValue());
        Object rev = first(raw, "reviseCount", "revise_count");
        if (rev instanceof Number n) m.put("reviseCount", n.intValue());
        m.put("followSoonNotifiedAt", fmt(first(raw, "followSoonNotifiedAt", "follow_soon_notified_at")));
        String pn = str(first(raw, "proxyName", "proxy_name"));
        if (!pn.isBlank()) m.put("proxyName", pn);
        String pp = str(first(raw, "proxyPhone", "proxy_phone"));
        if (!pp.isBlank()) m.put("proxyPhone", pp);
        String er = str(first(raw, "exceptionReason", "exception_reason"));
        if (!er.isBlank()) m.put("exceptionReason", er);
        String dn = str(first(raw, "damageClaimNote", "damage_claim_note"));
        if (!dn.isBlank()) m.put("damageClaimNote", dn);
        Object depObj = first(raw, "depositYuan", "deposit_yuan");
        if (depObj != null) {
            double dep = toDouble(depObj);
            if (dep > 0) m.put("depositYuan", dep);
        }
        Object ackObj = first(raw, "noticeAck", "notice_ack");
        if (ackObj != null) {
            String a = String.valueOf(ackObj);
            m.put("noticeAck", "1".equals(a) || "true".equalsIgnoreCase(a));
        }
        String peer = str(first(raw, "peerUsername", "peer_username"));
        if (!peer.isBlank()) m.put("peerUsername", peer);
        Object peerAckObj = first(raw, "peerAck", "peer_ack");
        if (peerAckObj != null) {
            String a = String.valueOf(peerAckObj);
            m.put("peerAck", "1".equals(a) || "true".equalsIgnoreCase(a));
        }
        String rankScope = str(first(raw, "rankScope", "rank_scope"));
        if (!rankScope.isBlank()) m.put("rankScope", rankScope);
        String pno = str(first(raw, "projectNo", "project_no"));
        if (!pno.isBlank()) m.put("projectNo", pno);
        String pref = str(first(raw, "procureRefNo", "procure_ref_no"));
        if (!pref.isBlank()) m.put("procureRefNo", pref);
        return m;
    }

    private static void putFollowOptStr(Map<String, Object> m, Map<String, Object> raw, String col, String key) {
        String v = str(first(raw, key, col)).trim();
        if (!v.isBlank()) m.put(key, v);
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
