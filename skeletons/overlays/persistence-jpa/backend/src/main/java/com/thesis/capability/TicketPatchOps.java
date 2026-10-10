package com.thesis.capability;

import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import java.sql.PreparedStatement;
import java.sql.Statement;
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
        if (body.containsKey("contactChannel")) {
            if (!TicketStore.hasColumn("contact_channel")) {
                throw new IllegalStateException("系统未配置联系渠道字段");
            }
            String ch = TicketSql.str(body.get("contactChannel")).trim();
            if (ch.length() > 32) ch = ch.substring(0, 32);
            TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET contact_channel=? WHERE id=?", ch, ticketId);
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
            TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET week_no=? WHERE id=?", weekNo, ticketId);
        }
        if (body.containsKey("interviewPlace")) {
            if (!TicketStore.hasColumn("interview_place")) {
                throw new IllegalStateException("系统未配置面试地点字段");
            }
            String place = TicketSql.str(body.get("interviewPlace")).trim();
            if (place.length() > 128) place = place.substring(0, 128);
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET interview_place=? WHERE id=?", place, ticketId);
        }
        if (body.containsKey("nextFollowAt")) {
            if (!TicketStore.hasColumn("next_follow_at")) {
                throw new IllegalStateException("系统未配置下次跟进字段");
            }
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
            TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET next_follow_at=? WHERE id=?", ts, ticketId);
        }
        // 报销等：提交时写入金额（复用 fine_yuan；借阅罚金/SLA 到期不计此路径）
        if (!TicketStore.useDeadline && (body.containsKey("fineYuan") || body.containsKey("amountYuan"))) {
            if (!TicketStore.hasColumn("fine_yuan")) {
                throw new IllegalStateException("系统未配置金额字段");
            }
            Object raw = body.containsKey("fineYuan") ? body.get("fineYuan") : body.get("amountYuan");
            double amt = TicketSql.toDouble(raw);
            if (amt < 0) amt = 0;
            if (amt > 99999999) amt = 99999999;
            TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET fine_yuan=? WHERE id=?", amt, ticketId);
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
                TicketSql.db().update(
                        "UPDATE " + TicketStore.TICKET + " SET proxy_name=?, proxy_phone=? WHERE id=?", pn, pp, ticketId);
            }
        }
        if (body.containsKey("noticeAck") && TicketStore.hasColumn("notice_ack")) {
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET notice_ack=? WHERE id=?",
                    TicketNotifyOps.truthy(body.get("noticeAck")) ? 1 : 0,
                    ticketId);
        }
        if (TicketStore.allowMeetingPlace || body.containsKey("pickupPlace") || body.containsKey("meetingPlace")) {
            if ((body.containsKey("pickupPlace") || body.containsKey("meetingPlace"))
                    && TicketStore.hasColumn("pickup_place")) {
                Object raw = body.containsKey("pickupPlace") ? body.get("pickupPlace") : body.get("meetingPlace");
                String place = TicketSql.str(raw).trim();
                if (place.length() > 128) place = place.substring(0, 128);
                TicketSql.db().update(
                        "UPDATE " + TicketStore.TICKET + " SET pickup_place=? WHERE id=?", place, ticketId);
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
                TicketSql.db().update(
                        "UPDATE " + TicketStore.TICKET + " SET emergency_contact=?, emergency_phone=? WHERE id=?",
                        ec, ep, ticketId);
            }
        }
        if ((TicketStore.allowDeposit || body.containsKey("depositYuan")) && body.containsKey("depositYuan")) {
            if (!TicketStore.hasColumn("deposit_yuan")) {
                throw new IllegalStateException("系统未配置押金字段");
            }
            double dep = TicketSql.toDouble(body.get("depositYuan"));
            if (dep < 0) dep = 0;
            if (dep > 999999) dep = 999999;
            TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET deposit_yuan=? WHERE id=?", dep, ticketId);
        }
        if (TicketStore.allowExceptionClose || body.containsKey("exceptionReason") || body.containsKey("damageClaimNote")) {
            if (body.containsKey("exceptionReason") && TicketStore.hasColumn("exception_reason")) {
                String er = TicketSql.str(body.get("exceptionReason")).trim();
                if (er.length() > 128) er = er.substring(0, 128);
                TicketSql.db().update(
                        "UPDATE " + TicketStore.TICKET + " SET exception_reason=? WHERE id=?", er, ticketId);
            }
            if (body.containsKey("damageClaimNote") && TicketStore.hasColumn("damage_claim_note")) {
                String dn = TicketSql.str(body.get("damageClaimNote")).trim();
                if (dn.length() > 255) dn = dn.substring(0, 255);
                TicketSql.db().update(
                        "UPDATE " + TicketStore.TICKET + " SET damage_claim_note=? WHERE id=?", dn, ticketId);
            }
        }
        if (body.containsKey("insuranceAck") && TicketStore.hasColumn("insurance_ack")) {
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET insurance_ack=? WHERE id=?",
                    TicketNotifyOps.truthy(body.get("insuranceAck")) ? 1 : 0,
                    ticketId);
        }
        if (body.containsKey("meetingAck") && TicketStore.hasColumn("meeting_ack")) {
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET meeting_ack=? WHERE id=?",
                    TicketNotifyOps.truthy(body.get("meetingAck")) ? 1 : 0,
                    ticketId);
        }
        if (body.containsKey("ownerMeetingAck") && TicketStore.hasColumn("owner_meeting_ack")) {
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET owner_meeting_ack=? WHERE id=?",
                    TicketNotifyOps.truthy(body.get("ownerMeetingAck")) ? 1 : 0,
                    ticketId);
        }
        if (body.containsKey("priceNoteAck") && TicketStore.hasColumn("price_note_ack")) {
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET price_note_ack=? WHERE id=?",
                    TicketNotifyOps.truthy(body.get("priceNoteAck")) ? 1 : 0,
                    ticketId);
        }
        if (body.containsKey("sponsorAck") && TicketStore.hasColumn("sponsor_ack")) {
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET sponsor_ack=? WHERE id=?",
                    TicketNotifyOps.truthy(body.get("sponsorAck")) ? 1 : 0,
                    ticketId);
        }
        if (body.containsKey("planAck") && TicketStore.hasColumn("plan_ack")) {
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET plan_ack=? WHERE id=?",
                    TicketNotifyOps.truthy(body.get("planAck")) ? 1 : 0,
                    ticketId);
        }
        if (body.containsKey("prereqAck") && TicketStore.hasColumn("prereq_ack")) {
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET prereq_ack=? WHERE id=?",
                    TicketNotifyOps.truthy(body.get("prereqAck")) ? 1 : 0,
                    ticketId);
        }
        if (body.containsKey("tourNoticeAck") && TicketStore.hasColumn("tour_notice_ack")) {
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET tour_notice_ack=? WHERE id=?",
                    TicketNotifyOps.truthy(body.get("tourNoticeAck")) ? 1 : 0,
                    ticketId);
        }
        if ((TicketStore.allowWishOrder || body.containsKey("wishOrder")) && body.containsKey("wishOrder")
                && TicketStore.hasColumn("wish_order")) {
            int wo = 0;
            try {
                wo = (int) Double.parseDouble(String.valueOf(body.get("wishOrder")));
            } catch (Exception ignored) {
            }
            if (wo < 1) wo = 1;
            if (wo > 2) wo = 2;
            TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET wish_order=? WHERE id=?", wo, ticketId);
        }
        if ((TicketStore.allowVolunteerRole || body.containsKey("volunteerRole")) && body.containsKey("volunteerRole")
                && TicketStore.hasColumn("volunteer_role")) {
            String vr = TicketSql.str(body.get("volunteerRole")).trim();
            if (vr.length() > 64) vr = vr.substring(0, 64);
            TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET volunteer_role=? WHERE id=?", vr, ticketId);
        }
        if ((TicketStore.allowCompanions || body.containsKey("companionNames")) && body.containsKey("companionNames")) {
            TicketLineOps.replaceCompanions(ticketId, body.get("companionNames"));
        }
        if ((TicketStore.allowSeatZone || body.containsKey("seatZone")) && body.containsKey("seatZone")
                && TicketStore.hasColumn("seat_zone")) {
            String sz = TicketSql.str(body.get("seatZone")).trim();
            if (sz.length() > 64) sz = sz.substring(0, 64);
            TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET seat_zone=? WHERE id=?", sz, ticketId);
        }
        if ((TicketStore.allowProjectNo || body.containsKey("projectNo")) && body.containsKey("projectNo") && TicketStore.hasColumn("project_no")) {
            String pn = TicketSql.str(body.get("projectNo")).trim();
            if (pn.length() > 64) pn = pn.substring(0, 64);
            TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET project_no=? WHERE id=?", pn, ticketId);
        }
        if ((TicketStore.allowProcureRef || body.containsKey("procureRefNo")) && body.containsKey("procureRefNo")
                && TicketStore.hasColumn("procure_ref_no")) {
            String pr = TicketSql.str(body.get("procureRefNo")).trim();
            if (pr.length() > 64) pr = pr.substring(0, 64);
            TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET procure_ref_no=? WHERE id=?", pr, ticketId);
        }
        if (TicketStore.allowDualReview || body.containsKey("dualReviewerA") || body.containsKey("dualReviewerB")) {
            if (body.containsKey("dualReviewerA") && TicketStore.hasColumn("dual_reviewer_a")) {
                String a = TicketSql.str(body.get("dualReviewerA")).trim();
                if (a.length() > 64) a = a.substring(0, 64);
                TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET dual_reviewer_a=? WHERE id=?", a, ticketId);
            }
            if (body.containsKey("dualReviewerB") && TicketStore.hasColumn("dual_reviewer_b")) {
                String b = TicketSql.str(body.get("dualReviewerB")).trim();
                if (b.length() > 64) b = b.substring(0, 64);
                TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET dual_reviewer_b=? WHERE id=?", b, ticketId);
            }
        }
        if ((TicketStore.allowShipFee || body.containsKey("shipFeeYuan")) && body.containsKey("shipFeeYuan") && TicketStore.hasColumn("ship_fee_yuan")) {
            double fee = TicketSql.toDouble(body.get("shipFeeYuan"));
            if (fee < 0) fee = 0;
            if (fee > 999999) fee = 999999;
            TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET ship_fee_yuan=? WHERE id=?", fee, ticketId);
        }
        if ((TicketStore.allowUtilityNote || body.containsKey("utilityNote")) && body.containsKey("utilityNote") && TicketStore.hasColumn("utility_note")) {
            String un = TicketSql.str(body.get("utilityNote")).trim();
            if (un.length() > 255) un = un.substring(0, 255);
            TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET utility_note=? WHERE id=?", un, ticketId);
        }
        if (TicketStore.requirePeerConfirm || body.containsKey("peerUsername")) {
            if (body.containsKey("peerUsername") && TicketStore.hasColumn("peer_username")) {
                String pu = TicketSql.str(body.get("peerUsername")).trim();
                if (pu.length() > 64) pu = pu.substring(0, 64);
                if (TicketStore.requirePeerConfirm && pu.isBlank()) {
                    throw new IllegalStateException("请填写对方学号或用户名");
                }
                TicketSql.db().update(
                        "UPDATE " + TicketStore.TICKET + " SET peer_username=?, peer_ack=0 WHERE id=?", pu, ticketId);
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
            TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET written_score=? WHERE id=?", sc, ticketId);
        }
        patchFollowExtraStr(ticketId, body, "bgCheckNote", "bg_check_note", 255, TicketStore.allowBgCheckNote);
        if ((TicketStore.allowDealAmount || body.containsKey("dealAmountYuan")) && body.containsKey("dealAmountYuan")
                && TicketStore.hasColumn("deal_amount_yuan")) {
            double amt = TicketSql.toDouble(body.get("dealAmountYuan"));
            if (amt < 0) amt = 0;
            if (amt > 99999999) amt = 99999999;
            TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET deal_amount_yuan=? WHERE id=?", amt, ticketId);
        }
        patchFollowExtraStr(ticketId, body, "nextAction", "next_action", 255, TicketStore.allowNextAction);
        if (body.containsKey("nextActionDone") && TicketStore.hasColumn("next_action_done")) {
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET next_action_done=? WHERE id=?",
                    TicketNotifyOps.truthy(body.get("nextActionDone")) ? 1 : 0,
                    ticketId);
        }
        if (TicketStore.allowLeaveProxy && body.containsKey("proxyName") && TicketStore.hasColumn("proxy_name")) {
            String pn = TicketSql.str(body.get("proxyName")).trim();
            if (pn.length() > 64) pn = pn.substring(0, 64);
            TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET proxy_name=? WHERE id=?", pn, ticketId);
        }
        patchFollowExtraStr(ticketId, body, "returnDate", "return_date", 32, TicketStore.requireReturnDate);
        patchFollowExtraStr(ticketId, body, "defenseResult", "defense_result", 32, TicketStore.allowDefenseResult);
        patchFollowExtraStr(ticketId, body, "bankAccount", "bank_account", 64, TicketStore.maskBankAccount);
        patchFollowExtraStr(ticketId, body, "closeAttachUrl", "close_attach_url", 255, TicketStore.requireCloseAttach);
        patchFollowExtraStr(ticketId, body, "assignDept", "assign_dept", 64, TicketStore.allowAssignDept);
        if (body.containsKey("confidential") && TicketStore.hasColumn("confidential")) {
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET confidential=? WHERE id=?",
                    TicketNotifyOps.truthy(body.get("confidential")) ? 1 : 0,
                    ticketId);
        }
        patchFollowExtraStr(ticketId, body, "appraisalComment", "appraisal_comment", 512, TicketStore.requireAppraisal);
        patchFollowExtraStr(ticketId, body, "appraisalGrade", "appraisal_grade", 16, TicketStore.requireAppraisal);
        patchFollowExtraStr(ticketId, body, "companyEval", "company_eval", 512, TicketStore.allowCompanyEval);
        if (body.containsKey("excellentMark") && TicketStore.hasColumn("excellent_mark")) {
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET excellent_mark=? WHERE id=?",
                    TicketNotifyOps.truthy(body.get("excellentMark")) ? 1 : 0,
                    ticketId);
        }
        patchFollowExtraStr(ticketId, body, "feedbackInterest", "feedback_interest", 128, TicketStore.requireFeedbackSet);
        patchFollowExtraStr(ticketId, body, "feedbackConcern", "feedback_concern", 255, TicketStore.requireFeedbackSet);
        patchFollowExtraStr(ticketId, body, "feedbackNext", "feedback_next", 255, TicketStore.requireFeedbackSet);
        patchFollowExtraStr(ticketId, body, "recordUrl", "record_url", 255, TicketStore.allowRecordUrl);
        patchFollowExtraStr(ticketId, body, "disburseBatch", "disburse_batch", 64, TicketStore.allowDisburseBatch);
        patchFollowExtraStr(ticketId, body, "faultReason", "fault_reason", 64, TicketStore.requireFaultReason || TicketStore.repairThicken);
        patchFollowExtraStr(ticketId, body, "closeSummary", "close_summary", 512, TicketStore.requireCloseSummary || TicketStore.repairThicken);
        patchFollowExtraStr(ticketId, body, "preferredSlot", "preferred_slot", 64, TicketStore.preferredSlot);
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
        patchFollowExtraStr(ticketId, body, "pickupMethod", "pickup_method", 16, TicketStore.allowCertPickup);
        patchFollowExtraStr(ticketId, body, "mailAddress", "mail_address", 255, TicketStore.allowCertPickup);
        if (TicketStore.allowCertPickup && body.containsKey("pickupMethod")) {
            String pm = TicketSql.str(body.get("pickupMethod")).trim();
            if (pm.isBlank()) throw new IllegalStateException("请选择领取方式");
            if ("邮寄".equals(pm)) {
                String addr = TicketSql.str(body.get("mailAddress")).trim();
                if (addr.isBlank()) throw new IllegalStateException("邮寄请填写收件地址");
            }
        }
        if ((TicketStore.allowCertUrgent || body.containsKey("certUrgent"))
                && body.containsKey("certUrgent")
                && TicketStore.hasColumn("cert_urgent")) {
            boolean urgent = TicketNotifyOps.truthy(body.get("certUrgent"));
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET cert_urgent=? WHERE id=?",
                    urgent ? 1 : 0,
                    ticketId);
            if (urgent && TicketStore.hasColumn("priority")) {
                TicketSql.db().update(
                        "UPDATE " + TicketStore.TICKET + " SET priority=? WHERE id=?",
                        "紧急",
                        ticketId);
            }
        }
        patchFollowExtraStr(ticketId, body, "expressNo", "express_no", 64, TicketStore.allowCertPickup);
        if (TicketStore.allowCertPickup
                && body.containsKey("expressNo")
                && TicketStore.hasColumn("express_no")) {
            String en = TicketSql.str(body.get("expressNo")).trim();
            if (en.length() > 64) en = en.substring(0, 64);
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET express_no=? WHERE id=?", en, ticketId);
        }
        if ((TicketStore.allowSealCopies || body.containsKey("sealCopies"))
                && body.containsKey("sealCopies")
                && TicketStore.hasColumn("seal_copies")) {
            int copies = (int) Math.round(TicketSql.toDouble(body.get("sealCopies")));
            if (TicketStore.allowSealCopies && copies < 1) {
                throw new IllegalStateException("用印份数至少 1 份");
            }
            if (copies < 0) copies = 0;
            if (copies > 999) copies = 999;
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET seal_copies=? WHERE id=?", copies, ticketId);
        }
        patchFollowExtraStr(ticketId, body, "bindNote", "bind_note", 255, TicketStore.allowSealCopies);
        patchFollowExtraStr(ticketId, body, "sealCopyNos", "seal_copy_nos", 255, TicketStore.allowSealCopies);
        if ((TicketStore.allowSealCopies || body.containsKey("sealWitnessAck"))
                && body.containsKey("sealWitnessAck")
                && TicketStore.hasColumn("seal_witness_ack")) {
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET seal_witness_ack=? WHERE id=?",
                    TicketNotifyOps.truthy(body.get("sealWitnessAck")) ? 1 : 0,
                    ticketId);
        }
        if ((TicketStore.allowFleetMileage || body.containsKey("mileageKm"))
                && body.containsKey("mileageKm")
                && TicketStore.hasColumn("mileage_km")) {
            double km = TicketSql.toDouble(body.get("mileageKm"));
            if (TicketStore.allowFleetMileage && !(km > 0)) {
                throw new IllegalStateException("行驶里程须大于 0");
            }
            if (km < 0) throw new IllegalStateException("行驶里程不能为负数");
            if (km > 999999) km = 999999;
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET mileage_km=? WHERE id=?", km, ticketId);
        }
        patchFollowExtraStr(ticketId, body, "fuelNote", "fuel_note", 255, TicketStore.allowFleetMileage);
        if (TicketStore.allowFleetMileage
                && body.containsKey("fuelNote")
                && TicketSql.str(body.get("fuelNote")).trim().isBlank()) {
            throw new IllegalStateException("请填写油耗备注");
        }
        if ((TicketStore.allowExpenseInvoice || body.containsKey("invoiceCount"))
                && body.containsKey("invoiceCount")
                && TicketStore.hasColumn("invoice_count")) {
            int n = (int) Math.round(TicketSql.toDouble(body.get("invoiceCount")));
            if (TicketStore.allowExpenseInvoice && n < 1) {
                throw new IllegalStateException("发票张数至少 1 张");
            }
            if (n < 0) n = 0;
            if (n > 999) n = 999;
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET invoice_count=? WHERE id=?", n, ticketId);
        }
        if (TicketStore.allowExpenseInvoice && (body.containsKey("fineYuan") || body.containsKey("amountYuan"))) {
            Object raw = body.containsKey("fineYuan") ? body.get("fineYuan") : body.get("amountYuan");
            if (TicketSql.toDouble(raw) <= 0) {
                throw new IllegalStateException("报销金额须大于 0");
            }
        }
        if ((TicketStore.allowVisitorCount || body.containsKey("visitorCount"))
                && body.containsKey("visitorCount")
                && TicketStore.hasColumn("visitor_count")) {
            int n = (int) Math.round(TicketSql.toDouble(body.get("visitorCount")));
            if (n < 0) n = 0;
            if (n > 99) n = 99;
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET visitor_count=? WHERE id=?", n, ticketId);
            if (TicketStore.allowVisitorCount && n > 0) {
                String cn = TicketSql.str(body.get("companionNames")).trim();
                    Map<String, Object> cur = TicketRowMaps.load(ticketId);
                    String existing = cur == null ? "" : TicketSql.str(cur.get("companionNames")).trim();
                    if (existing.isBlank() && !body.containsKey("companionNames")) {
                        throw new IllegalStateException("有随行请填写随行人姓名");
                    }
                    if (body.containsKey("companionNames") && cn.isBlank()) {
                        throw new IllegalStateException("有随行请填写随行人姓名");
                    }
                }
            }
        if (TicketStore.allowVisitorCount || TicketStore.allowCompanions) {
            if (body.containsKey("companionNames")) {
                TicketLineOps.replaceCompanions(ticketId, body.get("companionNames"));
            }
        }
        if (TicketStore.allowAwardCertNo && body.containsKey("awardCertNo")) {
            if (!TicketStore.hasColumn("award_cert_no")) {
                throw new IllegalStateException("系统未配置证书编号字段");
            }
            String certNo = TicketSql.str(body.get("awardCertNo")).trim();
            if (certNo.isBlank()) {
                throw new IllegalStateException("请填写证书编号");
            }
            if (certNo.length() > 64) certNo = certNo.substring(0, 64);
            Integer dup = TicketSql.db().queryForObject(
                    "SELECT COUNT(*) FROM " + TicketStore.TICKET
                            + " WHERE award_cert_no=? AND id<>?",
                    Integer.class, certNo, ticketId);
            if (dup != null && dup > 0) {
                throw new IllegalStateException("证书编号已存在，请核对后重填");
            }
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET award_cert_no=? WHERE id=?",
                    certNo, ticketId);
        }
        if (TicketStore.allowFleetCrew && body.containsKey("driverName")) {
            if (!TicketStore.hasColumn("driver_name")) {
                throw new IllegalStateException("系统未配置驾驶员字段");
            }
            String dn = TicketSql.str(body.get("driverName")).trim();
            if (dn.isBlank()) {
                throw new IllegalStateException("请填写驾驶员");
            }
            if (dn.length() > 64) dn = dn.substring(0, 64);
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET driver_name=? WHERE id=?", dn, ticketId);
        }
        if (TicketStore.allowFleetCrew && body.containsKey("passengerNames")) {
            if (!TicketStore.hasColumn("passenger_names")) {
                throw new IllegalStateException("系统未配置随车人字段");
            }
            String pn = TicketSql.str(body.get("passengerNames")).trim();
            if (pn.length() > 255) pn = pn.substring(0, 255);
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET passenger_names=? WHERE id=?", pn, ticketId);
        }
        if ((TicketStore.allowCompHours || body.containsKey("compHours"))
                && body.containsKey("compHours")
                && TicketStore.hasColumn("comp_hours")) {
            double h = TicketSql.toDouble(body.get("compHours"));
            if (h < 0) h = 0;
            if (h > 9999) h = 9999;
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET comp_hours=? WHERE id=?", h, ticketId);
        }
        if ((TicketStore.allowReturnFuel || body.containsKey("returnFuel"))
                && body.containsKey("returnFuel")
                && TicketStore.hasColumn("return_fuel")) {
            double fuel = TicketSql.toDouble(body.get("returnFuel"));
            if (fuel < 0) fuel = 0;
            if (fuel > 100) fuel = 100;
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET return_fuel=? WHERE id=?", fuel, ticketId);
        }
        if (TicketStore.allowLaborPlace && body.containsKey("laborPlace")) {
            if (!TicketStore.hasColumn("labor_place")) {
                throw new IllegalStateException("系统未配置劳动地点字段");
            }
            String lp = TicketSql.str(body.get("laborPlace")).trim();
            if (lp.isBlank()) {
                throw new IllegalStateException("请填写劳动地点");
            }
            if (lp.length() > 128) lp = lp.substring(0, 128);
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET labor_place=? WHERE id=?", lp, ticketId);
        }
        if (TicketStore.allowEffectiveOn && body.containsKey("effectiveOn")) {
            if (!TicketStore.hasColumn("effective_on")) {
                throw new IllegalStateException("系统未配置生效日期字段");
            }
            String eo = TicketSql.str(body.get("effectiveOn")).trim();
            if (eo.isBlank()) {
                throw new IllegalStateException("请选择生效日期");
            }
            if (eo.length() > 32) eo = eo.substring(0, 32);
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET effective_on=? WHERE id=?", eo, ticketId);
        }
        if (TicketStore.allowDocRev) {
            if (!TicketStore.hasColumn("doc_rev")) {
                throw new IllegalStateException("系统未配置正文版本号字段");
            }
            String rev = TicketSql.str(body.get("docRev")).trim();
            if (rev.isBlank()) {
                throw new IllegalStateException("请填写正文版本号");
            }
            if (rev.length() > 32) rev = rev.substring(0, 32);
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET doc_rev=? WHERE id=?", rev, ticketId);
        }
        if (TicketStore.allowFitoutQuiet) {
            if (!TicketStore.hasColumn("work_start") || !TicketStore.hasColumn("work_end")) {
                throw new IllegalStateException("系统未配置施工时段字段");
            }
            String ws = TicketSql.str(body.get("workStart")).trim();
            String we = TicketSql.str(body.get("workEnd")).trim();
            if (ws.length() > 8) ws = ws.substring(0, 8);
            if (we.length() > 8) we = we.substring(0, 8);
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET work_start=?, work_end=? WHERE id=?",
                    ws, we, ticketId);
        }
        if (TicketStore.allowIssueCopies) {
            if (!TicketStore.hasColumn("issue_copies")) {
                throw new IllegalStateException("系统未配置开具份数字段");
            }
            int n = (int) Math.round(TicketSql.toDouble(body.get("issueCopies")));
            if (n < 1) {
                throw new IllegalStateException("请填写开具份数（至少 1 份）");
            }
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET issue_copies=? WHERE id=?", n, ticketId);
        }
        if (TicketStore.allowSignParties) {
            if (!TicketStore.hasColumn("sign_parties")) {
                throw new IllegalStateException("系统未配置签署方字段");
            }
            String sp = TicketSql.str(body.get("signParties")).trim();
            if (sp.isBlank()) {
                throw new IllegalStateException("请勾选签署方");
            }
            if (sp.length() > 255) sp = sp.substring(0, 255);
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET sign_parties=? WHERE id=?", sp, ticketId);
        }
        if (TicketStore.allowTrainHours) {
            if (!TicketStore.hasColumn("train_hours")) {
                throw new IllegalStateException("系统未配置培训学时字段");
            }
            double hours = TicketSql.toDouble(body.get("trainHours"));
            if (!(hours > 0)) {
                throw new IllegalStateException("请填写大于 0 的培训学时");
            }
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET train_hours=? WHERE id=?", hours, ticketId);
        }
        if (TicketStore.allowMemberChange) {
            if (!TicketStore.hasColumn("member_change_note")) {
                throw new IllegalStateException("系统未配置成员变更说明字段");
            }
            String note = TicketSql.str(body.get("memberChangeNote")).trim();
            if (note.isBlank()) {
                throw new IllegalStateException("请填写成员变更说明");
            }
            if (note.length() > 512) note = note.substring(0, 512);
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET member_change_note=? WHERE id=?", note, ticketId);
        }
        if (TicketStore.allowProcureBudget) {
            if (!TicketStore.hasColumn("procure_amount")) {
                throw new IllegalStateException("系统未配置申购金额字段");
            }
            double amt = TicketSql.toDouble(body.get("procureAmount"));
            if (!(amt > 0)) {
                throw new IllegalStateException("请填写大于 0 的申购金额");
            }
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET procure_amount=? WHERE id=?", amt, ticketId);
        }
        if (TicketStore.allowCheckinException) {
            if (!TicketStore.hasColumn("exception_type")) {
                throw new IllegalStateException("系统未配置异常类型字段");
            }
            String et = TicketSql.str(body.get("exceptionType")).trim();
            if (et.isBlank()) {
                throw new IllegalStateException("请选择异常类型");
            }
            if (et.length() > 32) et = et.substring(0, 32);
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET exception_type=? WHERE id=?", et, ticketId);
        }
        if (TicketStore.allowVisitPurpose) {
            if (!TicketStore.hasColumn("visit_purpose")) {
                throw new IllegalStateException("系统未配置来访目的字段");
            }
            String vp = TicketSql.str(body.get("visitPurpose")).trim();
            if (vp.isBlank()) {
                throw new IllegalStateException("请选择来访目的");
            }
            if (vp.length() > 32) vp = vp.substring(0, 32);
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET visit_purpose=? WHERE id=?", vp, ticketId);
        }
        if (TicketStore.allowFitoutRectify) {
            if (!TicketStore.hasColumn("rectify_note")) {
                throw new IllegalStateException("系统未配置整改说明字段");
            }
            String rn = TicketSql.str(body.get("rectifyNote")).trim();
            if (rn.isBlank()) {
                throw new IllegalStateException("请填写整改说明");
            }
            if (rn.length() > 512) rn = rn.substring(0, 512);
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET rectify_note=? WHERE id=?", rn, ticketId);
        }
        if (TicketStore.allowProjFundUse) {
            if (!TicketStore.hasColumn("fund_use_yuan") || !TicketStore.hasColumn("fund_use_note")) {
                throw new IllegalStateException("系统未配置经费使用字段");
            }
            double yuan = TicketSql.toDouble(body.get("fundUseYuan"));
            if (!(yuan > 0)) {
                throw new IllegalStateException("请填写大于 0 的使用经费");
            }
            String fn = TicketSql.str(body.get("fundUseNote")).trim();
            if (fn.isBlank()) {
                throw new IllegalStateException("请填写经费使用说明");
            }
            if (fn.length() > 512) fn = fn.substring(0, 512);
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET fund_use_yuan=?, fund_use_note=? WHERE id=?",
                    yuan, fn, ticketId);
        }
        if (TicketStore.allowVisitSlotRemain) {
            if (!TicketStore.hasColumn("visit_on")) {
                throw new IllegalStateException("系统未配置来访日期字段");
            }
            String vo = TicketSql.str(body.get("visitOn")).trim();
            if (vo.length() >= 10) vo = vo.substring(0, 10);
            if (vo.isBlank()) {
                throw new IllegalStateException("请选择来访日期");
            }
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET visit_on=? WHERE id=?", vo, ticketId);
        }
        if (TicketStore.allowPlagiarismUrl) {
            if (!TicketStore.hasColumn("plagiarism_url")) {
                throw new IllegalStateException("系统未配置查重链接字段");
            }
            String url = TicketSql.str(body.get("plagiarismUrl")).trim();
            if (url.isBlank() || !(url.startsWith("http://") || url.startsWith("https://"))) {
                throw new IllegalStateException("请填写以 http:// 或 https:// 开头的查重报告链接");
            }
            if (url.length() > 512) url = url.substring(0, 512);
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET plagiarism_url=? WHERE id=?", url, ticketId);
        }
        if (TicketStore.allowPartyStage) {
            if (!TicketStore.hasColumn("party_stage") || !TicketStore.hasColumn("stage_on")) {
                throw new IllegalStateException("系统未配置发展阶段字段");
            }
            String ps = TicketSql.str(body.get("partyStage")).trim();
            String so = TicketSql.str(body.get("stageOn")).trim();
            if (so.length() >= 10) so = so.substring(0, 10);
            if (ps.isBlank() || so.isBlank()) {
                throw new IllegalStateException("请选择发展阶段并填写进入日期");
            }
            if (ps.length() > 32) ps = ps.substring(0, 32);
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET party_stage=?, stage_on=? WHERE id=?",
                    ps, so, ticketId);
        }
        if (TicketStore.allowEvalObserve) {
            if (!TicketStore.hasColumn("observe_on") || !TicketStore.hasColumn("observe_note")) {
                throw new IllegalStateException("系统未配置听课记录字段");
            }
            String oo = TicketSql.str(body.get("observeOn")).trim();
            if (oo.length() >= 10) oo = oo.substring(0, 10);
            String on = TicketSql.str(body.get("observeNote")).trim();
            if (oo.isBlank() || on.isBlank()) {
                throw new IllegalStateException("请填写听课日期和记录");
            }
            if (on.length() > 512) on = on.substring(0, 512);
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET observe_on=?, observe_note=? WHERE id=?",
                    oo, on, ticketId);
        }
        if (TicketStore.allowScheduleImpact) {
            if (!TicketStore.hasColumn("schedule_impact_note")) {
                throw new IllegalStateException("系统未配置课表影响说明字段");
            }
            String si = TicketSql.str(body.get("scheduleImpactNote")).trim();
            if (si.isBlank()) {
                throw new IllegalStateException("请填写对课表的影响");
            }
            if (si.length() > 512) si = si.substring(0, 512);
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET schedule_impact_note=? WHERE id=?", si, ticketId);
        }
        if (TicketStore.allowContractAmount) {
            if (!TicketStore.hasColumn("contract_amount")) {
                throw new IllegalStateException("系统未配置合同金额字段");
            }
            double amt = TicketSql.toDouble(body.get("contractAmount"));
            if (!(amt > 0)) {
                throw new IllegalStateException("请填写大于 0 的合同金额");
            }
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET contract_amount=? WHERE id=?", amt, ticketId);
        }
        if (TicketStore.allowExpenseLines) {
            TicketLineOps.replaceExpenseLines(ticketId, body.get("expenseLines"));
        }
        if (TicketStore.allowTripLegs) {
            TicketLineOps.replaceTripLegs(ticketId, body.get("tripLegs"));
        }
        if (TicketStore.allowClubRoster) {
            TicketLineOps.replaceClubRoster(ticketId, body.get("clubMembers"));
        }
        if (TicketStore.allowCarpassParkingMutex) {
            if (!TicketStore.hasColumn("parking_on")) {
                throw new IllegalStateException("系统未配置占用车位日期字段");
            }
            String po = TicketSql.str(body.get("parkingOn")).trim();
            if (po.length() >= 10) po = po.substring(0, 10);
            if (po.isBlank()) {
                throw new IllegalStateException("请选择占用车位日期");
            }
            long itemId = 0;
            try {
                Long iid = TicketSql.db().queryForObject(
                        "SELECT " + TicketStore.itemFkColumn() + " FROM " + TicketStore.TICKET + " WHERE id=?",
                        Long.class,
                        ticketId);
                itemId = iid == null ? 0 : iid;
            } catch (Exception ignored) {
            }
            TicketGuardOps.assertParkingMutexIfRequired(itemId, po, ticketId);
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET parking_on=? WHERE id=?", po, ticketId);
        }
        if (TicketStore.allowContractRenew) {
            if (!TicketStore.hasColumn("renew_on") || !TicketStore.hasColumn("renew_note")) {
                throw new IllegalStateException("系统未配置续签字段");
            }
            String ro = TicketSql.str(body.get("renewOn")).trim();
            if (ro.length() >= 10) ro = ro.substring(0, 10);
            String rn = TicketSql.str(body.get("renewNote")).trim();
            if (ro.isBlank() || rn.isBlank()) {
                throw new IllegalStateException("请填写续签日期和说明");
            }
            if (rn.length() > 512) rn = rn.substring(0, 512);
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET renew_on=?, renew_note=? WHERE id=?",
                    ro, rn, ticketId);
        }
        if (TicketStore.allowVisitWalkIn && body.containsKey("walkIn") && TicketStore.hasColumn("walk_in")) {
            boolean wi = TicketNotifyOps.truthy(body.get("walkIn"));
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET walk_in=? WHERE id=?", wi ? 1 : 0, ticketId);
            if (wi && TicketStore.hasColumn("visit_on")) {
                String vo = TicketSql.str(body.get("visitOn")).trim();
                if (vo.length() >= 10) vo = vo.substring(0, 10);
                if (!vo.isBlank()) {
                    TicketSql.db().update(
                            "UPDATE " + TicketStore.TICKET + " SET visit_on=? WHERE id=?", vo, ticketId);
                }
            }
        }
        if (TicketStore.allowCheckinProxy && body.containsKey("checkinProxyBy")
                && TicketStore.hasColumn("checkin_proxy_by")) {
            String by = TicketSql.str(body.get("checkinProxyBy")).trim();
            if (by.length() > 64) by = by.substring(0, 64);
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET checkin_proxy_by=? WHERE id=?", by, ticketId);
        }
        if (TicketStore.allowProjChangeLog) {
            if (!TicketStore.hasColumn("change_log_note")) {
                throw new IllegalStateException("系统未配置变更摘要字段");
            }
            String note = TicketSql.str(body.get("changeLogNote")).trim();
            if (note.isBlank()) {
                throw new IllegalStateException("请填写变更摘要");
            }
            if (note.length() > 512) note = note.substring(0, 512);
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET change_log_note=? WHERE id=?", note, ticketId);
        }
        if (TicketStore.allowProcureReturn
                && body.containsKey("returnFail")
                && TicketStore.hasColumn("return_fail")) {
            boolean fail = TicketNotifyOps.truthy(body.get("returnFail"));
            String rn2 = TicketSql.str(body.get("returnNote")).trim();
            if (fail && rn2.isBlank()) {
                throw new IllegalStateException("验收不合格时请填写退货说明");
            }
            if (rn2.length() > 512) rn2 = rn2.substring(0, 512);
            if (TicketStore.hasColumn("return_note")) {
                TicketSql.db().update(
                        "UPDATE " + TicketStore.TICKET + " SET return_fail=?, return_note=? WHERE id=?",
                        fail ? 1 : 0, rn2, ticketId);
            } else {
                TicketSql.db().update(
                        "UPDATE " + TicketStore.TICKET + " SET return_fail=? WHERE id=?",
                        fail ? 1 : 0, ticketId);
            }
        }
        if (TicketStore.allowFleetViolation
                && body.containsKey("violationPerson")
                && TicketStore.hasColumn("violation_person")) {
            String vp = TicketSql.str(body.get("violationPerson")).trim();
            if (vp.isBlank()) {
                throw new IllegalStateException("请填写违章责任人");
            }
            if (vp.length() > 64) vp = vp.substring(0, 64);
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET violation_person=? WHERE id=?", vp, ticketId);
        }
        if ((TicketStore.allowVendorQuotes || TicketStore.minVendorQuotes > 0)
                && body.containsKey("vendorQuotes")) {
            if (!TicketStore.hasColumn("vendor_quotes")) {
                throw new IllegalStateException("系统未配置比价供应商字段");
            }
            String raw = TicketSql.str(body.get("vendorQuotes"));
            int need = TicketStore.minVendorQuotes;
            int n = 0;
            for (String line : raw.replace('\r', '\n').split("\n")) {
                if (!line.trim().isBlank()) n++;
            }
            if (need > 0 && n < need) {
                throw new IllegalStateException("比价供应商至少 " + need + " 家，请每行填写一家");
            }
            String v = raw.trim();
            if (v.length() > 2000) v = v.substring(0, 2000);
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET vendor_quotes=? WHERE id=?", v, ticketId);
        }

        if (body.containsKey("nightUrgent") && TicketStore.hasColumn("night_urgent")) {
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET night_urgent=? WHERE id=?",
                    TicketNotifyOps.truthy(body.get("nightUrgent")) ? 1 : 0,
                    ticketId);
        }
        if (body.containsKey("subscribeProgress") && TicketStore.hasColumn("subscribe_progress")) {
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET subscribe_progress=? WHERE id=?",
                    TicketNotifyOps.truthy(body.get("subscribeProgress")) ? 1 : 0,
                    ticketId);
        }
        if (body.containsKey("knowledgeDeposit") && TicketStore.hasColumn("knowledge_deposit")) {
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET knowledge_deposit=? WHERE id=?",
                    TicketNotifyOps.truthy(body.get("knowledgeDeposit")) ? 1 : 0,
                    ticketId);
        }
        if ((TicketStore.allowQuote || body.containsKey("quoteYuan")) && body.containsKey("quoteYuan") && TicketStore.hasColumn("quote_yuan")) {
            double q = TicketSql.toDouble(body.get("quoteYuan"));
            if (q < 0) q = 0;
            if (q > 999999) q = 999999;
            TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET quote_yuan=? WHERE id=?", q, ticketId);
        }
        if ((TicketStore.allowQuote || body.containsKey("materialFeeYuan")) && body.containsKey("materialFeeYuan")
                && TicketStore.hasColumn("material_fee_yuan")) {
            double fee = TicketSql.toDouble(body.get("materialFeeYuan"));
            if (fee < 0) fee = 0;
            if (fee > 999999) fee = 999999;
            TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET material_fee_yuan=? WHERE id=?", fee, ticketId);
        }
        if (body.containsKey("parentTicketId") && TicketStore.hasColumn("parent_ticket_id")) {
            long pid = TicketSql.toLong(body.get("parentTicketId"));
            if (pid > 0) {
                Map<String, Object> parent = TicketStore.get(pid);
                if (parent == null) throw new IllegalArgumentException("回复对象不存在");
                Object grand = parent.get("parentTicketId");
                if (grand instanceof Number n && n.longValue() > 0) {
                    throw new IllegalStateException("该回复下不能再盖楼");
                }
                Map<String, Object> child = TicketStore.get(ticketId);
                if (child != null) {
                    long pItem = TicketSql.toLong(parent.get("itemId") != null ? parent.get("itemId") : parent.get("bookId"));
                    long cItem = TicketSql.toLong(child.get("itemId") != null ? child.get("itemId") : child.get("bookId"));
                    if (pItem > 0 && cItem > 0 && pItem != cItem) {
                        throw new IllegalStateException("只能回复同一帖下的内容");
                    }
                }
                TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET parent_ticket_id=? WHERE id=?", pid, ticketId);
            }
        }
        if (body.containsKey("visitDueAt") && TicketStore.hasColumn("visit_due_at") && TicketStore.repairThicken) {
            String raw = TicketSql.str(body.get("visitDueAt")).trim();
            if (raw.isBlank()) {
                TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET visit_due_at=NULL WHERE id=?", ticketId);
            } else {
                try {
                    LocalDateTime due = LocalDateTime.parse(raw.replace(' ', 'T'));
                    TicketSql.db().update(
                            "UPDATE " + TicketStore.TICKET + " SET visit_due_at=? WHERE id=?",
                            Timestamp.valueOf(due),
                            ticketId);
                } catch (Exception ignored) {
                    // 格式不对则跳过，避免假成功写坏列
                }
            }
        }
    }

    static void patchFollowExtraStr(
            long ticketId, Map<String, Object> body, String bodyKey, String col, int maxLen, boolean flagOn) {
        if (!(flagOn || body.containsKey(bodyKey)) || !body.containsKey(bodyKey) || !TicketStore.hasColumn(col)) return;
        String v = TicketSql.str(body.get(bodyKey)).trim();
        if (v.length() > maxLen) v = v.substring(0, maxLen);
        TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET " + col + "=? WHERE id=?", v, ticketId);
    }

}
