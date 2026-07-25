package com.thesis.capability;

import com.thesis.config.MybatisSupport;
import com.thesis.mapper.RecommendMapper;
import com.thesis.service.UserStore;

import java.util.*;

/**
 * 轻量个性化推荐（规则版）：分类偏好 + 热度 + 上新兜底。
 */
public final class RecommendStore {

    private RecommendStore() {}

    private static RecommendMapper mapper() {
        return MybatisSupport.mapper(RecommendMapper.class);
    }

    public static Map<String, Object> recommend(String username, int limit) {
        if (limit < 1) limit = 6;
        if (limit > 24) limit = 24;

        Map<String, Object> out = new LinkedHashMap<>();
        String item = ArchiveStore.itemTable();
        if (item == null || item.isBlank()) {
            out.put("list", List.of());
            out.put("mode", "disabled");
            out.put("reason", "暂无推荐");
            return out;
        }
        String cat = ArchiveStore.categoryTable();

        Set<Long> seen = new LinkedHashSet<>();
        List<Map<String, Object>> list = new ArrayList<>();
        String mode = "cold";

        Set<Long> interacted = interactedItemIds(username);
        List<Long> preferredCats = preferredCategoryIds(item, cat, username, interacted);

        if (!preferredCats.isEmpty()) {
            mode = "personalized";
            appendByCategories(list, seen, interacted, preferredCats, item, limit, "偏好分类");
        }

        if (list.size() < limit) {
            if ("cold".equals(mode)) mode = "hot";
            appendHot(list, seen, interacted, item, limit, "热门");
        }

        if (list.size() < limit) {
            if ("cold".equals(mode)) mode = "latest";
            appendLatest(list, seen, interacted, item, limit, "上新", 8);
        }

        out.put("list", list);
        out.put("mode", mode);
        out.put("total", list.size());
        ArchiveStore.redactSensitiveListForPublic(list);
        return out;
    }

    private static Set<Long> interactedItemIds(String username) {
        Set<Long> out = new LinkedHashSet<>();
        if (username == null || username.isBlank()) return out;
        if (TicketStore.enabled() && TicketStore.isArchiveMode()) {
            try {
                List<Long> ids = mapper().selectInteractedTicketItemIds(
                        TicketStore.ticketTable(), TicketStore.itemFkColumn(), username);
                if (ids != null) out.addAll(ids);
            } catch (Exception ignored) {
            }
        }
        if (FavoriteStore.enabled()) {
            out.addAll(FavoriteStore.idsOf(username));
        }
        if (BrowseHistoryStore.enabled()) {
            out.addAll(BrowseHistoryStore.idsOf(username));
        }
        return out;
    }

    private static List<Long> preferredCategoryIds(
            String item, String cat, String username, Set<Long> interacted) {
        Map<Long, Integer> scores = new LinkedHashMap<>();

        if (!interacted.isEmpty()) {
            try {
                List<Long> ids = new ArrayList<>();
                int n = 0;
                for (Long id : interacted) {
                    if (id == null || id <= 0) continue;
                    ids.add(id);
                    n++;
                    if (n >= 80) break;
                }
                if (!ids.isEmpty()) {
                    List<Map<String, Object>> rows = mapper().selectCategoryCounts(item, ids);
                    if (rows != null) {
                        for (Map<String, Object> row : rows) {
                            long cid = ((Number) row.get("cid")).longValue();
                            if (cid > 0) {
                                scores.merge(cid, ((Number) row.get("cnt")).intValue() * 3, Integer::sum);
                            }
                        }
                    }
                }
            } catch (Exception ignored) {
            }
        }

        boostFromProfile(scores, cat, username);

        List<Map.Entry<Long, Integer>> ranked = new ArrayList<>(scores.entrySet());
        ranked.sort((a, b) -> Integer.compare(b.getValue(), a.getValue()));
        List<Long> out = new ArrayList<>();
        for (Map.Entry<Long, Integer> e : ranked) {
            if (e.getKey() > 0) out.add(e.getKey());
            if (out.size() >= 3) break;
        }
        return out;
    }

