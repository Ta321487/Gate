package com.thesis.capability;

import java.util.*;
import java.sql.Timestamp;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import com.thesis.service.MessageStore;
import com.thesis.service.UserStore;
import com.thesis.service.ExamStore;
import com.thesis.service.ClaimProofStore;
import com.thesis.service.OccupySpanStore;
import com.thesis.service.TimebankStore;
import com.thesis.service.BalanceLedgerStore;
import com.thesis.config.DomainResourceJson;

/**
 * TicketPatchOps：单据扩展字段补丁（含 SQL）。
 * package-private；TicketStore 保留 public 门面。
 */
final class TicketPatchOps {

    private TicketPatchOps() {}

    static void patchTicketExtras(long ticketId, Map<String, Object> body) {
        if (ticketId <= 0 || body == null || body.isEmpty()) return;
        if (body.containsKey("contactChannel") && !TicketStore.hasColumn("contact_channel")) {
            throw new IllegalStateException("系统未配置联系渠道字段");
        }
        if (body.containsKey("nextFollowAt") && !TicketStore.hasColumn("next_follow_at")) {
            throw new IllegalStateException("系统未配置下次跟进字段");
        }
        if ((body.containsKey("fineYuan") || body.containsKey("amountYuan"))
                && !TicketStore.useDeadline
                && !TicketStore.hasColumn("fine_yuan")) {
            throw new IllegalStateException("系统未配置金额字段");
        }
        if (TicketStore.hasColumn("contact_channel") && body.containsKey("contactChannel")) {
            String ch = TicketSql.str(body.get("contactChannel")).trim();
            if (ch.length() > 32) ch = ch.substring(0, 32);
            TicketStore.mapper().updateContactChannel(TicketStore.TICKET, ticketId, ch);
        }
        if (body.containsKey("weekNo")) {
            if (!TicketStore.hasColumn("week_no")) {
                throw new IllegalStateException("系统未配置周次字段");
            }
            String rawWeek = TicketSql.str(body.get("weekNo")).trim();
            int weekNo;
            try {
                weekNo = Integer.parseInt(rawWeek);
            } catch (NumberFormatException e) {
                throw new IllegalStateException("周次须为数字");
            }
            if (weekNo < 1 || weekNo > 60) throw new IllegalStateException("周次须在 1 到 60 之间");
            TicketStore.mapper().updateWeekNo(TicketStore.TICKET, ticketId, weekNo);
        }
        if (body.containsKey("interviewPlace")) {
            if (!TicketStore.hasColumn("interview_place")) {
                throw new IllegalStateException("系统未配置面试地点字段");
            }
            String place = TicketSql.str(body.get("interviewPlace")).trim();
            if (place.length() > 128) place = place.substring(0, 128);
            TicketStore.mapper().updateInterviewPlace(TicketStore.TICKET, ticketId, place);
        }
        if (TicketStore.hasColumn("next_follow_at") && body.containsKey("nextFollowAt")) {
            Timestamp ts = null;
            Object raw = body.get("nextFollowAt");
            if (raw != null && !String.valueOf(raw).isBlank()) {
                try {
                    ts = Timestamp.valueOf(TicketSql.parseDateTimeFlexible(String.valueOf(raw).trim(), false));
                } catch (RuntimeException e) {
                    throw e instanceof IllegalStateException
                            ? e
                            : new IllegalStateException("下次跟进时间无效", e);
                } catch (Exception e) {
                    throw new IllegalStateException("下次跟进时间无效", e);
                }
            }
            TicketStore.mapper().updateNextFollowAt(TicketStore.TICKET, ticketId, ts);
        }
        // 报销等：提交时写入金额（复用 fine_yuan；借阅罚金/SLA 到期不计此路径）
        if (TicketStore.hasColumn("fine_yuan") && !TicketStore.useDeadline
                && (body.containsKey("fineYuan") || body.containsKey("amountYuan"))) {
            Object raw = body.containsKey("fineYuan") ? body.get("fineYuan") : body.get("amountYuan");
            double amt = TicketSql.toDouble(raw);
            if (amt < 0) amt = 0;
            if (amt > 99999999) amt = 99999999;
            TicketStore.mapper().updateFineYuan(TicketStore.TICKET, ticketId, amt);
        }
        if (TicketStore.allowProxyPickup || body.containsKey("proxyName") || body.containsKey("proxyPhone")) {
            if (body.containsKey("proxyName") || body.containsKey("proxyPhone")) {
                if (!TicketStore.hasColumn("proxy_name") || !TicketStore.hasColumn("proxy_phone")) {
                    throw new IllegalStateException("系统未配置代取人字段");
                }
                String pn = TicketSql.str(body.get("proxyName")).trim();
                String pp = TicketSql.str(body.get("proxyPhone")).trim();
                if (pn.length() > 64) pn = pn.substring(0, 64);
                if (pp.length() > 20) pp = pp.substring(0, 20);
                TicketStore.mapper().updateProxyPair(TicketStore.TICKET, ticketId, pn, pp);
            }
        }
        if (body.containsKey("noticeAck") && TicketStore.hasColumn("notice_ack")) {
            TicketStore.updateTicketColumn(ticketId, "notice_ack", TicketNotifyOps.truthy(body.get("noticeAck")) ? 1 : 0);
        }
        if (TicketStore.allowMeetingPlace || body.containsKey("pickupPlace") || body.containsKey("meetingPlace")) {
            if ((body.containsKey("pickupPlace") || body.containsKey("meetingPlace"))
                    && TicketStore.hasColumn("pickup_place")) {
                Object raw = body.containsKey("pickupPlace") ? body.get("pickupPlace") : body.get("meetingPlace");
                String place = TicketSql.str(raw).trim();
                if (place.length() > 128) place = place.substring(0, 128);
                TicketStore.updateTicketColumn(ticketId, "pickup_place", place);
            }
        }
        if (TicketStore.allowEmergencyContact
                || body.containsKey("emergencyContact")
                || body.containsKey("emergencyPhone")) {
            if (!TicketStore.hasColumn("emergency_contact") || !TicketStore.hasColumn("emergency_phone")) {
                if (TicketStore.allowEmergencyContact) {
                    throw new IllegalStateException("系统未配置紧急联系人字段");
                }
            } else if (body.containsKey("emergencyContact") || body.containsKey("emergencyPhone")) {
                String ec = TicketSql.str(body.get("emergencyContact")).trim();
                String ep = TicketSql.str(body.get("emergencyPhone")).trim();
                if (ec.length() > 64) ec = ec.substring(0, 64);
                if (ep.length() > 20) ep = ep.substring(0, 20);
                TicketStore.updateTicketColumn(ticketId, "emergency_contact", ec);
                TicketStore.updateTicketColumn(ticketId, "emergency_phone", ep);
            }
        }
        if ((TicketStore.allowDeposit || body.containsKey("depositYuan")) && body.containsKey("depositYuan")) {
            if (!TicketStore.hasColumn("deposit_yuan")) {
                throw new IllegalStateException("系统未配置押金字段");
            }
            double dep = TicketSql.toDouble(body.get("depositYuan"));
            if (dep < 0) dep = 0;
            if (dep > 999999) dep = 999999;
            TicketStore.updateTicketColumn(ticketId, "deposit_yuan", dep);
        }
        if (TicketStore.allowExceptionClose || body.containsKey("exceptionReason") || body.containsKey("damageClaimNote")) {
            if (body.containsKey("exceptionReason") && TicketStore.hasColumn("exception_reason")) {
                String er = TicketSql.str(body.get("exceptionReason")).trim();
                if (er.length() > 128) er = er.substring(0, 128);
                TicketStore.updateTicketColumn(ticketId, "exception_reason", er);
            }
            if (body.containsKey("damageClaimNote") && TicketStore.hasColumn("damage_claim_note")) {
                String dn = TicketSql.str(body.get("damageClaimNote")).trim();
                if (dn.length() > 255) dn = dn.substring(0, 255);
                TicketStore.updateTicketColumn(ticketId, "damage_claim_note", dn);
            }
        }
        if (body.containsKey("insuranceAck") && TicketStore.hasColumn("insurance_ack")) {
            TicketStore.updateTicketColumn(ticketId, "insurance_ack", TicketNotifyOps.truthy(body.get("insuranceAck")) ? 1 : 0);
        }
        if (body.containsKey("meetingAck") && TicketStore.hasColumn("meeting_ack")) {
            TicketStore.updateTicketColumn(ticketId, "meeting_ack", TicketNotifyOps.truthy(body.get("meetingAck")) ? 1 : 0);
        }
        if (body.containsKey("ownerMeetingAck") && TicketStore.hasColumn("owner_meeting_ack")) {
            TicketStore.updateTicketColumn(ticketId, "owner_meeting_ack", TicketNotifyOps.truthy(body.get("ownerMeetingAck")) ? 1 : 0);
        }
        if (body.containsKey("priceNoteAck") && TicketStore.hasColumn("price_note_ack")) {
            TicketStore.updateTicketColumn(ticketId, "price_note_ack", TicketNotifyOps.truthy(body.get("priceNoteAck")) ? 1 : 0);
        }
        if (body.containsKey("sponsorAck") && TicketStore.hasColumn("sponsor_ack")) {
            TicketStore.updateTicketColumn(ticketId, "sponsor_ack", TicketNotifyOps.truthy(body.get("sponsorAck")) ? 1 : 0);
        }
        if (body.containsKey("planAck") && TicketStore.hasColumn("plan_ack")) {
            TicketStore.updateTicketColumn(ticketId, "plan_ack", TicketNotifyOps.truthy(body.get("planAck")) ? 1 : 0);
        }
        if (body.containsKey("prereqAck") && TicketStore.hasColumn("prereq_ack")) {
            TicketStore.updateTicketColumn(ticketId, "prereq_ack", TicketNotifyOps.truthy(body.get("prereqAck")) ? 1 : 0);
        }
        if ((TicketStore.allowProjectNo || body.containsKey("projectNo")) && body.containsKey("projectNo") && TicketStore.hasColumn("project_no")) {
            String pn = TicketSql.str(body.get("projectNo")).trim();
            if (pn.length() > 64) pn = pn.substring(0, 64);
            TicketStore.updateTicketColumn(ticketId, "project_no", pn);
        }
        if ((TicketStore.allowProcureRef || body.containsKey("procureRefNo")) && body.containsKey("procureRefNo")
                && TicketStore.hasColumn("procure_ref_no")) {
            String pr = TicketSql.str(body.get("procureRefNo")).trim();
            if (pr.length() > 64) pr = pr.substring(0, 64);
            TicketStore.updateTicketColumn(ticketId, "procure_ref_no", pr);
        }
        if (TicketStore.allowDualReview || body.containsKey("dualReviewerA") || body.containsKey("dualReviewerB")) {
            if (body.containsKey("dualReviewerA") && TicketStore.hasColumn("dual_reviewer_a")) {
                String a = TicketSql.str(body.get("dualReviewerA")).trim();
                if (a.length() > 64) a = a.substring(0, 64);
                TicketStore.updateTicketColumn(ticketId, "dual_reviewer_a", a);
            }
            if (body.containsKey("dualReviewerB") && TicketStore.hasColumn("dual_reviewer_b")) {
                String b = TicketSql.str(body.get("dualReviewerB")).trim();
                if (b.length() > 64) b = b.substring(0, 64);
                TicketStore.updateTicketColumn(ticketId, "dual_reviewer_b", b);
            }
        }
        if ((TicketStore.allowShipFee || body.containsKey("shipFeeYuan")) && body.containsKey("shipFeeYuan") && TicketStore.hasColumn("ship_fee_yuan")) {
            double fee = TicketSql.toDouble(body.get("shipFeeYuan"));
            if (fee < 0) fee = 0;
            if (fee > 999999) fee = 999999;
            TicketStore.updateTicketColumn(ticketId, "ship_fee_yuan", fee);
        }
        if ((TicketStore.allowUtilityNote || body.containsKey("utilityNote")) && body.containsKey("utilityNote") && TicketStore.hasColumn("utility_note")) {
            String un = TicketSql.str(body.get("utilityNote")).trim();
            if (un.length() > 255) un = un.substring(0, 255);
            TicketStore.updateTicketColumn(ticketId, "utility_note", un);
        }
        if (TicketStore.requirePeerConfirm || body.containsKey("peerUsername")) {
            if (body.containsKey("peerUsername") && TicketStore.hasColumn("peer_username")) {
                String pu = TicketSql.str(body.get("peerUsername")).trim();
                if (pu.length() > 64) pu = pu.substring(0, 64);
                if (TicketStore.requirePeerConfirm && pu.isBlank()) {
                    throw new IllegalStateException("请填写对方学号或用户名");
                }
                TicketStore.mapper().updatePeerUsername(TicketStore.TICKET, ticketId, pu);
            }
        }
        if (TicketStore.requireAbandonDual && TicketStore.allowDualReview) {
            String a = TicketSql.str(body.get("dualReviewerA")).trim();
            String b = TicketSql.str(body.get("dualReviewerB")).trim();
            if (a.isBlank() || b.isBlank()) {
                throw new IllegalStateException("弃件须两名确认人签字");
            }
            if (a.equalsIgnoreCase(b)) {
                throw new IllegalStateException("弃件确认人不能为同一人");
            }
        }
        patchFollowExtraStr(ticketId, body, "interviewResult", "interview_result", 16, TicketStore.allowInterviewResult);
        if ((TicketStore.allowWrittenScore || body.containsKey("writtenScore")) && body.containsKey("writtenScore")
                && TicketStore.hasColumn("written_score")) {
            double sc = TicketSql.toDouble(body.get("writtenScore"));
            if (sc < 0) sc = 0;
            if (sc > 999) sc = 999;
            TicketStore.updateTicketColumn(ticketId, "written_score", sc);
        }
        patchFollowExtraStr(ticketId, body, "bgCheckNote", "bg_check_note", 255, TicketStore.allowBgCheckNote);
        if ((TicketStore.allowDealAmount || body.containsKey("dealAmountYuan")) && body.containsKey("dealAmountYuan")
                && TicketStore.hasColumn("deal_amount_yuan")) {
            double amt = TicketSql.toDouble(body.get("dealAmountYuan"));
            if (amt < 0) amt = 0;
            if (amt > 99999999) amt = 99999999;
            TicketStore.updateTicketColumn(ticketId, "deal_amount_yuan", amt);
        }
        patchFollowExtraStr(ticketId, body, "nextAction", "next_action", 255, TicketStore.allowNextAction);
        if (body.containsKey("nextActionDone") && TicketStore.hasColumn("next_action_done")) {
            TicketStore.updateTicketColumn(ticketId, "next_action_done", TicketNotifyOps.truthy(body.get("nextActionDone")) ? 1 : 0);
        }
        if (TicketStore.allowLeaveProxy && body.containsKey("proxyName") && TicketStore.hasColumn("proxy_name")) {
            String pn = TicketSql.str(body.get("proxyName")).trim();
            if (pn.length() > 64) pn = pn.substring(0, 64);
            TicketStore.updateTicketColumn(ticketId, "proxy_name", pn);
        }
        patchFollowExtraStr(ticketId, body, "returnDate", "return_date", 32, TicketStore.requireReturnDate);
        patchFollowExtraStr(ticketId, body, "defenseResult", "defense_result", 32, TicketStore.allowDefenseResult);
        patchFollowExtraStr(ticketId, body, "bankAccount", "bank_account", 64, TicketStore.maskBankAccount);
        patchFollowExtraStr(ticketId, body, "closeAttachUrl", "close_attach_url", 255, TicketStore.requireCloseAttach);
        patchFollowExtraStr(ticketId, body, "assignDept", "assign_dept", 64, TicketStore.allowAssignDept);
        if (body.containsKey("confidential") && TicketStore.hasColumn("confidential")) {
            TicketStore.updateTicketColumn(ticketId, "confidential", TicketNotifyOps.truthy(body.get("confidential")) ? 1 : 0);
        }
        patchFollowExtraStr(ticketId, body, "appraisalComment", "appraisal_comment", 512, TicketStore.requireAppraisal);
        patchFollowExtraStr(ticketId, body, "appraisalGrade", "appraisal_grade", 16, TicketStore.requireAppraisal);
        patchFollowExtraStr(ticketId, body, "companyEval", "company_eval", 512, TicketStore.allowCompanyEval);
        if (body.containsKey("excellentMark") && TicketStore.hasColumn("excellent_mark")) {
            TicketStore.updateTicketColumn(ticketId, "excellent_mark", TicketNotifyOps.truthy(body.get("excellentMark")) ? 1 : 0);
        }
        patchFollowExtraStr(ticketId, body, "feedbackInterest", "feedback_interest", 128, TicketStore.requireFeedbackSet);
        patchFollowExtraStr(ticketId, body, "feedbackConcern", "feedback_concern", 255, TicketStore.requireFeedbackSet);
        patchFollowExtraStr(ticketId, body, "feedbackNext", "feedback_next", 255, TicketStore.requireFeedbackSet);
        patchFollowExtraStr(ticketId, body, "recordUrl", "record_url", 255, TicketStore.allowRecordUrl);
        patchFollowExtraStr(ticketId, body, "disburseBatch", "disburse_batch", 64, TicketStore.allowDisburseBatch);
        patchFollowExtraStr(ticketId, body, "faultReason", "fault_reason", 64, TicketStore.requireFaultReason || TicketStore.repairThicken);
        patchFollowExtraStr(ticketId, body, "closeSummary", "close_summary", 512, TicketStore.requireCloseSummary || TicketStore.repairThicken);
        patchFollowExtraStr(ticketId, body, "TicketStore.preferredSlot", "preferred_slot", 64, TicketStore.preferredSlot);
        patchFollowExtraStr(ticketId, body, "holdReason", "hold_reason", 255, TicketStore.allowHoldResume);
        patchFollowExtraStr(ticketId, body, "assetCode", "asset_code", 64, TicketStore.allowAssetCode);
        patchFollowExtraStr(ticketId, body, "remoteUrl", "remote_url", 255, TicketStore.allowRemoteUrl);
        patchFollowExtraStr(ticketId, body, "skillTag", "skill_tag", 64, TicketStore.repairThicken);
        patchFollowExtraStr(ticketId, body, "routeNote", "route_note", 255, TicketStore.repairThicken);
        patchFollowExtraStr(ticketId, body, "partsNote", "parts_note", 255, TicketStore.allowPartsNote);
        patchFollowExtraStr(ticketId, body, "serialNo", "serial_no", 64, TicketStore.allowSerialNo);
        patchFollowExtraStr(ticketId, body, "helperUsername", "helper_username", 64, TicketStore.allowHelper);
        patchFollowExtraStr(ticketId, body, "audioUrl", "audio_url", 255, TicketStore.repairThicken);
        patchFollowExtraStr(ticketId, body, "ratingTags", "rating_tags", 255, TicketStore.allowRatingTags);
        patchFollowExtraStr(ticketId, body, "addressType", "address_type", 16, TicketStore.allowPublicArea);
        patchFollowExtraStr(ticketId, body, "rankScope", "rank_scope", 16, true);
        if (body.containsKey("TicketStore.nightUrgent") && TicketStore.hasColumn("night_urgent")) {
            TicketStore.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET night_urgent=? WHERE id=?",
                    TicketNotifyOps.truthy(body.get("TicketStore.nightUrgent")) ? 1 : 0,
                    ticketId);
        }
        if (body.containsKey("subscribeProgress") && TicketStore.hasColumn("subscribe_progress")) {
            TicketStore.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET subscribe_progress=? WHERE id=?",
                    TicketNotifyOps.truthy(body.get("subscribeProgress")) ? 1 : 0,
                    ticketId);
        }
        if (body.containsKey("knowledgeDeposit") && TicketStore.hasColumn("knowledge_deposit")) {
            TicketStore.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET knowledge_deposit=? WHERE id=?",
                    TicketNotifyOps.truthy(body.get("knowledgeDeposit")) ? 1 : 0,
                    ticketId);
        }
        if ((TicketStore.allowQuote || body.containsKey("quoteYuan")) && body.containsKey("quoteYuan") && TicketStore.hasColumn("quote_yuan")) {
            double q = TicketSql.toDouble(body.get("quoteYuan"));
            if (q < 0) q = 0;
            if (q > 999999) q = 999999;
            TicketStore.db().update("UPDATE " + TicketStore.TICKET + " SET quote_yuan=? WHERE id=?", q, ticketId);
        }
        if ((TicketStore.allowQuote || body.containsKey("materialFeeYuan")) && body.containsKey("materialFeeYuan")
                && TicketStore.hasColumn("material_fee_yuan")) {
            double fee = TicketSql.toDouble(body.get("materialFeeYuan"));
            if (fee < 0) fee = 0;
            if (fee > 999999) fee = 999999;
            TicketStore.db().update("UPDATE " + TicketStore.TICKET + " SET material_fee_yuan=? WHERE id=?", fee, ticketId);
        }
        if (body.containsKey("parentTicketId") && TicketStore.hasColumn("parent_ticket_id")) {
            long pid = TicketSql.toLong(body.get("parentTicketId"));
            if (pid > 0) {
                TicketStore.db().update("UPDATE " + TicketStore.TICKET + " SET parent_ticket_id=? WHERE id=?", pid, ticketId);
            }
        }
        if (body.containsKey("visitDueAt") && TicketStore.hasColumn("visit_due_at") && TicketStore.repairThicken) {
            String raw = TicketSql.str(body.get("visitDueAt")).trim();
            if (raw.isBlank()) {
                TicketStore.updateTicketColumn(ticketId, "visit_due_at", null);
            } else {
                try {
                    LocalDateTime due = LocalDateTime.parse(raw.replace(' ', 'T'));
                    TicketStore.updateTicketColumn(ticketId, "visit_due_at", Timestamp.valueOf(due));
                } catch (Exception ignored) {
                }
            }
        }

    }

    static void patchFollowExtraStr(
            long ticketId, Map<String, Object> body, String bodyKey, String col, int maxLen, boolean flagOn) {
        if (!(flagOn || body.containsKey(bodyKey)) || !body.containsKey(bodyKey) || !TicketStore.hasColumn(col)) return;
        String v = TicketSql.str(body.get(bodyKey)).trim();
        if (v.length() > maxLen) v = v.substring(0, maxLen);
        TicketStore.updateTicketColumn(ticketId, col, v);
    }

}
