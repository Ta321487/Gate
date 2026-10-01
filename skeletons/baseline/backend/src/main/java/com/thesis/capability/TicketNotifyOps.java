package com.thesis.capability;

import java.util.*;
import java.time.LocalDate;
import com.thesis.service.MessageStore;
import com.thesis.service.UserStore;

/**
 * TicketNotifyOps：TicketStore 纯业务逻辑拆分（零 DB 接触）。
 *
 * <p>三栈共用：bake 时由 baseline 提供；mybatis/jpa overlay 不含此类
 * （helper 不出现任何 JDBC/MyBatis token，故不参与 persistence 覆盖）。
 * 对 TicketStore 静态成员的引用一律使用显式限定名。
 */
final class TicketNotifyOps {

    private TicketNotifyOps() {}

    /** 事件上报群发当日值班；返回实际通知人数。 */

    static int notifyDutyOnNewReport(long ticketId, String applicant, String subject) {
        if (!TicketStore.dutyNotify || ticketId <= 0) return 0;
        try {
            Set<String> onDuty = StaffRosterStore.onDutyUsernames(LocalDate.now().toString());
            if (onDuty.isEmpty()) return 0;
            String sub = subject == null || subject.isBlank() ? ("单据#" + ticketId) : subject;
            String who = UserStore.displayName(applicant);
            int sent = 0;
            for (String un : onDuty) {
                if (un == null || un.isBlank() || un.equals(applicant)) continue;
                MessageStore.send(un, "新事件上报", who + " 上报了「" + sub + "」，请当日值班关注。", "ticket", ticketId);
                sent++;
            }
            return sent;
        } catch (Exception ignored) {
            return 0;
        }
    
    }


    static boolean truthy(Object v) {
        if (v == null) return false;
        if (v instanceof Boolean b) return b;
        String s = String.valueOf(v).trim();
        return "1".equals(s) || "true".equalsIgnoreCase(s) || "yes".equalsIgnoreCase(s);
    
    }


    static void notifyAdminsNewTicket(long ticketId, String applicant, String subject) {
        if (ticketId <= 0) return;
        try {
            String sub = subject == null || subject.isBlank() ? ("单据#" + ticketId) : subject;
            String who = UserStore.displayName(applicant);
            MessageStore.notifyAdmins(
                    TicketStore.peerAccept ? "待调剂" : "待受理",
                    who + " 提交了「" + sub + "」，请尽快处理。",
                    "ticket",
                    ticketId);
        } catch (Exception ignored) {
        }
    
    }


    static void notifyPeerOwnerNewTicket(long ticketId, long itemId, String applicant, String subject) {
        if (!TicketStore.peerAccept || ticketId <= 0 || itemId <= 0) return;
        try {
            Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
            if (item == null) return;
            String owner = TicketSql.str(item.get("ownerUsername"));
            if (owner.isBlank() || owner.equals(applicant)) return;
            String sub = subject == null || subject.isBlank() ? ("单据#" + ticketId) : subject;
            String who = UserStore.displayName(applicant);
            MessageStore.send(
                    owner,
                    "待确认志愿",
                    who + " 向「" + sub + "」提交了志愿，请确认或婉拒。",
                    "ticket",
                    ticketId);
        } catch (Exception ignored) {
        }
    
    }


    static String subjectOf(Map<String, Object> ticket) {
        String subject = TicketSql.str(ticket.get("title"));
        if (subject.isBlank()) subject = TicketSql.str(ticket.get("bookTitle"));
        if (subject.isBlank()) subject = "单据#" + ticket.get("id");
        return subject;
    
    }


    static void notifyTicketResult(Map<String, Object> ticket, boolean pass, String note) {
        notifyTicketResult(ticket, pass, note, "");
    }