    private static void boostFromProfile(Map<Long, Integer> scores, String cat, String username) {
        if (username == null || username.isBlank() || cat == null || cat.isBlank()) return;
        UserStore.Profile p = UserStore.get(username);
        if (p == null || p.extras == null || p.extras.isEmpty()) return;
        String pref = firstNonBlank(
                p.extras.get("preferredGenre"),
                p.extras.get("preferredCategory"),
                p.extras.get("favoriteGenre"));
        if (pref == null || pref.isBlank()) return;
        String needle = pref.trim();
        try {
            List<Map<String, Object>> rows = mapper().selectAllCategories(cat);
            if (rows == null) return;
            for (Map<String, Object> row : rows) {
                String name = String.valueOf(row.get("name"));
                if (name.contains(needle) || needle.contains(name)) {
                    scores.merge(((Number) row.get("id")).longValue(), 2, Integer::sum);
                }
            }
        } catch (Exception ignored) {
        }
    }

    private static void appendByCategories(
            List<Map<String, Object>> list,
            Set<Long> seen,
            Set<Long> exclude,
            List<Long> categoryIds,
            String item,
            int limit,
            String reason) {
        if (categoryIds.isEmpty()) return;
        String hotJoin = hotJoinSql("b.id");
        try {
            List<Long> ids = mapper().selectIdsByCategories(
                    item, categoryIds, exclude, hotJoin, limit * 2);
            if (ids == null) return;
            for (Long id : ids) {
                if (list.size() >= limit) break;
                addItem(list, seen, id, reason);
            }
        } catch (Exception ignored) {
        }
    }

    private static void appendHot(
            List<Map<String, Object>> list,
            Set<Long> seen,
            Set<Long> exclude,
            String item,
            int limit,
            String reason) {
        String hotJoin = hotJoinSql("b.id");
        if (hotJoin.isBlank()) return;
        try {
            List<Long> ids = mapper().selectHotIds(item, exclude, hotJoin, limit * 2);
            if (ids == null) return;
            for (Long id : ids) {
                if (list.size() >= limit) break;
                addItem(list, seen, id, reason);
            }
        } catch (Exception ignored) {
        }
    }

    private static String hotJoinSql(String itemIdCol) {
        if (TicketStore.enabled() && TicketStore.isArchiveMode()) {
            String ticket = TicketStore.ticketTable();
            return "LEFT JOIN (SELECT " + TicketStore.itemFkColumn() + " AS hid, COUNT(*) AS hot FROM " + ticket
                    + " WHERE status<>'rejected' GROUP BY " + TicketStore.itemFkColumn()
                    + ") h ON h.hid=" + itemIdCol + " ";
        }
        if (FavoriteStore.enabled()) {
            return "LEFT JOIN (SELECT item_id AS hid, COUNT(*) AS hot FROM user_favorite"
                    + " GROUP BY item_id) h ON h.hid=" + itemIdCol + " ";
        }
        return "";
    }

    private static void appendLatest(
            List<Map<String, Object>> list,
            Set<Long> seen,
            Set<Long> exclude,
            String item,
            int limit,
            String reason,
            int skipNewest) {
        try {
            List<Long> ids = mapper().selectLatestIds(item, exclude, limit * 2, Math.max(0, skipNewest));
            if (ids == null) return;
            for (Long id : ids) {
                if (list.size() >= limit) break;
                addItem(list, seen, id, reason);
            }
        } catch (Exception ignored) {
        }
    }

    private static void addItem(List<Map<String, Object>> list, Set<Long> seen, long id, String reason) {
        if (id <= 0 || !seen.add(id)) return;
        Map<String, Object> item = ArchiveStore.getItem(id);
        if (item == null) return;
        if (reason != null && !reason.isBlank()) {
            item.put("recommendReason", reason);
        }
        list.add(item);
    }

    private static String firstNonBlank(String... vals) {
        if (vals == null) return null;
        for (String v : vals) {
            if (v != null && !v.isBlank()) return v;
        }
        return null;
    }
}
