package com.thesis.capability;

import java.util.*;
import java.sql.Timestamp;
import java.time.LocalDate;
import java.time.LocalDateTime;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import java.sql.PreparedStatement;
import java.sql.Statement;
import com.thesis.service.MentionNotify;
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
        com.thesis.service.UserStore.assertNotPostMuted(username);
        ExamStore.assertTicketGatePassed(username);
        if (TicketStore.allowApplyBlacklist) {
            com.thesis.service.ApplyBlacklistStore.assertNotBlocked(username);
        }
        Map<String, Object> item = ArchiveStore.getItem(itemId);
        if (item == null) throw new IllegalArgumentException("对象不存在");
        ArchiveStore.assertNotLocked(item);
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
        if (OccupySpanStore.enabled() && period != null) {
            OccupySpanStore.assertNoOverlap(username, itemId, period[0], period[1]);
        }
        TicketStore.assertNotOverdueFrozen(username);
        if (!TicketStore.allowMultiTicket) {
            Integer dup = TicketSql.db().queryForObject(
                    "SELECT COUNT(*) FROM " + TicketStore.TICKET
                            + " WHERE username=? AND " + TicketStore.itemFkColumn()
                            + "=? AND status IN ('pending','pending_mid','pending_final','approved','overdue','waitlisted','held','hold_ready','lottery')",
                    Integer.class, username, itemId);
            if (dup != null && dup > 0) {
                String deny = TicketStore.onePerArchiveDenyMessage;
                throw new IllegalStateException(
                        deny == null || deny.isBlank() ? "该对象已有进行中的单据" : deny);
            }
        }

        String rawNote = remark == null ? "" : remark.trim();
        com.thesis.service.SensitiveWordGate.assertClean(rawNote);
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
        KeyHolder kh = new GeneratedKeyHolder();
        final boolean withAttach = TicketStore.hasColumn("attach_url");
        final boolean withQty = TicketStore.hasColumn("qty");
        final boolean withDue = due != null;
        final boolean withPeriod = period != null;
        final String attachFinal = attach;
        final int qtyFinal = nQty;
        final Timestamp dueTs = withDue ? Timestamp.valueOf(due) : null;
        final Timestamp periodStartTs = withPeriod ? Timestamp.valueOf(period[0]) : null;
        final Timestamp periodEndTs = withPeriod ? Timestamp.valueOf(period[1]) : null;
        final boolean withLeaveDays = withPeriod && TicketStore.hasColumn("leave_days");
        final int leaveDaysFinal = withLeaveDays
                ? (int) (java.time.temporal.ChronoUnit.DAYS.between(
                                period[0].toLocalDate(), period[1].toLocalDate())
                        + 1)
                : 0;
        final boolean asLottery = !asWaitlist && !asBookHold && TicketStore.allowLottery
                && TicketSql.str(item.get("admitMode")).contains("抽签");
        final String initialStatus = asBookHold
                ? "held"
                : (asWaitlist ? "waitlisted"
                        : (asLottery ? "lottery"
                                : (TicketStore.autoApprove ? "approved" : "pending")));
        final boolean withApproveAt = !asWaitlist && !asBookHold && !asLottery
                && TicketStore.autoApprove && TicketStore.hasColumn("approve_at");
        TicketSql.db().update(con -> {
            StringBuilder cols = new StringBuilder(
                    TicketStore.itemFkColumn() + ",username,status,apply_at,remark");
            StringBuilder vals = new StringBuilder("?,?,?,NOW(),?");
            if (TicketStore.hasColumn("fine_yuan")) {
                cols.append(",fine_yuan");
                vals.append(",0");
            }
            if (TicketStore.hasColumn("remind_msg")) {
                cols.append(",remind_msg");
                vals.append(",''");
            }
            if (withApproveAt) {
                cols.append(",approve_at");
                vals.append(",NOW()");
            }
            if (withAttach) {
                cols.append(",attach_url");
                vals.append(",?");
            }
            if (withQty) {
                cols.append(",qty");
                vals.append(",?");
            }
            if (withDue) {
                cols.append(",due_at");
                vals.append(",?");
            }
            if (withPeriod) {
                cols.append(",period_start,period_end");
                vals.append(",?,?");
                if (withLeaveDays) {
                    cols.append(",leave_days");
                    vals.append(",?");
                }
            }
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO " + TicketStore.TICKET + " (" + cols + ") VALUES (" + vals + ")",
                    Statement.RETURN_GENERATED_KEYS);
            int i = 1;
            ps.setLong(i++, itemId);
            ps.setString(i++, username);
            ps.setString(i++, initialStatus);
            ps.setString(i++, note);
            if (withAttach) ps.setString(i++, attachFinal);
            if (withQty) ps.setInt(i++, qtyFinal);
            if (withDue) ps.setTimestamp(i++, dueTs);
            if (withPeriod) {
                ps.setTimestamp(i++, periodStartTs);
                ps.setTimestamp(i++, periodEndTs);
                if (withLeaveDays) ps.setInt(i, leaveDaysFinal);
            }
            return ps;
        }, kh);
        Number key = kh.getKey();
        long id = key == null ? 0L : key.longValue();
        if (asBookHold) {
            TicketDeriveOps.appendProgress(id, "held", username, "暂无库存，加入预约");
            try {
                MessageStore.send(
                        username,
                        "预约排队",
                        "「" + TicketNotifyOps.subjectOf(TicketDeriveOps.get(id)) + "」暂无库存，已加入预约队列，到书后将站内信通知。",
                        "ticket",
                        id);
            } catch (Exception ignored) {
                // 站内信失败不影响预约单
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
                // 站内信失败不影响候补单
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
                // 站内信失败不影响待抽签单
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
        if (period != null && OccupySpanStore.enabled()) {
            OccupySpanStore.record(username, itemId, id, TicketNotifyOps.subjectOf(TicketDeriveOps.get(id)), period[0], period[1]);
        }
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
        try {
            MentionNotify.notifyFromText(username, note, "ticket", id, "跟帖");
        } catch (Exception ignored) {
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

        KeyHolder kh = new GeneratedKeyHolder();
        if (TicketStore.hasColumn("attach_url")) {
            TicketSql.db().update(con -> {
                PreparedStatement ps = con.prepareStatement(
                        "INSERT INTO " + TicketStore.TICKET
                                + " (username,title,location,type_id,room_id,status,apply_at,remark,attach_url) "
                                + "VALUES (?,?,?,?,?, 'pending', NOW(), ?, ?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setString(1, username);
                ps.setString(2, t);
                ps.setString(3, locFinal);
                if (tidFinal > 0) ps.setLong(4, tidFinal); else ps.setObject(4, null);
                if (ridFinal > 0) ps.setLong(5, ridFinal); else ps.setObject(5, null);
                ps.setString(6, remarkFinal);
                ps.setString(7, attachFinal);
                return ps;
            }, kh);
        } else {
            TicketSql.db().update(con -> {
                PreparedStatement ps = con.prepareStatement(
                        "INSERT INTO " + TicketStore.TICKET
                                + " (username,title,location,type_id,room_id,status,apply_at,remark) "
                                + "VALUES (?,?,?,?,?, 'pending', NOW(), ?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setString(1, username);
                ps.setString(2, t);
                ps.setString(3, locFinal);
                if (tidFinal > 0) ps.setLong(4, tidFinal); else ps.setObject(4, null);
                if (ridFinal > 0) ps.setLong(5, ridFinal); else ps.setObject(5, null);
                ps.setString(6, remarkFinal);
                return ps;
            }, kh);
        }
        Number key = kh.getKey();
        long id = key == null ? 0L : key.longValue();
        patchStandaloneExtras(id, priority, contactPhone);
        TicketDeriveOps.appendProgress(id, "pending", username, "用户提交");
        TicketNotifyOps.notifyAdminsNewTicket(id, username, t);
        Map<String, Object> createdStd = TicketDeriveOps.get(id);
        if (createdStd != null) {
            int dutyNotified = TicketNotifyOps.notifyDutyOnNewReport(id, username, t);
            if (dutyNotified > 0) createdStd.put("dutyNotified", dutyNotified);
        }
        return createdStd;
    }

    static void patchStandaloneExtras(long id, String priority, String contactPhone) {
        if (id <= 0) return;
        boolean hasP = TicketStore.hasColumn("priority");
        boolean hasC = TicketStore.hasColumn("contact_phone");
        boolean wantP = priority != null && !priority.isBlank();
        boolean wantC = contactPhone != null && !contactPhone.isBlank();
        if (wantP && !hasP) {
            throw new IllegalStateException("系统未配置优先级字段，无法保存");
        }
        if (wantC && !hasC) {
            throw new IllegalStateException("系统未配置联系电话字段，无法保存");
        }
        if (!hasP && !hasC) return;
        String p = priority == null || priority.isBlank() ? "普通" : priority.trim();
        if (p.length() > 16) p = p.substring(0, 16);
        String phone = contactPhone == null ? "" : contactPhone.trim();
        if (phone.length() > 20) phone = phone.substring(0, 20);
        if (hasP && hasC) {
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET priority=?, contact_phone=? WHERE id=?", p, phone, id);
        } else if (hasP) {
            TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET priority=? WHERE id=?", p, id);
        } else {
            TicketSql.db().update("UPDATE " + TicketStore.TICKET + " SET contact_phone=? WHERE id=?", phone, id);
        }
    }

}
