package com.thesis.controller;

import com.thesis.capability.ArchiveStore;
import com.thesis.capability.CouponStore;
import com.thesis.capability.LessonStore;
import com.thesis.capability.OrderStore;
import com.thesis.capability.SlotStore;
import com.thesis.capability.TicketStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.R;
import com.thesis.service.SeatStore;
import com.thesis.service.SurveyStore;
import com.thesis.service.UserStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * XD-02 定时任务只读台：只列本包已启用的 DemoScheduleJobs 项，≠ 调度中台、≠ 全厂能力目录。
 */
@RestController
@RequestMapping("/api/admin/schedule-jobs")
public class ScheduleJobsController {

    @Value("${thesis.schedule-delay-ms:60000}")
    private long scheduleDelayMs;

    @Value("${thesis.order-timeout-minutes:0}")
    private int orderTimeoutMinutes;

    @Value("${thesis.confirm-receive-timeout-minutes:0}")
    private int confirmReceiveTimeoutMinutes;

    @Value("${thesis.rider-claim-timeout-minutes:0}")
    private int riderClaimTimeoutMinutes;

    @GetMapping
    public R<Map<String, Object>> list(HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        List<Map<String, Object>> jobs = new ArrayList<>();
        addIfArmed(
                jobs,
                "coupon_expire",
                "优惠券过期扫标",
                "扫描已过期的用户券并标过期",
                CouponStore.enabled(),
                "每轮扫描");
        addIfArmed(
                jobs,
                "order_timeout_cancel",
                "待付订单超时取消",
                "超时未支付的订单自动取消",
                OrderStore.enabled() && orderTimeoutMinutes > 0,
                orderTimeoutMinutes + " 分钟");
        addIfArmed(
                jobs,
                "confirm_receive_timeout",
                "确认收货超时办结",
                "超时未确认收货的订单自动完成",
                OrderStore.enabled() && confirmReceiveTimeoutMinutes > 0,
                confirmReceiveTimeoutMinutes + " 分钟");
        addIfArmed(
                jobs,
                "rider_claim_timeout",
                "骑手抢单超时释放",
                "超时未接的骑手单释放回池",
                OrderStore.enabled() && riderClaimTimeoutMinutes > 0,
                riderClaimTimeoutMinutes + " 分钟");
        addIfArmed(
                jobs,
                "cinema_show_expire",
                "过开场场次下架",
                "影院过场次关闭与占座释放",
                SeatStore.enabled(),
                "每轮扫描");
        addIfArmed(
                jobs,
                "archive_start_expire",
                "过开场档案下架",
                "到达开始时间的档案项自动关闭",
                ArchiveStore.hasStartAt(),
                "每轮扫描");
        addIfArmed(
                jobs,
                "ticket_auto_pass",
                "待审超时自动通过",
                "满足规则的待审单据自动通过",
                TicketStore.enabled()
                        && TicketStore.isAllowApproveAutoPass()
                        && TicketStore.approveAutoPassHours() > 0,
                "按业务规则");
        addIfArmed(
                jobs,
                "ticket_peer_timeout",
                "互选超时自动驳回",
                "超时未回应的互选申请自动驳回",
                TicketStore.enabled()
                        && TicketStore.isPeerAccept()
                        && TicketStore.peerTimeoutRejectHours() > 0,
                "按业务规则");
        addIfArmed(
                jobs,
                "archive_expire_notify",
                "档案临期提醒",
                "临近到期的档案发站内提醒",
                TicketStore.enabled() && TicketStore.notifyArchiveExpireDays() > 0,
                "每轮扫描");
        addIfArmed(
                jobs,
                "survey_open_close",
                "问卷开闭窗",
                "按计划开关问卷并催交",
                SurveyStore.enabled(),
                "每轮扫描");
        addIfArmed(
                jobs,
                "slot_remind",
                "预约提前提醒",
                "临近时段的预约发站内提醒",
                SlotStore.enabled() && SlotStore.remindAheadMinutes() > 0,
                "提前 " + SlotStore.remindAheadMinutes() + " 分钟");
        addIfArmed(
                jobs,
                "lesson_expire_notify",
                "课时临期提醒",
                "临近到期的课时包提醒",
                LessonStore.enabled(),
                "每轮扫描");
        addIfArmed(
                jobs,
                "post_mute_clear",
                "禁言到期解除",
                "过期的发帖禁言自动清除",
                UserStore.postMuteEnabled(),
                "每轮扫描");

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("delayMs", scheduleDelayMs);
        out.put("list", jobs);
        return R.ok(out);
    }

    private static void addIfArmed(
            List<Map<String, Object>> jobs,
            String id,
            String title,
            String detail,
            boolean armed,
            String threshold) {
        if (!armed) return;
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", id);
        m.put("title", title);
        m.put("detail", detail);
        m.put("armed", true);
        m.put("threshold", threshold);
        jobs.add(m);
    }
}
