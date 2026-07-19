package com.thesis.config;

import com.thesis.capability.ArchiveStore;
import com.thesis.capability.OrderStore;
import com.thesis.capability.SlotStore;
import com.thesis.capability.TicketLookupStore;
import com.thesis.capability.TicketStore;
import com.thesis.common.PasswordHashes;
import com.thesis.service.UserStore;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * 按 thesis.* 配置绑定能力运行时（薄领域无专用 Store）。
 */
@Component
public class DomainRuntimeBinder {

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

    @Value("${thesis.archive-tag-table:}")
    private String archiveTagTable;

    @Value("${thesis.archive-item-tag-table:}")
    private String archiveItemTagTable;

    @Value("${thesis.ticket-week-calendar:false}")
    private boolean ticketWeekCalendar;

    @Value("${thesis.ticket-allow-checkin:false}")
    private boolean ticketAllowCheckin;

    @Value("${thesis.ticket-pick-loan-period:false}")
    private boolean ticketPickLoanPeriod;

    @Value("${thesis.ticket-allow-qty:false}")
    private boolean ticketAllowQty;

    @Value("${thesis.ticket-require-remark:false}")
    private boolean ticketRequireRemark;

    @Value("${thesis.ticket-pick-date-range:false}")
    private boolean ticketPickDateRange;

    @Value("${thesis.slot-require-remark:false}")
    private boolean slotRequireRemark;

    @PostConstruct
    public void bind() {
        ArchiveStore.bind(archiveCategoryTable, archiveItemTable);
        ArchiveStore.configureSoftDelete(archiveSoftDelete);
        if (archiveTagTable != null && !archiveTagTable.isBlank()) {
            ArchiveStore.bindTags(archiveTagTable, archiveItemTagTable);
        }
        if (ticketAllowCheckin) {
            ArchiveStore.ensureCheckinCodeColumn();
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
            TicketStore.configureLoanOptions(ticketPickLoanPeriod, ticketAllowQty);
            TicketStore.configureApplyExtras(ticketRequireRemark, ticketPickDateRange);
        }
        if (orderCartTable != null && !orderCartTable.isBlank()) {
            OrderStore.bind(orderCartTable, orderTable, orderLineTable, useQuota);
        } else {
            OrderStore.unbind();
        }
        if (slotTable != null && !slotTable.isBlank()) {
            SlotStore.bind(slotTable, reservationTable);
            SlotStore.configureRemark(slotRequireRemark);
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
