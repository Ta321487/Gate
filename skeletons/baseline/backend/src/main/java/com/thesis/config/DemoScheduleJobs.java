package com.thesis.config;

import com.thesis.capability.ArchiveStore;
import com.thesis.capability.CouponStore;
import com.thesis.capability.OrderStore;
import com.thesis.service.SeatStore;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/** 演示定时任务：券过期扫标 + 订单超时自动取消 + 确认收货超时办结 + 过开场/出发下架。 */
@Component
public class DemoScheduleJobs {

    private static final Logger log = LoggerFactory.getLogger(DemoScheduleJobs.class);

    @Value("${thesis.order-timeout-minutes:0}")
    private int orderTimeoutMinutes;

    @Value("${thesis.confirm-receive-timeout-minutes:0}")
    private int confirmReceiveTimeoutMinutes;

    @Value("${thesis.rider-claim-timeout-minutes:0}")
    private int riderClaimTimeoutMinutes;

    @Scheduled(fixedDelayString = "${thesis.schedule-delay-ms:60000}")
    public void tick() {
        try {
            if (CouponStore.enabled()) {
                int n = CouponStore.expireSweep();
                if (n > 0) log.debug("expired {} user coupons", n);
            }
        } catch (Exception e) {
            log.debug("coupon expire sweep: {}", e.getMessage());
        }
        try {
            if (orderTimeoutMinutes > 0 && OrderStore.enabled()) {
                int n = OrderStore.cancelTimedOutPending(orderTimeoutMinutes);
                if (n > 0) log.info("auto-cancelled {} timed-out orders", n);
            }
        } catch (Exception e) {
            log.debug("order timeout cancel: {}", e.getMessage());
        }
        try {
            if (confirmReceiveTimeoutMinutes > 0 && OrderStore.enabled()) {
                int n = OrderStore.completeTimedOutUnreceived(confirmReceiveTimeoutMinutes);
                if (n > 0) log.info("auto-completed {} unreceived orders", n);
            }
        } catch (Exception e) {
            log.debug("confirm-receive timeout: {}", e.getMessage());
        }
        try {
            if (riderClaimTimeoutMinutes > 0 && OrderStore.enabled()) {
                int n = OrderStore.releaseTimedOutRiderClaims(riderClaimTimeoutMinutes);
                if (n > 0) log.info("released {} timed-out rider claims", n);
            }
        } catch (Exception e) {
            log.debug("rider claim timeout: {}", e.getMessage());
        }
        try {
            if (SeatStore.enabled()) {
                int n = SeatStore.expirePastShows();
                if (n > 0) log.info("auto-closed {} past-start cinema shows", n);
                int h = SeatStore.releaseExpiredHolds();
                if (h > 0) log.info("released {} expired cinema holds", h);
                SeatStore.syncSoldOutShows();
            }
        } catch (Exception e) {
            log.debug("cinema show expire: {}", e.getMessage());
        }
        try {
            int n = ArchiveStore.expirePastStarts();
            if (n > 0) log.info("auto-closed {} past-start archive items", n);
        } catch (Exception e) {
            log.debug("archive start expire: {}", e.getMessage());
        }
        try {
            int n = com.thesis.capability.TicketStore.autoPassStalePending();
            if (n > 0) log.info("auto-passed {} stale pending tickets", n);
        } catch (Exception e) {
            log.debug("approve auto-pass: {}", e.getMessage());
        }
        try {
            int n = ArchiveStore.maybeNotifyExpireSoon();
            if (n > 0) log.info("archive expire-soon notified {} items", n);
        } catch (Exception e) {
            log.debug("archive expire-soon notify: {}", e.getMessage());
        }
        try {
            if (com.thesis.capability.SlotStore.enabled()
                    && com.thesis.capability.SlotStore.remindAheadMinutes() > 0) {
                int n = com.thesis.capability.SlotStore.remindDueSweep();
                if (n > 0) log.info("reservation remind sent {}", n);
            }
        } catch (Exception e) {
            log.debug("reservation remind: {}", e.getMessage());
        }
        try {
            if (com.thesis.capability.LessonStore.enabled()) {
                int n = com.thesis.capability.LessonStore.expireSoonNotify();
                if (n > 0) log.info("lesson expire-soon notified {}", n);
            }
        } catch (Exception e) {
            log.debug("lesson expire-soon notify: {}", e.getMessage());
        }
        try {
            int n = com.thesis.service.UserStore.clearExpiredPostMutes();
            if (n > 0) log.info("cleared {} expired post mutes", n);
        } catch (Exception e) {
            log.debug("post mute expire: {}", e.getMessage());
        }
    }
}
