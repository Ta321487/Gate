package com.thesis.config;

import com.thesis.capability.CouponStore;
import com.thesis.capability.OrderStore;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/** 演示定时任务：券过期扫标 + 订单超时自动取消。 */
@Component
public class DemoScheduleJobs {

    private static final Logger log = LoggerFactory.getLogger(DemoScheduleJobs.class);

    @Value("${thesis.order-timeout-minutes:0}")
    private int orderTimeoutMinutes;

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
    }
}
