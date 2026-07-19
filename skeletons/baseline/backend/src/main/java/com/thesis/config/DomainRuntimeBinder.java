package com.thesis.config;

import com.thesis.capability.ArchiveStore;
import com.thesis.capability.TicketLookupStore;
import com.thesis.capability.TicketStore;
import com.thesis.common.PasswordHashes;
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

    @PostConstruct
    public void bind() {
        ArchiveStore.bind(archiveCategoryTable, archiveItemTable);
        if ("standalone".equalsIgnoreCase(ticketMode)) {
            TicketStore.bindStandalone(ticketTable);
        } else {
            TicketStore.bind(ticketTable, useQuota, useDeadline, allowMultiTicket, checkTimeConflict);
        }
        TicketStore.setUserRole(registerRole);
        PasswordHashes.bind(passwordHash);
        TicketLookupStore.bind(
                lookupSiteTable,
                lookupUnitTable,
                lookupTypeTable,
                lookupSiteLabel,
                lookupUnitLabel,
                lookupTypeLabel);
    }
}
