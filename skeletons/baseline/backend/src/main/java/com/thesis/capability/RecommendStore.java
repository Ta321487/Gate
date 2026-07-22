package com.thesis.capability;

import com.thesis.config.JdbcSupport;
import com.thesis.service.UserStore;
import org.springframework.jdbc.core.JdbcTemplate;

import java.util.*;

/**
 * 轻量个性化推荐（规则版）：分类偏好 + 热度 + 上新兜底。
 * 互动信号：单据（若开启）+ 收藏夹 + 浏览历史；无单据域（媒资/博客）仍可用。
 */
public final class RecommendStore {

    private RecommendStore() {}

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
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
            appendByCategories(list, seen, interacted, preferredCats, item, limit);
        }

        if (list.size() < limit) {
            if ("cold".equals(mode)) mode = "hot";
            appendHot(list, seen, interacted, item, limit);
        }

        if (list.size() < limit) {
            if ("cold".equals(mode)) mode = "latest";
            appendLatest(list, seen, interacted, item, limit);
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
                String ticket = TicketStore.ticketTable();
                List<Long> ids = db().query(
                        "SELECT DISTINCT book_id FROM " + ticket
                                + " WHERE username=? AND status<>'rejected' AND book_id IS NOT NULL",
                        (rs, i) -> rs.getLong(1),
                        username);
                if (ids != null) out.addAll(ids);
            } catch (Exception ignored) {
                // ignore
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
                StringBuilder in = new StringBuilder();
                List<Object> args = new ArrayList<>();
                int n = 0;
                for (Long id : interacted) {
                    if (id == null || id <= 0) continue;
                    if (n > 0) in.append(',');
                    in.append('?');
                    args.add(id);
                    n++;
                    if (n >= 80) break;
                }
                if (n > 0) {
                    List<Map<String, Object>> rows = db().query(
                            "SELECT category_id AS cid, COUNT(*) AS cnt FROM " + item
                                    + " WHERE id IN (" + in + ") GROUP BY category_id",
                            (rs, i) -> {
                                Map<String, Object> m = new LinkedHashMap<>();
                                m.put("cid", rs.getLong("cid"));
                                m.put("cnt", rs.getInt("cnt"));
                                return m;
                            },
                            args.toArray());
                    for (Map<String, Object> row : rows) {
                        long cid = ((Number) row.get("cid")).longValue();
                        if (cid > 0) {
                            scores.merge(cid, ((Number) row.get("cnt")).intValue() * 3, Integer::sum);
                        }
                    }
                }
            } catch (Exception ignored) {
                // 表结构异常时走冷启动
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

    /** profile_json 中 preferredGenre / preferredCategory 与分类名模糊匹配 */
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
            List<Map<String, Object>> rows = db().query(
                    "SELECT id, name FROM " + cat,
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("id", rs.getLong("id"));
                        m.put("name", rs.getString("name"));
                        return m;
                    });
            for (Map<String, Object> row : rows) {
                String name = String.valueOf(row.get("name"));
                if (name.contains(needle) || needle.contains(name)) {
                    scores.merge((Long) row.get("id"), 2, Integer::sum);
                }
            }
        } catch (Exception ignored) {
            // ignore
        }
    }

    private static void appendByCategories(
            List<Map<String, Object>> list,
            Set<Long> seen,
            Set<Long> exclude,
            List<Long> categoryIds,
            String item,
            int limit) {
        if (categoryIds.isEmpty()) return;
        StringBuilder in = new StringBuilder();
        List<Object> args = new ArrayList<>();
        for (int i = 0; i < categoryIds.size(); i++) {
            if (i > 0) in.append(',');
            in.append('?');
            args.add(categoryIds.get(i));
        }
        String excl = excludeSql("b.id", exclude, args);
        String hotJoin = hotJoinSql("b.id");
        String sql = "SELECT b.id FROM " + item + " b " + hotJoin
                + " WHERE b.category_id IN (" + in + ")" + excl
                + " ORDER BY COALESCE(h.hot,0) DESC, b.id DESC LIMIT ?";
        args.add(limit * 2);
        try {
            List<Long> ids = db().query(sql, (rs, i) -> rs.getLong(1), args.toArray());
            for (Long id : ids) {
                if (list.size() >= limit) break;
                addItem(list, seen, id);
            }
        } catch (Exception ignored) {
            // ignore
        }
    }

    private static void appendHot(
            List<Map<String, Object>> list,
            Set<Long> seen,
            Set<Long> exclude,
            String item,
            int limit) {
        List<Object> args = new ArrayList<>();
        String excl = excludeSql("b.id", exclude, args);
        String hotJoin = hotJoinSql("b.id");
        // 无热度源时 hotJoin 为空表，直接跳过
        if (hotJoin.isBlank()) return;
        String sql = "SELECT b.id FROM " + item + " b " + hotJoin
                + " WHERE COALESCE(h.hot,0) > 0" + excl
                + " ORDER BY h.hot DESC, b.id DESC LIMIT ?";
        args.add(limit * 2);
        try {
            List<Long> ids = db().query(sql, (rs, i) -> rs.getLong(1), args.toArray());
            for (Long id : ids) {
                if (list.size() >= limit) break;
                addItem(list, seen, id);
            }
        } catch (Exception ignored) {
            // ignore
        }
    }

    /** LEFT JOIN 热度子查询：优先单据，其次收藏次数 */
    private static String hotJoinSql(String itemIdCol) {
        if (TicketStore.enabled() && TicketStore.isArchiveMode()) {
            String ticket = TicketStore.ticketTable();
            return "LEFT JOIN (SELECT book_id AS hid, COUNT(*) AS hot FROM " + ticket
                    + " WHERE status<>'rejected' GROUP BY book_id) h ON h.hid=" + itemIdCol + " ";
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
            int limit) {
        List<Object> args = new ArrayList<>();
        String excl = excludeSql("id", exclude, args);
        String sql = "SELECT id FROM " + item + " WHERE 1=1" + excl + " ORDER BY id DESC LIMIT ?";
        args.add(limit * 2);
        try {
            List<Long> ids = db().query(sql, (rs, i) -> rs.getLong(1), args.toArray());
            for (Long id : ids) {
                if (list.size() >= limit) break;
                addItem(list, seen, id);
            }
        } catch (Exception ignored) {
            // ignore
        }
    }

    private static String excludeSql(String col, Set<Long> exclude, List<Object> args) {
        if (exclude == null || exclude.isEmpty()) return "";
        StringBuilder sb = new StringBuilder(" AND ").append(col).append(" NOT IN (");
        boolean first = true;
        for (Long id : exclude) {
            if (!first) sb.append(',');
            sb.append('?');
            args.add(id);
            first = false;
        }
        sb.append(')');
        return sb.toString();
    }

    private static void addItem(List<Map<String, Object>> list, Set<Long> seen, long id) {
        if (id <= 0 || !seen.add(id)) return;
        Map<String, Object> item = ArchiveStore.getItem(id);
        if (item != null) list.add(item);
    }

    private static String firstNonBlank(String... vals) {
        if (vals == null) return null;
        for (String v : vals) {
            if (v != null && !v.isBlank()) return v;
        }
        return null;
    }
}
