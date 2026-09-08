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
import java.util.Locale;
import java.util.Map;

/** 能力 favorites：即时收藏夹（user_favorite）；E-03 同文件扩展点赞 / 举报。 */
public final class FavoriteStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static boolean enabled = false;
    private static boolean likeEnabled = false;
    private static boolean reportEnabled = false;

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

    public static void configureLike(boolean on) {
        likeEnabled = on;
        if (likeEnabled) {
            try {
                mapper().ensureLikeTable();
                String item = ArchiveStore.itemTable();
                if (item != null && !item.isBlank()) {
                    try {
                        mapper().ensureLikeCountColumn(item);
                    } catch (Exception ignored) {
                        // 列已存在
                    }
                }
            } catch (Exception ignored) {
            }
        }
    }

    public static void configureReport(boolean on) {
        reportEnabled = on;
        if (reportEnabled) {
            try {
                mapper().ensureReportTable();
            } catch (Exception ignored) {
            }
        }
    }

    public static boolean enabled() {
        return enabled;
    }

    public static boolean likeEnabled() {
        return likeEnabled;
    }

    public static boolean reportEnabled() {
        return reportEnabled;
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

    /** @return true=已赞，false=取消赞 */
    public static boolean toggleLike(String username, long itemId) {
        requireLike();
        if (ArchiveStore.getItemRaw(itemId) == null) {
            throw new IllegalArgumentException("对象不存在");
        }
        if (mapper().countLike(username, itemId) > 0) {
            mapper().deleteLike(username, itemId);
            bumpLikeCount(itemId, -1);
            return false;
        }
        mapper().insertLike(username, itemId, Timestamp.valueOf(LocalDateTime.now()));
        bumpLikeCount(itemId, 1);
        return true;
    }

    private static void bumpLikeCount(long itemId, int delta) {
        String item = ArchiveStore.itemTable();
        if (item == null || item.isBlank()) return;
        try {
            mapper().bumpLikeCount(item, itemId, delta);
        } catch (Exception ignored) {
            // 无 like_count 列时忽略计数
        }
    }

    public static boolean isLiked(String username, long itemId) {
        if (!likeEnabled || username == null || username.isBlank() || itemId <= 0) return false;
        return mapper().countLike(username, itemId) > 0;
    }

    public static List<Long> likedIdsOf(String username) {
        if (!likeEnabled || username == null || username.isBlank()) return List.of();
        List<Long> ids = mapper().selectLikedItemIds(username);
        return ids == null ? List.of() : new ArrayList<>(ids);
    }

    public static Map<String, Object> submitReport(
            String username, String targetType, long targetId, String reason) {
        requireReport();
        String type = targetType == null || targetType.isBlank() ? "archive" : targetType.trim();
        if (!"archive".equals(type) && !"ticket".equals(type)) {
            throw new IllegalArgumentException("不支持的举报对象类型");
        }
        String note = reason == null ? "" : reason.trim();
        if (note.isBlank()) throw new IllegalStateException("请填写举报理由");
        if (note.length() > 512) note = note.substring(0, 512);
        if ("archive".equals(type) && ArchiveStore.getItemRaw(targetId) == null) {
            throw new IllegalArgumentException("对象不存在");
        }
        if ("ticket".equals(type) && TicketStore.get(targetId) == null) {
            throw new IllegalArgumentException("单据不存在");
        }
        if (mapper().countPendingDup(username, type, targetId) > 0) {
            throw new IllegalStateException("您已提交过该内容的举报，请等待处理");
        }
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("username", username);
        row.put("targetType", type);
        row.put("targetId", targetId);
        row.put("reason", note);
        row.put("status", "pending");
        row.put("createdAt", Timestamp.valueOf(LocalDateTime.now()));
        mapper().insertReport(row);
        long id = row.get("id") == null ? 0L : ((Number) row.get("id")).longValue();
        return getReport(id);
    }

    public static Map<String, Object> pageReports(String status, int page, int size) {
        requireReport();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        String st = status == null ? "" : status.trim();
        String filter = st.isBlank() ? null : st;
        PageHelper.startPage(page, size);
        List<Map<String, Object>> raw = mapper().selectReports(filter);
        PageInfo<Map<String, Object>> pi = new PageInfo<>(raw);
        List<Map<String, Object>> list = new ArrayList<>();
        if (raw != null) {
            for (Map<String, Object> r : raw) {
                list.add(mapReport(r));
            }
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", pi.getTotal());
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    /**
     * @param action ignore | takedown
     */
    public static Map<String, Object> resolveReport(
            long reportId, String action, String handler, String handleNote) {
        requireReport();
        Map<String, Object> m = getReport(reportId);
        if (m == null) throw new IllegalArgumentException("举报不存在");
        if (!"pending".equals(String.valueOf(m.get("status")))) {
            throw new IllegalStateException("该举报已处理");
        }
        String act = action == null ? "" : action.trim();
        if (!"ignore".equals(act) && !"takedown".equals(act)) {
            throw new IllegalStateException("处理方式须为忽略或下架");
        }
        String note = handleNote == null ? "" : handleNote.trim();
        if (note.length() > 512) note = note.substring(0, 512);
        String newStatus = "ignore".equals(act) ? "ignored" : "takedown";
        if ("takedown".equals(act)) {
            String type = String.valueOf(m.get("targetType"));
            long tid = toLong(m.get("targetId"));
            if ("archive".equals(type)) {
                boolean ok = ArchiveStore.deleteItem(tid);
                if (!ok) {
                    ArchiveStore.updateItem(tid, Map.of("status", "unavailable"));
                }
            } else if ("ticket".equals(type)) {
                TicketStore.hideForReport(tid, note.isBlank() ? "举报下架" : note);
            }
        }
        mapper().updateResolve(
                reportId,
                newStatus,
                handler == null ? "" : handler,
                note);
        return getReport(reportId);
    }

    private static Map<String, Object> getReport(long id) {
        return mapReport(mapper().selectReportById(id));
    }

    private static Map<String, Object> mapReport(Map<String, Object> raw) {
        if (raw == null) return null;
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", col(raw, "id", "id"));
        m.put("username", col(raw, "username", "username"));
        m.put("targetType", col(raw, "targetType", "target_type"));
        m.put("targetId", col(raw, "targetId", "target_id"));
        m.put("reason", col(raw, "reason", "reason"));
        m.put("status", col(raw, "status", "status"));
        Object handler = col(raw, "handler", "handler");
        m.put("handler", handler == null ? "" : String.valueOf(handler));
        Object handleNote = col(raw, "handleNote", "handle_note");
        m.put("handleNote", handleNote == null ? "" : String.valueOf(handleNote));
        m.put("createdAt", fmt(col(raw, "createdAt", "created_at")));
        m.put("handledAt", fmt(col(raw, "handledAt", "handled_at")));
        return m;
    }

    private static Object col(Map<String, Object> raw, String camel, String snake) {
        if (raw.containsKey(camel)) return raw.get(camel);
        if (raw.containsKey(snake)) return raw.get(snake);
        String lower = snake.toLowerCase(Locale.ROOT);
        for (Map.Entry<String, Object> e : raw.entrySet()) {
            if (e.getKey() != null && e.getKey().equalsIgnoreCase(lower)) return e.getValue();
        }
        return null;
    }

    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        String s = String.valueOf(o);
        return s.isBlank() ? null : s;
    }

    private static long toLong(Object o) {
        if (o instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(String.valueOf(o));
        } catch (Exception e) {
            return 0L;
        }
    }

    private static void require() {
        if (!enabled) throw new IllegalStateException("收藏功能暂不可用");
    }

    private static void requireLike() {
        if (!likeEnabled) throw new IllegalStateException("点赞功能暂不可用");
    }

    private static void requireReport() {
        if (!reportEnabled) throw new IllegalStateException("举报功能暂不可用");
    }
}
