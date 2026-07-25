package com.thesis.capability;

import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.thesis.config.MybatisSupport;
import com.thesis.mapper.FavoriteMapper;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 能力 favorites：即时收藏夹（user_favorite）；交易/内容流共用。 */
public final class FavoriteStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static boolean enabled = false;

    private FavoriteStore() {}

    private static FavoriteMapper mapper() {
        return MybatisSupport.mapper(FavoriteMapper.class);
    }

    public static void configure(boolean on) {
        enabled = on;
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

    public static boolean toggle(String username, long itemId) {
        require();
        if (ArchiveStore.getItemRaw(itemId) == null) {
            throw new IllegalArgumentException("对象不存在");
        }
        if (mapper().count(username, itemId) > 0) {
            mapper().delete(username, itemId);
            return false;
        }
        mapper().insert(username, itemId, Timestamp.valueOf(LocalDateTime.now()));
        return true;
    }

    public static boolean isFav(String username, long itemId) {
        if (!enabled || username == null || username.isBlank() || itemId <= 0) return false;
        return mapper().count(username, itemId) > 0;
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
            Object ts = r.get("createdAt");
            if (ts instanceof Timestamp t) {
                m.put("createdAt", t.toLocalDateTime().format(FMT));
            } else {
                m.put("createdAt", ts == null ? null : String.valueOf(ts));
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
        List<Long> ids = mapper().selectItemIds(username);
        return ids == null ? List.of() : new ArrayList<>(ids);
    }

    private static void require() {
        if (!enabled) throw new IllegalStateException("收藏功能暂不可用");
    }
}
