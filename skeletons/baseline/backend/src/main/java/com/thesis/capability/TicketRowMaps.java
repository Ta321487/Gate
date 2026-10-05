package com.thesis.capability;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
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
        m.put("ratingDimsJson", "");
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
        try {
            m.put("passExpireAt", TicketSql.fmt(TicketSql.safeTs(rs, "pass_expire_at")));
        } catch (Exception ignored) {
        }
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
            m.put("dueAt", TicketSql.fmt(TicketSql.safeTs(rs, "due_at")));
            m.put("fineYuan", TicketSql.safeDouble(rs, "fine_yuan"));
            m.put("remindedAt", TicketSql.fmt(TicketSql.safeTs(rs, "reminded_at")));
            m.put("remindMsg", TicketSql.safeStr(rs, "remind_msg"));
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
            if (item != null && item.get("surveyFormId") != null) {
                Object sf = item.get("surveyFormId");
                if (sf instanceof Number n && n.longValue() > 0) {
                    m.put("surveyFormId", n.longValue());
                }
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
        putFollowOptStr(m, rs, "interview_result", "interviewResult");
        putFollowOptStr(m, rs, "bg_check_note", "bgCheckNote");
        putFollowOptStr(m, rs, "return_date", "returnDate");
        putFollowOptStr(m, rs, "defense_result", "defenseResult");
        putFollowOptStr(m, rs, "bank_account", "bankAccount");
        putFollowOptStr(m, rs, "disburse_batch", "disburseBatch");
        putFollowOptStr(m, rs, "close_attach_url", "closeAttachUrl");
        putFollowOptStr(m, rs, "assign_dept", "assignDept");
        putFollowOptStr(m, rs, "appraisal_comment", "appraisalComment");
        putFollowOptStr(m, rs, "appraisal_grade", "appraisalGrade");
        putFollowOptStr(m, rs, "company_eval", "companyEval");
        putFollowOptStr(m, rs, "next_action", "nextAction");
        putFollowOptStr(m, rs, "feedback_interest", "feedbackInterest");
        putFollowOptStr(m, rs, "feedback_concern", "feedbackConcern");
        putFollowOptStr(m, rs, "feedback_next", "feedbackNext");
        putFollowOptStr(m, rs, "record_url", "recordUrl");
        putFollowOptStr(m, rs, "fault_reason", "faultReason");
        putFollowOptStr(m, rs, "close_summary", "closeSummary");
        putFollowOptStr(m, rs, "preferred_slot", "preferredSlot");
        putFollowOptStr(m, rs, "emergency_contact", "emergencyContact");
        putFollowOptStr(m, rs, "emergency_phone", "emergencyPhone");
        putFollowOptStr(m, rs, "hold_reason", "holdReason");
        putFollowOptStr(m, rs, "asset_code", "assetCode");
        putFollowOptStr(m, rs, "remote_url", "remoteUrl");
        putFollowOptStr(m, rs, "skill_tag", "skillTag");
        putFollowOptStr(m, rs, "route_note", "routeNote");
        putFollowOptStr(m, rs, "parts_note", "partsNote");
        putFollowOptStr(m, rs, "serial_no", "serialNo");
        putFollowOptStr(m, rs, "helper_username", "helperUsername");
            putFollowOptStr(m, rs, "cc_usernames", "ccUsernames");
            putFollowOptStr(m, rs, "approve_attach_url", "approveAttachUrl");
            putFollowOptStr(m, rs, "pickup_method", "pickupMethod");
            putFollowOptStr(m, rs, "mail_address", "mailAddress");
            putFollowOptStr(m, rs, "express_no", "expressNo");
            putFollowOptStr(m, rs, "bind_note", "bindNote");
            putFollowOptStr(m, rs, "seal_copy_nos", "sealCopyNos");
            putFollowOptStr(m, rs, "fuel_note", "fuelNote");
            try {
                if (TicketStore.hasColumn("seal_witness_ack")) {
                    int sw = rs.getInt("seal_witness_ack");
                    if (!rs.wasNull()) m.put("sealWitnessAck", sw != 0);
                }
            } catch (Exception ignored) {}
            try {
                int cu = rs.getInt("cert_urgent");
                if (!rs.wasNull()) m.put("certUrgent", cu == 1);
            } catch (Exception ignored) {
            }
            try {
                int sc = rs.getInt("seal_copies");
                if (!rs.wasNull()) m.put("sealCopies", sc);
            } catch (Exception ignored) {
            }
            try {
                Object mk = rs.getObject("mileage_km");
                if (mk instanceof Number n) m.put("mileageKm", n.doubleValue());
            } catch (Exception ignored) {
            }
            try {
                int ic = rs.getInt("invoice_count");
                if (!rs.wasNull()) m.put("invoiceCount", ic);
            } catch (Exception ignored) {
            }
            try {
                int vc = rs.getInt("visitor_count");
                if (!rs.wasNull()) m.put("visitorCount", vc);
            } catch (Exception ignored) {
            }
            putFollowOptStr(m, rs, "award_cert_no", "awardCertNo");
            putFollowOptStr(m, rs, "vendor_quotes", "vendorQuotes");

            putFollowOptStr(m, rs, "driver_name", "driverName");
            putFollowOptStr(m, rs, "passenger_names", "passengerNames");
            try {
                Object ch = rs.getObject("comp_hours");
                if (ch instanceof Number n) m.put("compHours", n.doubleValue());
            } catch (Exception ignored) {
            }
            try {
                Object rf = rs.getObject("return_fuel");
                if (rf instanceof Number n) m.put("returnFuel", n.doubleValue());
            } catch (Exception ignored) {
            }
            putFollowOptStr(m, rs, "labor_place", "laborPlace");
            putFollowOptStr(m, rs, "effective_on", "effectiveOn");
            putFollowOptStr(m, rs, "cert_issue_no", "certIssueNo");
            putFollowOptStr(m, rs, "doc_rev", "docRev");
            putFollowOptStr(m, rs, "work_start", "workStart");
            putFollowOptStr(m, rs, "work_end", "workEnd");
            putFollowOptStr(m, rs, "sign_parties", "signParties");
            putFollowOptStr(m, rs, "member_change_note", "memberChangeNote");
            putFollowOptStr(m, rs, "exception_type", "exceptionType");
            putFollowOptStr(m, rs, "visit_purpose", "visitPurpose");
            putFollowOptStr(m, rs, "violation_person", "violationPerson");
            putFollowOptStr(m, rs, "rectify_note", "rectifyNote");
            putFollowOptStr(m, rs, "return_note", "returnNote");
            putFollowOptStr(m, rs, "fund_use_note", "fundUseNote");
            putFollowOptStr(m, rs, "visit_on", "visitOn");
            putFollowOptStr(m, rs, "plagiarism_url", "plagiarismUrl");
            putFollowOptStr(m, rs, "party_stage", "partyStage");
            putFollowOptStr(m, rs, "stage_on", "stageOn");
            putFollowOptStr(m, rs, "observe_on", "observeOn");
            putFollowOptStr(m, rs, "observe_note", "observeNote");
            putFollowOptStr(m, rs, "schedule_impact_note", "scheduleImpactNote");
            putFollowOptStr(m, rs, "change_log_note", "changeLogNote");
            putFollowOptStr(m, rs, "verify_code", "verifyCode");
            putFollowOptStr(m, rs, "checkin_proxy_by", "checkinProxyBy");
            putFollowOptStr(m, rs, "parking_on", "parkingOn");
            putFollowOptStr(m, rs, "renew_on", "renewOn");
            putFollowOptStr(m, rs, "renew_note", "renewNote");
            putFollowOptStr(m, rs, "pickup_redeem_code", "pickupRedeemCode");
            putFollowOptStr(m, rs, "objection_note", "objectionNote");
            try {
                m.put("objectionDueAt", TicketSql.fmt(TicketSql.safeTs(rs, "objection_due_at")));
            } catch (Exception ignored) {
            }
            try {
                m.put("objectionAt", TicketSql.fmt(TicketSql.safeTs(rs, "objection_at")));
            } catch (Exception ignored) {
            }
            try {
                int rf = rs.getInt("return_fail");
                if (!rs.wasNull()) m.put("returnFail", rf == 1);
            } catch (Exception ignored) {
            }
            try {
                int wi = rs.getInt("walk_in");
                if (!rs.wasNull()) m.put("walkIn", wi == 1);
            } catch (Exception ignored) {
            }
            try {
                int pr = rs.getInt("pickup_redeemed");
                if (!rs.wasNull()) m.put("pickupRedeemed", pr == 1);
            } catch (Exception ignored) {
            }
            try {
                Object fu = rs.getObject("fund_use_yuan");
                if (fu instanceof Number n) m.put("fundUseYuan", n.doubleValue());
            } catch (Exception ignored) {
            }
            putFollowOptStr(m, rs, "return_note", "returnNote");
            putFollowOptStr(m, rs, "fund_use_note", "fundUseNote");
            putFollowOptStr(m, rs, "visit_on", "visitOn");
            putFollowOptStr(m, rs, "plagiarism_url", "plagiarismUrl");
            putFollowOptStr(m, rs, "party_stage", "partyStage");
            putFollowOptStr(m, rs, "stage_on", "stageOn");
            putFollowOptStr(m, rs, "observe_on", "observeOn");
            putFollowOptStr(m, rs, "observe_note", "observeNote");
            putFollowOptStr(m, rs, "schedule_impact_note", "scheduleImpactNote");
            putFollowOptStr(m, rs, "change_log_note", "changeLogNote");
            putFollowOptStr(m, rs, "verify_code", "verifyCode");
            putFollowOptStr(m, rs, "checkin_proxy_by", "checkinProxyBy");
            putFollowOptStr(m, rs, "parking_on", "parkingOn");
            putFollowOptStr(m, rs, "renew_on", "renewOn");
            putFollowOptStr(m, rs, "renew_note", "renewNote");
            putFollowOptStr(m, rs, "pickup_redeem_code", "pickupRedeemCode");
            putFollowOptStr(m, rs, "objection_note", "objectionNote");
            try {
                m.put("objectionDueAt", TicketSql.fmt(TicketSql.safeTs(rs, "objection_due_at")));
            } catch (Exception ignored) {
            }
            try {
                m.put("objectionAt", TicketSql.fmt(TicketSql.safeTs(rs, "objection_at")));
            } catch (Exception ignored) {
            }
            try {
                int rf = rs.getInt("return_fail");
                if (!rs.wasNull()) m.put("returnFail", rf == 1);
            } catch (Exception ignored) {
            }
            try {
                int wi = rs.getInt("walk_in");
                if (!rs.wasNull()) m.put("walkIn", wi == 1);
            } catch (Exception ignored) {
            }
            try {
                int pr = rs.getInt("pickup_redeemed");
                if (!rs.wasNull()) m.put("pickupRedeemed", pr == 1);
            } catch (Exception ignored) {
            }
            try {
                Object fu = rs.getObject("fund_use_yuan");
                if (fu instanceof Number n) m.put("fundUseYuan", n.doubleValue());
            } catch (Exception ignored) {
            }
            try {
                Object ca = rs.getObject("contract_amount");
                if (ca instanceof Number n) m.put("contractAmount", n.doubleValue());
            } catch (Exception ignored) {
            }
            try {
                Object ic = rs.getObject("issue_copies");
                if (ic instanceof Number n) m.put("issueCopies", n.intValue());
            } catch (Exception ignored) {
            }
            try {
                Object th = rs.getObject("train_hours");
                if (th instanceof Number n) m.put("trainHours", n.doubleValue());
            } catch (Exception ignored) {
            }
            try {
                Object pa = rs.getObject("procure_amount");
                if (pa instanceof Number n) m.put("procureAmount", n.doubleValue());
            } catch (Exception ignored) {
            }

        putFollowOptStr(m, rs, "audio_url", "audioUrl");
        putFollowOptStr(m, rs, "rating_tags", "ratingTags");
        putFollowOptStr(m, rs, "address_type", "addressType");
        putFollowOptStr(m, rs, "rank_scope", "rankScope");
        try {
            m.put("urgeAt", TicketSql.fmt(TicketSql.safeTs(rs, "urge_at")));
        } catch (Exception ignored) {
        }
        try {
            m.put("responseDueAt", TicketSql.fmt(TicketSql.safeTs(rs, "response_due_at")));
        } catch (Exception ignored) {
        }
        try {
            m.put("visitDueAt", TicketSql.fmt(TicketSql.safeTs(rs, "visit_due_at")));
        } catch (Exception ignored) {
        }
        try {
            int uc = rs.getInt("urge_count");
            if (!rs.wasNull()) m.put("urgeCount", uc);
        } catch (Exception ignored) {
        }
        try {
            int ucx = rs.getInt("urge_cancelled");
            if (!rs.wasNull()) m.put("urgeCancelled", ucx == 1);
        } catch (Exception ignored) {
        }
        try {
            int nu = rs.getInt("night_urgent");
            if (!rs.wasNull()) m.put("nightUrgent", nu == 1);
        } catch (Exception ignored) {
        }
        try {
            int sp = rs.getInt("subscribe_progress");
            if (!rs.wasNull()) m.put("subscribeProgress", sp == 1);
        } catch (Exception ignored) {
        }
        try {
            int kd = rs.getInt("knowledge_deposit");
            if (!rs.wasNull()) m.put("knowledgeDeposit", kd == 1);
        } catch (Exception ignored) {
        }
        try {
            int qc = rs.getInt("quote_confirmed");
            if (!rs.wasNull()) m.put("quoteConfirmed", qc == 1);
        } catch (Exception ignored) {
        }
        try {
            Object qy = rs.getObject("quote_yuan");
            if (qy instanceof Number n) m.put("quoteYuan", n.doubleValue());
        } catch (Exception ignored) {
        }
        try {
            Object mf = rs.getObject("material_fee_yuan");
            if (mf instanceof Number n) m.put("materialFeeYuan", n.doubleValue());
        } catch (Exception ignored) {
        }
        try {
            Object pid = rs.getObject("parent_ticket_id");
            if (pid instanceof Number n && n.longValue() > 0) m.put("parentTicketId", n.longValue());
        } catch (Exception ignored) {
        }
        try {
            Object ws = rs.getObject("written_score");
            if (ws instanceof Number n) m.put("writtenScore", n.doubleValue());
        } catch (Exception ignored) {
        }
        try {
            Object da = rs.getObject("deal_amount_yuan");
            if (da instanceof Number n) m.put("dealAmountYuan", n.doubleValue());
        } catch (Exception ignored) {
        }
        try {
            Object conf = rs.getObject("confidential");
            if (conf instanceof Number n) m.put("confidential", n.intValue());
        } catch (Exception ignored) {
        }
        try {
            Object nad = rs.getObject("next_action_done");
            if (nad instanceof Number n) m.put("nextActionDone", n.intValue());
        } catch (Exception ignored) {
        }
        try {
            Object em = rs.getObject("excellent_mark");
            if (em instanceof Number n) m.put("excellentMark", n.intValue());
        } catch (Exception ignored) {
        }
        try {
            Object rc = rs.getObject("revise_count");
            if (rc instanceof Number n) m.put("reviseCount", n.intValue());
        } catch (Exception ignored) {
        }
        try {
            m.put("followSoonNotifiedAt", TicketSql.fmt(TicketSql.safeTs(rs, "follow_soon_notified_at")));
        } catch (Exception ignored) {
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
            int mack = rs.getInt("meeting_ack");
            if (!rs.wasNull()) m.put("meetingAck", mack == 1);
        } catch (Exception ignored) {
        }
        try {
            int omack = rs.getInt("owner_meeting_ack");
            if (!rs.wasNull()) m.put("ownerMeetingAck", omack == 1);
        } catch (Exception ignored) {
        }
        try {
            int pnack = rs.getInt("price_note_ack");
            if (!rs.wasNull()) m.put("priceNoteAck", pnack == 1);
        } catch (Exception ignored) {
        }
        try {
            int sack = rs.getInt("sponsor_ack");
            if (!rs.wasNull()) m.put("sponsorAck", sack == 1);
        } catch (Exception ignored) {
        }
        try {
            int packPlan = rs.getInt("plan_ack");
            if (!rs.wasNull()) m.put("planAck", packPlan == 1);
        } catch (Exception ignored) {
        }
        try {
            int preq = rs.getInt("prereq_ack");
            if (!rs.wasNull()) m.put("prereqAck", preq == 1);
        } catch (Exception ignored) {
        }
        try {
            int late = rs.getInt("late_minutes");
            if (!rs.wasNull() && late >= 0) m.put("lateMinutes", late);
        } catch (Exception ignored) {
        }
        try {
            int iack = rs.getInt("insurance_ack");
            if (!rs.wasNull()) m.put("insuranceAck", iack == 1);
        } catch (Exception ignored) {
        }
        try {
            int tnack = rs.getInt("tour_notice_ack");
            if (!rs.wasNull()) m.put("tourNoticeAck", tnack == 1);
        } catch (Exception ignored) {
        }
        try {
            int wo = rs.getInt("wish_order");
            if (!rs.wasNull() && wo > 0) m.put("wishOrder", wo);
        } catch (Exception ignored) {
        }
        try {
            String vr = TicketSql.safeStr(rs, "volunteer_role");
            if (vr != null && !vr.isBlank()) m.put("volunteerRole", vr);
        } catch (Exception ignored) {
        }
        try {
            String sz = TicketSql.safeStr(rs, "seat_zone");
            if (sz != null && !sz.isBlank()) m.put("seatZone", sz);
        } catch (Exception ignored) {
        }
        try {
            String pg = TicketSql.safeStr(rs, "post_gallery_json");
            if (pg != null && !pg.isBlank()) {
                m.put("postGalleryImages", parsePostGallery(pg));
            }
        } catch (Exception ignored) {
        }
        try {
            int cwa = rs.getInt("credit_writeback_ack");
            if (!rs.wasNull()) m.put("creditWritebackAck", cwa == 1);
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
        TicketLineOps.attach(m);
        return m;
    }

    private static void putFollowOptStr(Map<String, Object> m, java.sql.ResultSet rs, String col, String key) {
        try {
            String v = TicketSql.safeStr(rs, col);
            if (v != null && !v.isBlank()) m.put(key, v);
        } catch (Exception ignored) {
        }
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

    private static List<String> parsePostGallery(String raw) {
        List<String> out = new ArrayList<>();
        if (raw == null || raw.isBlank()) return out;
        String s = raw.trim();
        if (!s.startsWith("[")) {
            out.add(s);
            return out;
        }
        // 轻量解析：按引号切片，避免再引 Jackson
        int i = 0;
        while (i < s.length()) {
            int a = s.indexOf('"', i);
            if (a < 0) break;
            int b = s.indexOf('"', a + 1);
            if (b < 0) break;
            String u = s.substring(a + 1, b).replace("\\\"", "\"").replace("\\\\", "\\").trim();
            if (!u.isBlank()) out.add(u);
            i = b + 1;
            if (out.size() >= 9) break;
        }
        return out;
    }
}
