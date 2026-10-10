package com.thesis.capability;

/**
 * ArchiveCfgOps：纯开关配置（不含 DDL ensure）。
 * package-private；ArchiveStore 保留 public 门面。
 */
final class ArchiveCfgOps {

    private ArchiveCfgOps() {}

    static void configureStockWarn(boolean notify, int below) {
        ArchiveStore.stockWarnNotify = notify;
        ArchiveStore.stockWarnBelow = Math.max(1, Math.min(999, below <= 0 ? 10 : below));
    }

    static void configureStockLabel(String label) {
        if (label != null && !label.isBlank()) {
            ArchiveStore.STOCK_LABEL = label.trim();
        }
    }

    static void configureSoftDelete(boolean enabled) {
        ArchiveStore.softDeleteEnabled = enabled;
    }

    static void configureUserPublish(boolean enabled) {
        ArchiveStore.userPublishEnabled = enabled;
    }

    static void configurePublishReview(boolean enabled) {
        ArchiveStore.publishReviewEnabled = enabled;
    }

    static void configureForumDailyPostLimit(int limit) {
        ArchiveStore.forumDailyPostLimit = Math.max(0, limit);
    }

    static void configureShopMarketplace(boolean enabled) {
        ArchiveStore.shopMarketplaceEnabled = enabled;
    }

    static void configureMultiCategory(boolean enabled) {
        ArchiveStore.multiCategoryEnabled = enabled;
        ArchiveStore.hasDimensionCol = null;
    }
}
