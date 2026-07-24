package com.thesis.config;

import com.thesis.capability.ArchiveLogStore;
import com.thesis.capability.ArchiveStore;
import com.thesis.capability.BrowseHistoryStore;
import com.thesis.capability.CouponStore;
import com.thesis.capability.FavoriteStore;
import com.thesis.capability.LoyaltyStore;
import com.thesis.capability.OrderReviewStore;
import com.thesis.capability.OrderStore;
import com.thesis.capability.SlotStore;
import com.thesis.capability.TicketLookupStore;
import com.thesis.capability.TicketStore;
import com.thesis.common.PasswordHashes;
import com.thesis.service.UserStore;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

/**
 * 按 thesis.* 配置绑定能力运行时（薄领域无专用 Store）。
 * 用 ApplicationRunner：保证 JdbcSupport 已注入后再 ensureStaffColumns。
 */
@Component
@Order(0)
public class DomainRuntimeBinder implements ApplicationRunner {

    @Value("${thesis.ticket-mode:archive}")
    private String ticketMode;

    @Value("${thesis.ticket-table:borrow}")
    private String ticketTable;

    @Value("${thesis.enable-ticket:true}")
    private boolean enableTicket;

    @Value("${thesis.archive-category-table:category}")
    private String archiveCategoryTable;

    @Value("${thesis.archive-item-table:book}")
    private String archiveItemTable;

    @Value("${thesis.register-role:user}")
    private String registerRole;

    @Value("${thesis.password-hash:none}")
    private String passwordHash;

    @Value("${thesis.lookup-site-table:}")
    private String lookupSiteTable;

    @Value("${thesis.lookup-unit-table:}")
    private String lookupUnitTable;

    @Value("${thesis.lookup-type-table:}")
    private String lookupTypeTable;

    @Value("${thesis.lookup-site-label:楼栋}")
    private String lookupSiteLabel;

    @Value("${thesis.lookup-unit-label:房间}")
    private String lookupUnitLabel;

    @Value("${thesis.lookup-type-label:类型}")
    private String lookupTypeLabel;

    @Value("${thesis.use-quota:true}")
    private boolean useQuota;

    @Value("${thesis.use-deadline:true}")
    private boolean useDeadline;

    @Value("${thesis.allow-multi-ticket:false}")
    private boolean allowMultiTicket;

    @Value("${thesis.check-time-conflict:false}")
    private boolean checkTimeConflict;

    @Value("${thesis.order-cart-table:}")
    private String orderCartTable;

    @Value("${thesis.order-table:}")
    private String orderTable;

    @Value("${thesis.order-line-table:}")
    private String orderLineTable;

    @Value("${thesis.slot-table:}")
    private String slotTable;

    @Value("${thesis.reservation-table:}")
    private String reservationTable;

    @Value("${thesis.ticket-two-level:false}")
    private boolean ticketTwoLevel;

    @Value("${thesis.ticket-require-attach:false}")
    private boolean ticketRequireAttach;

    @Value("${thesis.ticket-allow-rating:false}")
    private boolean ticketAllowRating;

    @Value("${thesis.ticket-check-mutex:false}")
    private boolean ticketCheckMutex;

    @Value("${thesis.ticket-category-limit:0}")
    private int ticketCategoryLimit;

    @Value("${thesis.archive-soft-delete:false}")
    private boolean archiveSoftDelete;

    @Value("${thesis.archive-user-publish:false}")
    private boolean archiveUserPublish;

    @Value("${thesis.archive-tag-table:}")
    private String archiveTagTable;

    @Value("${thesis.archive-item-tag-table:}")
    private String archiveItemTagTable;

    @Value("${thesis.ticket-week-calendar:false}")
    private boolean ticketWeekCalendar;

    @Value("${thesis.ticket-allow-checkin:false}")
    private boolean ticketAllowCheckin;

    @Value("${thesis.ticket-no-show-after-end:false}")
    private boolean ticketNoShowAfterEnd;

    @Value("${thesis.ticket-no-show-penalty-yuan:0}")
    private double ticketNoShowPenaltyYuan;

    @Value("${thesis.ticket-pick-loan-period:false}")
    private boolean ticketPickLoanPeriod;

    @Value("${thesis.ticket-allow-qty:false}")
    private boolean ticketAllowQty;

    @Value("${thesis.ticket-require-remark:false}")
    private boolean ticketRequireRemark;

    @Value("${thesis.ticket-pick-date-range:false}")
    private boolean ticketPickDateRange;

    @Value("${thesis.ticket-approve-ends-flow:false}")
    private boolean ticketApproveEndsFlow;

