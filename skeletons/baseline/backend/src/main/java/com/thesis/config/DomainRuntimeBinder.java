package com.thesis.config;

import com.thesis.capability.ArchiveLogStore;
import com.thesis.capability.AuditLogStore;
import com.thesis.capability.StaffRosterStore;
import com.thesis.capability.BookSuggestStore;
import com.thesis.capability.EquipmentDictStore;
import com.thesis.capability.ArchiveStore;
import com.thesis.capability.BrowseHistoryStore;
import com.thesis.capability.CouponStore;
import com.thesis.capability.ConsignStore;
import com.thesis.capability.WeighSaleStore;
import com.thesis.capability.ShootStore;
import com.thesis.capability.BoardingStore;
import com.thesis.capability.BuybackStore;
import com.thesis.capability.DigitalGoodsStore;
import com.thesis.capability.RentalBondStore;
import com.thesis.capability.LessonStore;
import com.thesis.capability.DeliveryWindowStore;
import com.thesis.capability.BlindBoxStore;
import com.thesis.capability.GroupBuyStore;
import com.thesis.capability.PurchaseGateStore;
import com.thesis.capability.FavoriteStore;
import com.thesis.capability.LineCustomStore;
import com.thesis.capability.LoyaltyStore;
import com.thesis.capability.OrderReviewStore;
import com.thesis.capability.OrderStore;
import com.thesis.capability.SlotStore;
import com.thesis.capability.TicketLookupStore;
import com.thesis.capability.TicketStore;
import com.thesis.common.PasswordHashes;
import com.thesis.service.MessageStore;
import com.thesis.service.DmStore;
import com.thesis.service.ExamStore;
import com.thesis.service.SurveyStore;
import com.thesis.service.UserStore;
import com.thesis.service.VoteStore;
import com.thesis.service.BalanceLedgerStore;
import com.thesis.service.GradeScoreStore;
import com.thesis.service.DoclibStore;
import com.thesis.service.ESignStore;
import com.thesis.service.MaterialCheckStore;
import com.thesis.service.ClaimProofStore;
import com.thesis.service.LostMessageStore;
import com.thesis.service.OccupySpanStore;
import com.thesis.service.SeatStore;
import com.thesis.service.StockIoStore;
import com.thesis.service.TimebankStore;
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

    /** 空串 = 管理端不展示单元容量列 */
    @Value("${thesis.lookup-unit-capacity-label:容量}")
    private String lookupUnitCapacityLabel;

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

    @Value("${thesis.ticket-three-level:false}")
    private boolean ticketThreeLevel;

    @Value("${thesis.ticket-require-attach:false}")
    private boolean ticketRequireAttach;

    @Value("${thesis.ticket-allow-rating:false}")
    private boolean ticketAllowRating;

    @Value("${thesis.ticket-check-mutex:false}")
    private boolean ticketCheckMutex;

    @Value("${thesis.ticket-category-limit:0}")
    private int ticketCategoryLimit;

    @Value("${thesis.ticket-loan-days:0}")
    private int ticketLoanDays;

    @Value("${thesis.ticket-max-active:0}")
    private int ticketMaxActive;

    @Value("${thesis.ticket-fine-per-day:-1}")
    private double ticketFinePerDay;

    @Value("${thesis.ticket-pickup-place:}")
    private String ticketPickupPlace;

    @Value("${thesis.archive-soft-delete:false}")
    private boolean archiveSoftDelete;

    @Value("${thesis.archive-user-publish:false}")
    private boolean archiveUserPublish;

    @Value("${thesis.archive-publish-review:false}")
    private boolean archivePublishReview;

    @Value("${thesis.archive-tag-table:}")
    private String archiveTagTable;

    @Value("${thesis.archive-item-tag-table:}")
    private String archiveItemTagTable;

    @Value("${thesis.ticket-week-calendar:false}")
    private boolean ticketWeekCalendar;

    @Value("${thesis.ticket-allow-checkin:false}")
    private boolean ticketAllowCheckin;

    @Value("${thesis.ticket-peer-accept:false}")
    private boolean ticketPeerAccept;

    @Value("${thesis.ticket-issue-pass-code:false}")
    private boolean ticketIssuePassCode;

    @Value("${thesis.ticket-allow-renew:false}")
    private boolean ticketAllowRenew;

    @Value("${thesis.ticket-allow-waitlist:false}")
    private boolean ticketAllowWaitlist;

    @Value("${thesis.ticket-allow-book-hold:false}")
    private boolean ticketAllowBookHold;

    @Value("${thesis.ticket-hold-hours:48}")
    private int ticketHoldHours;

    @Value("${thesis.ticket-max-renew:1}")
    private int ticketMaxRenew;

    @Value("${thesis.ticket-renew-days:0}")
    private int ticketRenewDays;

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

    @Value("${thesis.ticket-require-claim-code:false}")
    private boolean ticketRequireClaimCode;

    @Value("${thesis.ticket-match-profile-room:false}")
    private boolean ticketMatchProfileRoom;

    @Value("${thesis.ticket-match-profile-building-key:}")
    private String ticketMatchProfileBuildingKey;

    @Value("${thesis.ticket-match-profile-room-key:}")
    private String ticketMatchProfileRoomKey;

    @Value("${thesis.ticket-match-profile-building-field:}")
    private String ticketMatchProfileBuildingField;

    @Value("${thesis.ticket-match-profile-room-field:}")
    private String ticketMatchProfileRoomField;

    @Value("${thesis.ticket-match-profile-loose-building:false}")
    private boolean ticketMatchProfileLooseBuilding;

    @Value("${thesis.ticket-match-profile-need-message:}")
    private String ticketMatchProfileNeedMessage;

    @Value("${thesis.ticket-match-profile-deny-message:}")
    private String ticketMatchProfileDenyMessage;

    @Value("${thesis.ticket-applicant-complete-only:false}")
    private boolean ticketApplicantCompleteOnly;

    @Value("${thesis.slot-require-remark:false}")
    private boolean slotRequireRemark;

    @Value("${thesis.slot-require-confirm:false}")
    private boolean slotRequireConfirm;

    @Value("${thesis.slot-allow-rating:false}")
    private boolean slotAllowRating;

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

    @Value("${thesis.line-custom-enabled:false}")
    private boolean lineCustomEnabled;

    @Value("${thesis.line-custom-place-confirmed:false}")
    private boolean lineCustomPlaceConfirmed;

    @Value("${thesis.delivery-window-enabled:false}")
    private boolean deliveryWindowEnabled;

    @Value("${thesis.purchase-gate-enabled:false}")
    private boolean purchaseGateEnabled;

    @Value("${thesis.group-buy-enabled:false}")
    private boolean groupBuyEnabled;

    @Value("${thesis.blind-box-enabled:false}")
    private boolean blindBoxEnabled;

    @Value("${thesis.consign-enabled:false}")
    private boolean consignEnabled;

    @Value("${thesis.weigh-sale-enabled:false}")
    private boolean weighSaleEnabled;

    @Value("${thesis.shoot-enabled:false}")
    private boolean shootEnabled;

    @Value("${thesis.boarding-enabled:false}")
    private boolean boardingEnabled;

    @Value("${thesis.buyback-enabled:false}")
    private boolean buybackEnabled;

    @Value("${thesis.lesson-pack-enabled:false}")
    private boolean lessonPackEnabled;

    @Value("${thesis.rental-bond-enabled:false}")
    private boolean rentalBondEnabled;

    @Value("${thesis.digital-goods-enabled:false}")
    private boolean digitalGoodsEnabled;

    @Value("${thesis.no-casual-refund:false}")
    private boolean noCasualRefund;

    @Value("${thesis.favorites-enabled:false}")
    private boolean favoritesEnabled;

    @Value("${thesis.post-like-enabled:false}")
    private boolean postLikeEnabled;

    @Value("${thesis.content-report-enabled:false}")
    private boolean contentReportEnabled;

    @Value("${thesis.post-mute-enabled:false}")
    private boolean postMuteEnabled;

    @Value("${thesis.book-suggest-enabled:false}")
    private boolean bookSuggestEnabled;

    @Value("${thesis.audit-log-enabled:false}")
    private boolean auditLogEnabled;

    @Value("${thesis.message-template-enabled:false}")
    private boolean messageTemplateEnabled;

    @Value("${thesis.staff-roster-enabled:false}")
    private boolean staffRosterEnabled;

    @Value("${thesis.room-equipment-enabled:false}")
    private boolean roomEquipmentEnabled;

    @Value("${thesis.audit-log-login-only:false}")
    private boolean auditLogLoginOnly;

    @Value("${thesis.browse-history-enabled:false}")
    private boolean browseHistoryEnabled;

    @Value("${thesis.archive-log-enabled:false}")
    private boolean archiveLogEnabled;

    @Value("${thesis.exam-enabled:false}")
    private boolean examEnabled;

    @Value("${thesis.exam-practice-enabled:false}")
    private boolean examPracticeEnabled;

    @Value("${thesis.exam-explain-enabled:false}")
    private boolean examExplainEnabled;

    @Value("${thesis.exam-timer-enabled:false}")
    private boolean examTimerEnabled;

    @Value("${thesis.exam-attempt-limit-enabled:false}")
    private boolean examAttemptLimitEnabled;

    @Value("${thesis.exam-rank-enabled:false}")
    private boolean examRankEnabled;

    @Value("${thesis.exam-wrongbook-enabled:false}")
    private boolean examWrongbookEnabled;

    @Value("${thesis.exam-require-before-ticket:false}")
    private boolean examRequireBeforeTicket;

    @Value("${thesis.survey-enabled:false}")
    private boolean surveyEnabled;

    @Value("${thesis.vote-enabled:false}")
    private boolean voteEnabled;

    @Value("${thesis.doclib-enabled:false}")
    private boolean doclibEnabled;

    @Value("${thesis.timebank-enabled:false}")
    private boolean timebankEnabled;

    @Value("${thesis.timebank-redeem-on-approve:false}")
    private boolean timebankRedeemOnApprove;

    /** C-15 影院选座 */
    @Value("${thesis.seat-select-enabled:false}")
    private boolean seatSelectEnabled;

    /** C-17 浅进销存 */
    @Value("${thesis.stock-io-enabled:false}")
    private boolean stockIoEnabled;

    /** E-08 报废 */
    @Value("${thesis.stock-scrap-enabled:false}")
    private boolean stockScrapEnabled;

    /** E-08 盘点 */
    @Value("${thesis.stock-count-enabled:false}")
    private boolean stockCountEnabled;

    /** C-18 本地签章 */
    @Value("${thesis.e-sign-enabled:false}")
    private boolean eSignEnabled;

    @Value("${thesis.balance-ledger-enabled:false}")
    private boolean balanceLedgerEnabled;

    @Value("${thesis.balance-ledger-debit-on-approve:false}")
    private boolean balanceLedgerDebitOnApprove;

    @Value("${thesis.grade-scores-enabled:false}")
    private boolean gradeScoresEnabled;

    @Value("${thesis.occupy-span-enabled:false}")
    private boolean occupySpanEnabled;

    @Value("${thesis.material-check-enabled:false}")
    private boolean materialCheckEnabled;

    @Value("${thesis.claim-proof-enabled:false}")
    private boolean claimProofEnabled;

    @Value("${thesis.lost-clue-enabled:false}")
    private boolean lostClueEnabled;

    @Value("${thesis.gallery-enabled:false}")
    private boolean galleryEnabled;

    @Value("${thesis.flash-price-enabled:false}")
    private boolean flashPriceEnabled;

    @Value("${thesis.product-spec-enabled:false}")
    private boolean productSpecEnabled;

    @Value("${thesis.shop-marketplace:false}")
    private boolean shopMarketplace;

    /** 店铺客服选人 */
    @Value("${thesis.dm-shop-cs:false}")
    private boolean dmShopCs;

    @Value("${thesis.points-earn-per-yuan:1}")
    private int pointsEarnPerYuan;

    @Value("${thesis.points-pay-enabled:false}")
    private boolean pointsPayEnabled;

    @Value("${thesis.points-offset-enabled:false}")
    private boolean pointsOffsetEnabled;

    @Value("${thesis.points-checkin-enabled:false}")
    private boolean pointsCheckInEnabled;

    @Value("${thesis.points-checkin-amount:10}")
    private int pointsCheckInAmount;

    @Value("${thesis.points-expire-enabled:false}")
    private boolean pointsExpireEnabled;

    @Value("${thesis.points-expire-period:year}")
    private String pointsExpirePeriod;

    @Value("${thesis.points-expire-scope:all}")
    private String pointsExpireScope;

    @Value("${thesis.member-tier-basis:spend}")
    private String memberTierBasis;

    @Value("${thesis.spend-discount-threshold-yuan:100}")
    private double spendDiscountThresholdYuan;

    @Value("${thesis.spend-discount-off-yuan:10}")
    private double spendDiscountOffYuan;

    @Override
    public void run(ApplicationArguments args) {
        ArchiveStore.bind(archiveCategoryTable, archiveItemTable);
        ArchiveStore.configureSoftDelete(archiveSoftDelete);
        ArchiveStore.configureUserPublish(archiveUserPublish);
        ArchiveStore.configurePublishReview(archivePublishReview);
        ArchiveStore.configureGallery(galleryEnabled);
        ArchiveStore.configureRoomEquipment(roomEquipmentEnabled);
        ArchiveStore.configureFlashPrice(flashPriceEnabled);
        ArchiveStore.configureProductSpec(productSpecEnabled);
        ArchiveStore.configureShopMarketplace(shopMarketplace);
        DmStore.configureShopCustomerService(dmShopCs);
        if (archiveTagTable != null && !archiveTagTable.isBlank()) {
            ArchiveStore.bindTags(archiveTagTable, archiveItemTagTable);
        }
        if (ticketAllowCheckin) {
            // checkin_code 已随档案表 schema 建好；此处不再 ALTER
        }
        if (enableTicket && ticketTable != null && !ticketTable.isBlank()) {
            if ("standalone".equalsIgnoreCase(ticketMode)) {
                TicketStore.bindStandalone(ticketTable, useDeadline);
            } else {
                TicketStore.bind(ticketTable, useQuota, useDeadline, allowMultiTicket, checkTimeConflict);
            }
            TicketStore.setUserRole(registerRole);
            TicketStore.configureThreeLevel(ticketThreeLevel);
            TicketStore.configureL1(ticketTwoLevel || ticketThreeLevel, ticketRequireAttach, ticketAllowRating);
            TicketStore.configureRules(ticketCheckMutex, ticketCategoryLimit);
            TicketStore.configureBizParams(ticketLoanDays, ticketMaxActive, ticketFinePerDay, ticketPickupPlace);
            TicketStore.configureCheckin(ticketAllowCheckin);
            TicketStore.configurePeerAccept(ticketPeerAccept);
            TicketStore.configureIssuePassCode(ticketIssuePassCode);
            TicketStore.configureRenew(ticketAllowRenew, ticketMaxRenew, ticketRenewDays);
            TicketStore.configureWaitlist(ticketAllowWaitlist);
            TicketStore.configureBookHold(ticketAllowBookHold, ticketHoldHours);
            TicketStore.configureNoShow(ticketNoShowAfterEnd, ticketNoShowPenaltyYuan);
            TicketStore.configureTimebankRedeem(timebankEnabled && timebankRedeemOnApprove);
            TicketStore.configureLoanOptions(ticketPickLoanPeriod, ticketAllowQty);
            TicketStore.configureApplyExtras(ticketRequireRemark, ticketPickDateRange);
            TicketStore.configureApproveEndsFlow(ticketApproveEndsFlow);
            TicketStore.configureAutoApprove(ticketAutoApprove);
            TicketStore.configureRequireClaimCode(ticketRequireClaimCode);
            TicketStore.configureMatchProfileRoom(
                    ticketMatchProfileRoom,
                    ticketMatchProfileBuildingKey,
                    ticketMatchProfileRoomKey,
                    ticketMatchProfileBuildingField,
                    ticketMatchProfileRoomField,
                    ticketMatchProfileLooseBuilding,
                    ticketMatchProfileNeedMessage,
                    ticketMatchProfileDenyMessage);
            TicketStore.configureApplicantCompleteOnly(ticketApplicantCompleteOnly);
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
        LoyaltyStore.configurePointsModes(
                pointsPayEnabled,
                pointsOffsetEnabled,
                pointsCheckInEnabled,
                pointsCheckInAmount,
                pointsExpireEnabled,
                pointsExpirePeriod,
                pointsExpireScope,
                memberTierBasis);
        CouponStore.configure(couponEnabled);
        if (orderCartTable != null && !orderCartTable.isBlank()) {
            OrderStore.bind(orderCartTable, orderTable, orderLineTable, useQuota);
        } else {
            OrderStore.unbind();
        }
        OrderReviewStore.configure(orderReviewEnabled);
        OrderStore.configureLineCustom(lineCustomEnabled, lineCustomPlaceConfirmed, noCasualRefund);
        LineCustomStore.configure(lineCustomEnabled);
        DeliveryWindowStore.configure(deliveryWindowEnabled);
        PurchaseGateStore.configure(purchaseGateEnabled);
        GroupBuyStore.configure(groupBuyEnabled);
        BlindBoxStore.configure(blindBoxEnabled);
        ConsignStore.configure(consignEnabled);
        WeighSaleStore.configure(weighSaleEnabled);
        ShootStore.configure(shootEnabled);
        BoardingStore.configure(boardingEnabled);
        BuybackStore.configure(buybackEnabled);
        LessonStore.configure(lessonPackEnabled);
        RentalBondStore.configure(rentalBondEnabled);
        DigitalGoodsStore.configure(digitalGoodsEnabled);
        FavoriteStore.configure(favoritesEnabled);
        FavoriteStore.configureLike(postLikeEnabled);
        FavoriteStore.configureReport(contentReportEnabled);
        UserStore.configurePostMute(postMuteEnabled);
        BrowseHistoryStore.configure(browseHistoryEnabled, 20);
        ArchiveLogStore.configure(archiveLogEnabled);
        AuditLogStore.configure(auditLogEnabled, auditLogLoginOnly);
        MessageStore.configureTemplate(messageTemplateEnabled);
        StaffRosterStore.configure(staffRosterEnabled);
        BookSuggestStore.configure(bookSuggestEnabled);
        EquipmentDictStore.configure(roomEquipmentEnabled);
        ExamStore.configure(
                examEnabled,
                examPracticeEnabled,
                examExplainEnabled,
                examTimerEnabled,
                examAttemptLimitEnabled,
                examRankEnabled,
                examWrongbookEnabled,
                examRequireBeforeTicket);
        SurveyStore.configure(surveyEnabled);
        VoteStore.configure(voteEnabled);
        DoclibStore.configure(doclibEnabled);
        TimebankStore.configure(timebankEnabled, timebankRedeemOnApprove);
        SeatStore.configure(seatSelectEnabled);
        StockIoStore.configure(stockIoEnabled, stockScrapEnabled, stockCountEnabled);
        ESignStore.configure(eSignEnabled);
        BalanceLedgerStore.configure(balanceLedgerEnabled, balanceLedgerDebitOnApprove);
        GradeScoreStore.configure(gradeScoresEnabled);
        OccupySpanStore.configure(occupySpanEnabled);
        MaterialCheckStore.configure(materialCheckEnabled);
        ClaimProofStore.configure(claimProofEnabled);
        LostMessageStore.configure(lostClueEnabled);
        if (slotTable != null && !slotTable.isBlank()) {
            SlotStore.bind(slotTable, reservationTable);
            SlotStore.configureRemark(slotRequireRemark);
            SlotStore.configureConfirm(slotRequireConfirm);
            SlotStore.configureRating(slotAllowRating);
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
                lookupTypeLabel,
                lookupUnitCapacityLabel);
        UserStore.ensureStaffColumns();
    }
}
