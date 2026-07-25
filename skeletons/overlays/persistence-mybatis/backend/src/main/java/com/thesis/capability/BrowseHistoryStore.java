package com.thesis.capability;

import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.thesis.config.MybatisSupport;
import com.thesis.mapper.BrowseHistoryMapper;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 能力 browse_history：最近浏览足迹（user_browse_history）。 */
public final class BrowseHistoryStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static boolean enabled = false;
    private static int limit = 20;

    private BrowseHistoryStore() {}

    private static BrowseHistoryMapper mapper() {
        return MybatisSupport.mapper(BrowseHistoryMapper.class);
    }

    public static void configure(boolean on, int maxKeep) {
        enabled = on;
        limit = maxKeep > 0 ? Math.min(maxKeep, 50) : 20;
        if (enabled) {
            try {
                mapper().ensureTable();
            } catch (Exception ignored) {
            }
        }
    }

    public static boolean enabled() {
        return enabled;
    }

    public static void touch(String username, long itemId) {
        if (!enabled || username == null || username.isBlank() || itemId <= 0) return;
        if (ArchiveStore.getItemRaw(itemId) == null) return;
        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        if (mapper().count(username, itemId) > 0) {
            mapper().touch(now, username, itemId);
        } else {
            mapper().insert(username, itemId, now);
        }
        trim(username);
    }

    private static void trim(String username) {
        try {
            List<Long> ids = mapper().selectIdsByUsername(username);
            if (ids == null || ids.size() <= limit) return;
            for (int i = limit; i < ids.size(); i++) {
                mapper().deleteById(ids.get(i));
            }
        } catch (Exception ignored) {
        }
    }

    public static Map<String, Object> page(String username, int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        PageHelper.startPage(page, size);
        List<Map<String, Object>> raw = mapper().selectByUsername(username);
        PageInfo<Map<String, Object>> pi = new PageInfo<>(raw);
        List<Map<String, Object>> rows = new ArrayList<>();
        for (Map<String, Object> r : raw) {
            Map<String, Object> m = new LinkedHashMap<>();
            long itemId = ((Number) r.get("itemId")).longValue();
            m.put("itemId", itemId);
            Object ts = r.get("viewedAt");
            if (ts instanceof Timestamp t) {
                m.put("viewedAt", t.toLocalDateTime().format(FMT));
            } else {
                m.put("viewedAt", ts == null ? null : String.valueOf(ts));
            }
            Map<String, Object> item = ArchiveStore.getItem(itemId);
            if (item != null) {
                m.putAll(item);
                m.put("id", itemId);
            } else {
                m.put("id", itemId);
                m.put("title", "已下架");
            }
            rows.add(m);
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", rows);
        out.put("total", pi.getTotal());
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    public static List<Long> idsOf(String username) {
        if (!enabled || username == null || username.isBlank()) return List.of();
        try {
            List<Long> ids = mapper().selectItemIds(username);
            return ids == null ? List.of() : ids;
        } catch (Exception e) {
            return List.of();
        }
    }

    public static boolean clear(String username) {
        require();
        return mapper().clear(username) >= 0;
    }

    private static void require() {
        if (!enabled) throw new IllegalStateException("浏览历史暂不可用");
    }
}