    static void notifyTicketResult(Map<String, Object> ticket, boolean pass, String note, String passCode) {
        try {
            String user = TicketSql.str(ticket.get("username"));
            if (user.isBlank()) return;
            String subject = subjectOf(ticket);
            String noteText = note == null ? "" : note.trim();
            String noteSuffix = noteText.isBlank() ? "" : ("：" + noteText);
            String title = pass ? "审核已通过" : "审核未通过";
            String body = pass
                    ? ("「" + subject + "」已通过" + noteSuffix)
                    : ("「" + subject + "」已驳回" + noteSuffix);
            if (pass && TicketStore.hasColumn("pickup_at") && !TicketStore.bizPickupPlace.isBlank()) {
                body = body + "。请到「" + TicketStore.bizPickupPlace + "」领取，到场后由工作人员登记实发。";
            }
            String code = passCode == null ? "" : passCode.trim();
            if (pass && !code.isBlank()) {
                body = body + "。通行码：" + code + "（到访时出示即可）。";
            }
            java.util.Map<String, String> vars = new java.util.LinkedHashMap<>();
            vars.put("subject", subject);
            vars.put("note", noteText);
            vars.put("note_suffix", noteSuffix);
            vars.put("passCode", code);
            String tpl = pass ? "ticket_approved" : "ticket_rejected";
            MessageStore.sendWithTemplate(
                    user, tpl, vars, title, body, "ticket", TicketSql.toLong(ticket.get("id")));
        } catch (Exception ignored) {
            // 消息失败不影响主流程
        }
    
    }

    /** 驿站等到件：审核通过后站内信提醒申请人可取件 */

    static void notifyArrivalIfNeeded(Map<String, Object> ticket) {
        if (!TicketStore.arrivalNotify || ticket == null) return;
        String user = TicketSql.str(ticket.get("username")).trim();
        if (user.isBlank()) return;
        String subj = subjectOf(ticket);
        String body = "「" + subj + "」已到站/可办理，请尽快取件或按指引办理。";
        try {
            MessageStore.send(user, "到件通知", body, "ticket", TicketSql.toLong(ticket.get("id")));
        } catch (Exception ignored) {
            // 站内信失败不影响审核
        }
    
    }


    static void notifyPickup(Map<String, Object> ticket, String place, Integer actualQty) {
        try {
            String user = TicketSql.str(ticket.get("username"));
            if (user.isBlank()) return;
            String subject = subjectOf(ticket);
            String body = "「" + subject + "」已登记领取，地点：" + (place == null || place.isBlank() ? "—" : place);
            if (actualQty != null && actualQty > 0) {
                body = body + "，实发数量：" + actualQty;
            }
            MessageStore.send(user, "领取已登记", body, "ticket", TicketSql.toLong(ticket.get("id")));
        } catch (Exception ignored) {
            // 消息失败不影响主流程
        }
    
    }


    public static Map<String, Object> remind(long ticketId) {
        if (!TicketStore.useDeadline) throw new IllegalStateException("当前不支持到期催办");
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        TicketStatusOps.refreshOverdue(m);
        String st = String.valueOf(m.get("status"));
        if (!List.of("approved", "overdue").contains(st)) {
            throw new IllegalStateException("仅进行中/逾期可催办");
        }
        TicketStatusOps.applyFineAndRemind(m, true);
        TicketStatusOps.persistFine(m);
        try {
            String owner = TicketSql.str(m.get("username"));
            if (!owner.isBlank()) {
                String title = TicketSql.str(m.get("title"));
                if (title.isBlank()) title = TicketSql.str(m.get("bookTitle"));
                if (title.isBlank()) title = "单据#" + ticketId;
                String dueLab = "应还日";
                Object due = m.get("dueAt");
                String dueTxt = due == null ? "" : String.valueOf(due);
                String body = "【催办】「" + title + "」请尽快处理"
                        + (dueTxt.isBlank() ? "。" : "，" + dueLab + "：" + dueTxt + "。");
                Object fine = m.get("fineYuan");
                if (fine instanceof Number n && n.doubleValue() > 0) {
                    body += "预估费用 " + n.doubleValue() + " 元。";
                }
                MessageStore.send(owner, "催办提醒", body, "ticket", ticketId);
            }
        } catch (Exception ignored) {
        }
        return TicketDeriveOps.get(ticketId);
    
    }

    static void notifyApplySuccessInbox(long ticketId, String username, boolean queued) {
        if (!TicketStore.notifyOnApplySuccess || queued || ticketId <= 0) return;
        String user = username == null ? "" : username.trim();
        if (user.isBlank()) return;
        try {
            Map<String, Object> t = TicketDeriveOps.get(ticketId);
            String subject = subjectOf(t);
            String title = "报名已提交";
            String body = "「" + subject + "」已提交，请留意审核结果站内信。";
            MessageStore.send(user, title, body, "ticket", ticketId);
        } catch (Exception ignored) {
            // 站内信失败不影响主流程
        }
    }

}
