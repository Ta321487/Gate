package com.thesis.controller;

import com.thesis.capability.CouponStore;
import com.thesis.capability.LessonStore;
import com.thesis.capability.OrderStore;
import com.thesis.capability.SlotStore;
import com.thesis.capability.TicketStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.R;
import com.thesis.service.SeatStore;
import com.thesis.service.SurveyStore;
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
 * XD-02 定时任务只读台：列出 DemoScheduleJobs 会扫的项与是否启用，≠ 调度中台。
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
        jobs.add(job(
                "coupon_expire",
                "优惠券过期扫标",
                "扫描已过期的用户券并标过期",
                CouponStore.enabled(),
                "每轮扫描"));
        jobs.add(job(
                "order_timeout_cancel",
                "待付订单超时取消",
                "超时未支付的订单自动取消",
                OrderStore.enabled() && orderTimeoutMinutes > 0,
                orderTimeoutMinutes > 0 ? orderTimeoutMinutes + " 分钟" : "未启用"));
        jobs.add(job(
                "confirm_receive_timeout",
                "确认收货超时办结",
                "超时未确认收货的订单自动完成",
                OrderStore.enabled() && confirmReceiveTimeoutMinutes > 0,
                confirmReceiveTimeoutMinutes > 0 ? confirmReceiveTimeoutMinutes + " 分钟" : "未启用"));
        jobs.add(job(
                "rider_claim_timeout",
                "骑手抢单超时释放",
                "超时未接的骑手单释放回池",
                OrderStore.enabled() && riderClaimTimeoutMinutes > 0,
                riderClaimTimeoutMinutes > 0 ? riderClaimTimeoutMinutes + " 分钟" : "未启用"));
        jobs.add(job(
                "cinema_show_expire",
                "过开场场次下架",
                "影院过场次关闭与占座释放",
                SeatStore.enabled(),
                "每轮扫描"));
        jobs.add(job(
                "archive_start_expire",
                "过开场档案下架",
                "到达开始时间的档案项自动关闭",
                true,
                "每轮扫描"));
        jobs.add(job(
                "ticket_auto_pass",
                "待审超时自动通过",
                "满足规则的待审单据自动通过（默认常关）",
                TicketStore.enabled(),
                "按业务规则"));
        jobs.add(job(
                "ticket_peer_timeout",
                "互选超时自动驳回",
                "超时未回应的互选申请自动驳回",
                TicketStore.enabled(),
                "按业务规则"));
        jobs.add(job(
                "archive_expire_notify",
                "档案临期提醒",
                "临近到期的档案发站内提醒",
                true,
                "每轮扫描"));
        jobs.add(job(
                "survey_open_close",
                "问卷开闭窗",
                "按计划开关问卷并催交",
                SurveyStore.enabled(),
                "每轮扫描"));
        jobs.add(job(
                "slot_remind",
                "预约提前提醒",
                "临近时段的预约发站内提醒",
                SlotStore.enabled() && SlotStore.remindAheadMinutes() > 0,
                SlotStore.enabled() && SlotStore.remindAheadMinutes() > 0
                        ? "提前 " + SlotStore.remindAheadMinutes() + " 分钟"
                        : "未启用"));
        jobs.add(job(
                "lesson_expire_notify",
                "课时临期提醒",
                "临近到期的课时包提醒",
                LessonStore.enabled(),
                "每轮扫描"));
        jobs.add(job(
                "post_mute_clear",
                "禁言到期解除",
                "过期的发帖禁言自动清除",
                true,
                "每轮扫描"));

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("delayMs", scheduleDelayMs);
        out.put("list", jobs);
        return R.ok(out);
    }

    private static Map<String, Object> job(
            String id, String title, String detail, boolean armed, String threshold) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", id);
        m.put("title", title);
        m.put("detail", detail);
        m.put("armed", armed);
        m.put("threshold", threshold);
        return m;
    }
}
