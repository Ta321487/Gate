package com.thesis.capability;

import java.util.*;
import java.sql.Timestamp;
import java.time.LocalDate;
import java.time.LocalDateTime;

import com.thesis.config.MybatisSupport;
import com.thesis.mapper.TicketMapper;
import com.thesis.service.MessageStore;
import com.thesis.service.UserStore;
import com.thesis.service.ExamStore;
import com.thesis.service.ClaimProofStore;
import com.thesis.service.OccupySpanStore;
import com.thesis.service.TimebankStore;
import com.thesis.service.BalanceLedgerStore;

/**
 * TicketApplyOps：申请提交（含 SQL）。
 * package-private；TicketStore 保留 public 门面。
 */
final class TicketApplyOps {

    private TicketApplyOps() {}

    private static TicketMapper mapper() {
        return MybatisSupport.mapper(TicketMapper.class);
    }

    static Map<String, Object> apply(
            String username,
            long itemId,
            String remark,
            String attachUrl,
            Integer qty,
            String dueAt,
            String periodStart,
            String periodEnd) {
        if (TicketStore.MODE != TicketStore.Mode.ARCHIVE) {
            throw new IllegalStateException("当前为独立工单模式，请使用 applyStandalone");
        }
        UserStore.assertNotPostMuted(username);
        ExamStore.assertTicketGatePassed(username);
        if (TicketStore.allowApplyBlacklist) {
            com.thesis.service.ApplyBlacklistStore.assertNotBlocked(username);
        }
        Map<String, Object> item = ArchiveStore.getItem(itemId);
        if (item == null) throw new IllegalArgumentException("对象不存在");
        TicketGuardOps.assertClaimCooldownIfRequired(item);
        TicketGuardOps.assertSemesterCreditCapIfRequired(username, item);
        int stock = item.get("stock") instanceof Number n ? n.intValue() : Integer.parseInt(String.valueOf(item.get("stock")));
        int nQty = TicketDeriveOps.resolveQty(qty, stock);
        boolean asWaitlist = false;
        boolean asBookHold = false;
        boolean lotteryMode = TicketStore.allowLottery
                && TicketSql.str(item.get("admitMode")).contains("抽签");
        if (TicketStore.useQuota && stock < nQty) {
            if (lotteryMode) {
                // 抽签场：先收集报名，满额由管理抽签占额，此处不拦
            } else if (TicketStore.allowBookHold) {
                if (!TicketStore.hasColumn("hold_expire_at")) {
                    throw new IllegalStateException("系统未配置到书过期字段，无法预约到书");
                }
                asBookHold = true;
            } else if (TicketStore.allowWaitlist) {
                asWaitlist = true;
            } else {
                throw new IllegalStateException(ArchiveStore.stockShortage(stock));
            }
        }
        TicketAsserts.assertItemOpen(item);
        TicketAsserts.assertApplyDeadline(item);
        TicketAsserts.assertEvalOpenWindow(item);
        if (!asWaitlist && !asBookHold) {
            TicketAsserts.assertNoTimeConflict(username, itemId, item);
            TicketAsserts.assertNoMutexConflict(username, itemId, item);
            TicketAsserts.assertCategoryLimit(username, item);
            TicketAsserts.assertUnderActiveLimit(username);
        }
        String attach = TicketAsserts.normalizeAttach(attachUrl);
        if (TicketStore.requireAttach && !TicketStore.hasColumn("attach_url")) {
            throw new IllegalStateException("系统未配置附件字段，无法提交带附件的申请");
        }
        if (!attach.isBlank() && !TicketStore.hasColumn("attach_url")) {
            throw new IllegalStateException("系统未配置附件字段，无法保存附件");
        }
        LocalDateTime due = TicketDeriveOps.resolveRequestedDue(dueAt);
        LocalDateTime[] period = TicketDeriveOps.resolvePeriod(periodStart, periodEnd);
        if (TicketStore.allowQty && !TicketStore.hasColumn("qty")) {
            throw new IllegalStateException("系统未配置数量字段，无法提交带数量的申请");
        }
        if (due != null && !TicketStore.hasColumn("due_at")) {
            throw new IllegalStateException("系统未配置应还日字段，无法保存到期日期");
        }
        if (period != null && (!TicketStore.hasColumn("period_start") || !TicketStore.hasColumn("period_end"))) {
            throw new IllegalStateException("系统未配置请假区间字段，无法保存起止日期");
        }
        TicketStore.assertNotOverdueFrozen(username);
        if (!TicketStore.allowMultiTicket) {
            int dup = mapper().countActiveDup(TicketStore.TICKET, TicketStore.itemFkColumn(), username, itemId);
            if (dup > 0) {
                String deny = TicketStore.onePerArchiveDenyMessage;
                throw new IllegalStateException(
                        deny == null || deny.isBlank() ? "该对象已有进行中的单据" : deny);
            }
        }

        String rawNote = remark == null ? "" : remark.trim();
        if (TicketStore.requireRemark && rawNote.isBlank()) {
            throw new IllegalStateException("请填写说明后再提交");
        }
        if (TicketStore.minRemarkWords > 0) {
            int words = rawNote.replaceAll("\\s+", "").length();
            if (words < TicketStore.minRemarkWords) {
                throw new IllegalStateException("正文不少于 " + TicketStore.minRemarkWords + " 字后再提交");
            }
        }
        final String note = rawNote.length() > 255 ? rawNote.substring(0, 255) : rawNote;
        final boolean withAttach = TicketStore.hasColumn("attach_url");
        final boolean withQty = TicketStore.hasColumn("qty");
        final boolean withDue = due != null;
        final boolean withPeriod = period != null;
        final boolean asLottery = !asWaitlist && !asBookHold && TicketStore.allowLottery
                && TicketSql.str(item.get("admitMode")).contains("抽签");
        final String initialStatus = asBookHold
                ? "held"
                : (asWaitlist ? "waitlisted"
                        : (asLottery ? "lottery"
                                : (TicketStore.autoApprove ? "approved" : "pending")));
        final boolean withApproveAt = !asWaitlist && !asBookHold && !asLottery
                && TicketStore.autoApprove && TicketStore.hasColumn("approve_at");
        final boolean withLeaveDays = withPeriod && TicketStore.hasColumn("leave_days");
        final int leaveDaysFinal = withLeaveDays
                ? (int) (java.time.temporal.ChronoUnit.DAYS.between(
                                period[0].toLocalDate(), period[1].toLocalDate())
                        + 1)
                : 0;
        Map<String, Object> ins = new LinkedHashMap<>();
        ins.put("ticketTable", TicketStore.TICKET);
        ins.put("itemFk", TicketStore.itemFkColumn());
        ins.put("itemId", itemId);
        ins.put("username", username);
        ins.put("status", initialStatus);
        ins.put("remark", note);
        ins.put("withFineYuan", TicketStore.hasColumn("fine_yuan"));
        ins.put("withRemindMsg", TicketStore.hasColumn("remind_msg"));
        ins.put("withApproveAt", withApproveAt);
        ins.put("withAttach", withAttach);
        ins.put("withQty", withQty);
        ins.put("withDue", withDue);
        ins.put("withPeriod", withPeriod);
        if (withAttach) ins.put("attachUrl", attach);
        if (withQty) ins.put("qty", nQty);
        if (withDue) ins.put("dueAt", Timestamp.valueOf(due));
        if (withPeriod) {
            ins.put("periodStart", Timestamp.valueOf(period[0]));
            ins.put("periodEnd", Timestamp.valueOf(period[1]));
            ins.put("withLeaveDays", withLeaveDays);
            if (withLeaveDays) ins.put("leaveDays", leaveDaysFinal);
        }
        mapper().insertArchive(ins);
        long id = TicketSql.toLong(ins.get("id"));
        if (asBookHold) {
            TicketDeriveOps.appendProgress(id, "held", username, "用户预约到书");
            try {
                MessageStore.send(
                        username,
                        "预约已登记",
                        "「" + TicketNotifyOps.subjectOf(TicketDeriveOps.get(id)) + "」已预约到书，有书时将通知您确认借阅。",
                        "ticket",
                        id);
            } catch (Exception ignored) {
            }
        } else if (asWaitlist) {
            TicketDeriveOps.appendProgress(id, "waitlisted", username, "名额已满，加入候补");
            try {
                MessageStore.send(
                        username,
                        "候补排队",
                        "「" + TicketNotifyOps.subjectOf(TicketDeriveOps.get(id)) + "」名额已满，已进入候补队列，有名额时将按顺序转为待审。",
                        "ticket",
                        id);
            } catch (Exception ignored) {
            }
        } else if (asLottery) {
            TicketDeriveOps.appendProgress(id, "lottery", username, "进入待抽签");
            try {
                MessageStore.send(
                        username,
                        "待抽签",
                        "「" + TicketNotifyOps.subjectOf(TicketDeriveOps.get(id)) + "」已提交，等待抽签录取。",
                        "ticket",
                        id);
            } catch (Exception ignored) {
            }
        } else if (TicketStore.autoApprove) {
            TicketDeriveOps.appendProgress(id, "approved", username, "用户提交（即时生效）");
        } else {
            TicketDeriveOps.appendProgress(id, "pending", username, "用户提交");
            String subj = TicketNotifyOps.subjectOf(TicketDeriveOps.get(id));
            TicketNotifyOps.notifyAdminsNewTicket(id, username, subj);
            TicketNotifyOps.notifyPeerOwnerNewTicket(id, itemId, username, subj);
        }
        TicketNotifyOps.notifyApplySuccessInbox(id, username, asWaitlist || asBookHold || asLottery);
        Map<String, Object> applied = TicketDeriveOps.get(id);
        if (applied != null) {
            int dutyNotified = TicketNotifyOps.notifyDutyOnNewReport(id, username, TicketNotifyOps.subjectOf(applied));
            if (dutyNotified > 0) applied.put("dutyNotified", dutyNotified);
            String creditWarn = TicketGuardOps.creditWarnIfNearCap(username, item);
            if (creditWarn != null && !creditWarn.isBlank()) {
                applied.put("creditWarnHint", creditWarn);
            }
            String prereq = TicketSql.str(item.get("prereqCode")).trim();
            if (!prereq.isBlank()) {
                applied.put("prereqHint", "请确认已具备先修基础（提示码：" + prereq + "）");
                TicketDeriveOps.appendProgress(id, String.valueOf(applied.get("status")), username,
                        "先修提示：提示码 " + prereq + "（弱提示，未强制拦截）");
            }
        }
        return applied;
    }