    @Value("${thesis.ticket-auto-approve:false}")
    private boolean ticketAutoApprove;

    @Value("${thesis.slot-require-remark:false}")
    private boolean slotRequireRemark;

    @Value("${thesis.slot-require-confirm:false}")
    private boolean slotRequireConfirm;

    @Value("${thesis.wallet-enabled:false}")
    private boolean walletEnabled;

    @Value("${thesis.points-enabled:false}")
    private boolean pointsEnabled;

    @Value("${thesis.spend-discount-enabled:false}")
    private boolean spendDiscountEnabled;

    @Value("${thesis.member-tier-enabled:false}")
    private boolean memberTierEnabled;

    @Value("${thesis.coupon-enabled:false}")
    private boolean couponEnabled;

    @Value("${thesis.order-review-enabled:false}")
    private boolean orderReviewEnabled;

    @Value("${thesis.favorites-enabled:false}")
    private boolean favoritesEnabled;

    @Value("${thesis.browse-history-enabled:false}")
    private boolean browseHistoryEnabled;

    @Value("${thesis.archive-log-enabled:false}")
    private boolean archiveLogEnabled;

    @Value("${thesis.gallery-enabled:false}")
    private boolean galleryEnabled;

    @Value("${thesis.points-earn-per-yuan:1}")
    private int pointsEarnPerYuan;

    @Value("${thesis.spend-discount-threshold-yuan:100}")
    private double spendDiscountThresholdYuan;

    @Value("${thesis.spend-discount-off-yuan:10}")
    private double spendDiscountOffYuan;

    @Override
    public void run(ApplicationArguments args) {
        ArchiveStore.bind(archiveCategoryTable, archiveItemTable);
        ArchiveStore.configureSoftDelete(archiveSoftDelete);
        ArchiveStore.configureUserPublish(archiveUserPublish);
        ArchiveStore.configureGallery(galleryEnabled);
        if (archiveTagTable != null && !archiveTagTable.isBlank()) {
            ArchiveStore.bindTags(archiveTagTable, archiveItemTagTable);
        }
        if (ticketAllowCheckin) {
            // checkin_code 由 bake 写入档案表；此处不再 ALTER
        }
        if (enableTicket && ticketTable != null && !ticketTable.isBlank()) {
            if ("standalone".equalsIgnoreCase(ticketMode)) {
                TicketStore.bindStandalone(ticketTable);
            } else {
                TicketStore.bind(ticketTable, useQuota, useDeadline, allowMultiTicket, checkTimeConflict);
            }
            TicketStore.setUserRole(registerRole);
            TicketStore.configureL1(ticketTwoLevel, ticketRequireAttach, ticketAllowRating);
            TicketStore.configureRules(ticketCheckMutex, ticketCategoryLimit);
            TicketStore.configureCheckin(ticketAllowCheckin);
            TicketStore.configureNoShow(ticketNoShowAfterEnd, ticketNoShowPenaltyYuan);
            TicketStore.configureLoanOptions(ticketPickLoanPeriod, ticketAllowQty);
            TicketStore.configureApplyExtras(ticketRequireRemark, ticketPickDateRange);
            TicketStore.configureApproveEndsFlow(ticketApproveEndsFlow);
            TicketStore.configureAutoApprove(ticketAutoApprove);
        }
        LoyaltyStore.configure(
                walletEnabled,
                pointsEnabled,
                spendDiscountEnabled,
                memberTierEnabled,
                couponEnabled,
                pointsEarnPerYuan,
                spendDiscountThresholdYuan,
                spendDiscountOffYuan);
        CouponStore.configure(couponEnabled);
        if (orderCartTable != null && !orderCartTable.isBlank()) {
            OrderStore.bind(orderCartTable, orderTable, orderLineTable, useQuota);
        } else {
            OrderStore.unbind();
        }
        OrderReviewStore.configure(orderReviewEnabled);
        FavoriteStore.configure(favoritesEnabled);
        BrowseHistoryStore.configure(browseHistoryEnabled, 20);
        ArchiveLogStore.configure(archiveLogEnabled);
        if (slotTable != null && !slotTable.isBlank()) {
            SlotStore.bind(slotTable, reservationTable);
            SlotStore.configureRemark(slotRequireRemark);
            SlotStore.configureConfirm(slotRequireConfirm);
        } else {
            SlotStore.unbind();
        }
        PasswordHashes.bind(passwordHash);
        TicketLookupStore.bind(
                lookupSiteTable,
                lookupUnitTable,
                lookupTypeTable,
                lookupSiteLabel,
                lookupUnitLabel,
                lookupTypeLabel);
        UserStore.ensureStaffColumns();
    }
}
