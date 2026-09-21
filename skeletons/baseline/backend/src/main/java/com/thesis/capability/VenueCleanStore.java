package com.thesis.capability;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.util.List;
import java.util.Map;

/**
 * 场馆/会议室保洁：档案表 clean_status 待清洁↔已清洁。
 * 不碰酒店 room_instance。
 */
public final class VenueCleanStore {
    public static final String DIRTY = "待清洁";
    public static final String CLEAN = "已清洁";

    private static volatile boolean enabled;
    private static volatile Boolean hasCol;

    private VenueCleanStore() {}

    public static void configure(boolean on) {
        enabled = on;
        hasCol = null;
        if (enabled) {
            ensureColumn();
        }
    }

    public static boolean enabled() {
        return enabled;
    }

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    private static String itemTable() {
        String t = ArchiveStore.itemTable();
        if (t == null || t.isBlank()) {
            throw new IllegalStateException("未绑定档案表");
        }
        return t;
    }

    private static void ensureColumn() {
        try {
            db().execute(
                    "ALTER TABLE `" + itemTable() + "` ADD COLUMN `clean_status` VARCHAR(16) NOT NULL DEFAULT ''");
        } catch (Exception ignored) {
        }
        hasCol = null;
    }

    private static boolean hasCleanStatus() {
        if (!enabled) return false;
        if (hasCol == null) {
            try {
                Integer n = db().queryForObject(
                        "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE()"
                                + " AND TABLE_NAME=? AND COLUMN_NAME='clean_status'",
                        Integer.class,
                        itemTable());
                hasCol = n != null && n > 0;
            } catch (Exception e) {
                hasCol = false;
            }
        }
        return Boolean.TRUE.equals(hasCol);
    }

    public static void requireEnabled() {
        if (!enabled || !hasCleanStatus()) {
            throw new IllegalStateException("未开启场馆保洁");
        }
    }

    public static List<Map<String, Object>> dirtyList() {
        requireEnabled();
        String soft = ArchiveStore.softDeleteEnabled() ? " AND deleted_at IS NULL" : "";
        return db().queryForList(
                "SELECT id, title, clean_status AS cleanStatus FROM `" + itemTable()
                        + "` WHERE clean_status=? " + soft + " ORDER BY id",
                DIRTY);
    }

    public static List<Map<String, Object>> listAll() {
        requireEnabled();
        String soft = ArchiveStore.softDeleteEnabled() ? " AND deleted_at IS NULL" : "";
        return db().queryForList(
                "SELECT id, title, clean_status AS cleanStatus FROM `" + itemTable()
                        + "` WHERE 1=1 " + soft + " ORDER BY id");
    }

    public static void markDirty(long itemId) {
        requireEnabled();
        int n = db().update(
                "UPDATE `" + itemTable() + "` SET clean_status=? WHERE id=?",
                DIRTY,
                itemId);
        if (n == 0) throw new IllegalArgumentException("场地不存在");
    }

    public static void markClean(long itemId) {
        requireEnabled();
        int n = db().update(
                "UPDATE `" + itemTable() + "` SET clean_status=? WHERE id=? AND clean_status=?",
                CLEAN,
                itemId,
                DIRTY);
        if (n == 0) throw new IllegalStateException("仅待清洁项可完成打扫");
    }

    /** 预约办结后标待清洁（会议室等毕设常见：用完需清扫）。 */
    public static void markDirtyAfterReservation(long itemId) {
        if (!enabled || !hasCleanStatus() || itemId <= 0) return;
        try {
            db().update(
                    "UPDATE `" + itemTable() + "` SET clean_status=? WHERE id=?",
                    DIRTY,
                    itemId);
        } catch (Exception ignored) {
        }
    }
}