    static Map<String, Object> applyStandalone(
            String username,
            String title,
            String location,
            String remark,
            Long typeId,
            Long roomId,
            String attachUrl,
            String priority,
            String contactPhone) {
        if (TicketStore.MODE != TicketStore.Mode.STANDALONE) {
            throw new IllegalStateException("当前为档案关联模式，请使用 apply");
        }
        String t = title == null ? "" : title.trim();
        if (t.isBlank()) throw new IllegalArgumentException("请填写标题");
        long dupPhoneId = TicketStore.dupPhoneOpenId(contactPhone);
        if (dupPhoneId > 0) {
            throw new IllegalStateException(
                    "该联系电话已有未办结单据#" + dupPhoneId + "，请确认是否重复提交。");
        }
        TicketAsserts.assertUnderActiveLimit(username);
        String attach = TicketAsserts.normalizeAttach(attachUrl);
        if (TicketStore.requireAttach && !TicketStore.hasColumn("attach_url")) {
            throw new IllegalStateException("系统未配置附件字段，无法提交带附件的申请");
        }
        if (!attach.isBlank() && !TicketStore.hasColumn("attach_url")) {
            throw new IllegalStateException("系统未配置附件字段，无法保存附件");
        }

        long tid = typeId == null ? 0L : typeId;
        long rid = roomId == null ? 0L : roomId;
        if (TicketLookupStore.enabled()) {
            if (tid <= 0 || !TicketLookupStore.typeExists(tid)) {
                throw new IllegalArgumentException("请选择" + TicketLookupStore.meta().get("typeLabel"));
            }
            if (rid <= 0 || !TicketLookupStore.unitExists(rid)) {
                throw new IllegalArgumentException("请选择" + TicketLookupStore.meta().get("unitLabel"));
            }
        }

        String loc = location == null ? "" : location.trim();
        if (rid > 0) {
            String fromUnit = TicketLookupStore.formatLocation(rid);
            if (!fromUnit.isBlank()) loc = fromUnit;
        }

        final String locFinal = loc;
        final String remarkFinal = remark == null ? "" : remark.trim();
        final long tidFinal = tid;
        final long ridFinal = rid;
        final String attachFinal = attach;

        String p = priority == null || priority.isBlank() ? "普通" : priority.trim();
        if (p.length() > 16) p = p.substring(0, 16);
        String phone = contactPhone == null ? "" : contactPhone.trim();
        if (phone.length() > 20) phone = phone.substring(0, 20);
        boolean wantP = priority != null && !priority.isBlank();
        boolean wantC = contactPhone != null && !contactPhone.isBlank();
        boolean withPriority = TicketStore.hasColumn("priority");
        boolean withContact = TicketStore.hasColumn("contact_phone");
        if (wantP && !withPriority) {
            throw new IllegalStateException("系统未配置优先级字段，无法保存");
        }
        if (wantC && !withContact) {
            throw new IllegalStateException("系统未配置联系电话字段，无法保存");
        }

        Map<String, Object> ins = new LinkedHashMap<>();
        ins.put("ticketTable", TicketStore.TICKET);
        ins.put("username", username);
        ins.put("title", t);
        ins.put("location", locFinal);
        ins.put("typeId", tidFinal > 0 ? tidFinal : null);
        ins.put("roomId", ridFinal > 0 ? ridFinal : null);
        ins.put("remark", remarkFinal);
        boolean withAttach = TicketStore.hasColumn("attach_url");
        ins.put("withAttach", withAttach);
        if (withAttach) ins.put("attachUrl", attachFinal);
        ins.put("withPriority", withPriority);
        ins.put("withContactPhone", withContact);
        if (withPriority) ins.put("priority", p);
        if (withContact) ins.put("contactPhone", phone);
        mapper().insertStandalone(ins);
        long id = TicketSql.toLong(ins.get("id"));
        TicketDeriveOps.appendProgress(id, "pending", username, "用户提交");
        TicketNotifyOps.notifyAdminsNewTicket(id, username, t);
        Map<String, Object> createdStd = TicketDeriveOps.get(id);
        if (createdStd != null) {
            int dutyNotified = TicketNotifyOps.notifyDutyOnNewReport(id, username, t);
            if (dutyNotified > 0) createdStd.put("dutyNotified", dutyNotified);
        }
        return createdStd;
    }

}
