package com.thesis.capability;

import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.thesis.config.MybatisSupport;
import com.thesis.mapper.OrderReviewMapper;
import com.thesis.service.UserStore;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 订单评价：已完成订单星级+文字；管理端可回复。 */
public final class OrderReviewStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static boolean enabled;

    private OrderReviewStore() {}

    private static OrderReviewMapper mapper() {
        return MybatisSupport.mapper(OrderReviewMapper.class);
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

    public static Map<String, Object> submit(String username, long orderId, int rating, String body) {
        require();
        if (rating < 1 || rating > 5) throw new IllegalArgumentException("评分须为 1～5 星");
        Map<String, Object> order = OrderStore.getOrder(orderId);
        if (order == null) throw new IllegalArgumentException("订单不存在");
        if (!username.equals(String.valueOf(order.get("username")))) {
            throw new IllegalStateException("无权评价");
        }
        if (!"completed".equals(String.valueOf(order.get("status")))
                && !"signed".equals(String.valueOf(order.get("status")))) {
            throw new IllegalStateException("确认收货后方可评价");
        }
        if (mapper().countByOrderId(orderId) > 0) throw new IllegalStateException("该订单已评价");
        String text = body == null ? "" : body.trim();
        if (text.length() > 500) text = text.substring(0, 500);
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("orderId", orderId);
        row.put("username", username);
        row.put("rating", rating);
        row.put("body", text);
        row.put("createdAt", Timestamp.valueOf(LocalDateTime.now()));
        mapper().insert(row);
        long id = row.get("id") == null ? 0L : ((Number) row.get("id")).longValue();
        return get(id);
    }

    public static Map<String, Object> reply(long id, String reply) {
        require();
        Map<String, Object> cur = get(id);
        if (cur == null) throw new IllegalArgumentException("评价不存在");
        String text = reply == null ? "" : reply.trim();
        if (text.isBlank()) throw new IllegalArgumentException("请填写回复");
        if (text.length() > 500) text = text.substring(0, 500);
        mapper().reply(id, text, Timestamp.valueOf(LocalDateTime.now()));
        return get(id);
    }

    public static boolean delete(long id) {
        require();
        return mapper().deleteById(id) > 0;
    }

    /** 商品详情：按订单明细 item_id 汇总已完成订单的评价（公开只读）。 */
    public static Map<String, Object> pageByItem(long itemId, int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        String orderTable = OrderStore.orderTable();
        String lineTable = OrderStore.lineTable();
        if (itemId <= 0 || orderTable == null || orderTable.isBlank() || lineTable == null || lineTable.isBlank()) {
            Map<String, Object> empty = new LinkedHashMap<>();
            empty.put("list", List.of());
            empty.put("total", 0);
            empty.put("page", page);
            empty.put("size", size);
            return empty;
        }
        int total = mapper().countByItem(orderTable, lineTable, itemId);
        List<Map<String, Object>> raw = mapper().selectByItem(orderTable, lineTable, itemId, size, (page - 1) * size);
        List<Map<String, Object>> list = new ArrayList<>();
        if (raw != null) {
            for (Map<String, Object> r : raw) {
                list.add(shape(r));
            }
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    public static Map<String, Object> getByOrder(long orderId) {
        if (!enabled) return null;
        return shape(mapper().selectByOrderId(orderId));
    }

    public static Map<String, Object> page(String username, int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        PageHelper.startPage(page, size);
        List<Map<String, Object>> raw =
                username == null || username.isBlank()
                        ? mapper().selectAllOrderByIdDesc()
                        : mapper().selectByUsername(username);
        PageInfo<Map<String, Object>> pi = new PageInfo<>(raw);
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> r : raw) {
            list.add(enrichReview(shape(r)));
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", pi.getTotal());
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    /** 多店商家：仅本店商品所在订单的评价。 */
    public static Map<String, Object> pageForMerchant(String ownerUsername, int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        String owner = ownerUsername == null ? "" : ownerUsername.trim();
        if (owner.isBlank()) {
            Map<String, Object> empty = new LinkedHashMap<>();
            empty.put("list", List.of());
            empty.put("total", 0);
            empty.put("page", page);
            empty.put("size", size);
            return empty;
        }
        String lineTable = OrderStore.lineTable();
        String itemTable = ArchiveStore.itemTable();
        if (lineTable == null || lineTable.isBlank() || itemTable == null || itemTable.isBlank()
                || !ArchiveStore.hasOwnerUsername()) {
            return page(null, page, size);
        }
        int total = mapper().countByMerchant(lineTable, itemTable, owner);
        List<Map<String, Object>> raw =
                mapper().selectByMerchant(lineTable, itemTable, owner, size, (page - 1) * size);
        List<Map<String, Object>> list = new ArrayList<>();
        if (raw != null) {
            for (Map<String, Object> r : raw) {
                list.add(enrichReview(shape(r)));
            }
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    public static boolean merchantOwnsReview(String ownerUsername, long reviewId) {
        Map<String, Object> cur = get(reviewId);
        if (cur == null) return false;
        long orderId = toLong(cur.get("orderId"));
        return OrderStore.merchantOwnsOrder(ownerUsername, orderId);
    }

    private static Map<String, Object> enrichReview(Map<String, Object> m) {
        if (m == null) return null;
        try {
            long orderId = toLong(m.get("orderId"));
            if (orderId > 0) {
                Map<String, Object> order = OrderStore.getOrder(orderId);
                if (order != null && order.get("lines") instanceof List<?> lines && !lines.isEmpty()) {
                    List<String> titles = new ArrayList<>();
                    String shop = "";
                    for (Object o : lines) {
                        if (!(o instanceof Map<?, ?> line)) continue;
                        Object t = line.get("title");
                        if (t != null && !String.valueOf(t).isBlank()) titles.add(String.valueOf(t));
                        if (shop.isBlank() && line.get("shopName") != null) {
                            shop = String.valueOf(line.get("shopName")).trim();
                        }
                    }
                    if (!titles.isEmpty()) m.put("itemTitles", String.join("；", titles));
                    if (!shop.isBlank()) m.put("shopName", shop);
                }
            }
        } catch (Exception ignored) {
        }
        return m;
    }

    private static long toLong(Object o) {
        if (o instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(String.valueOf(o));
        } catch (Exception e) {
            return 0L;
        }
    }

    private static Map<String, Object> get(long id) {
        return shape(mapper().selectById(id));
    }

    private static Map<String, Object> shape(Map<String, Object> raw) {
        if (raw == null) return null;
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", raw.get("id"));
        m.put("orderId", raw.get("orderId"));
        m.put("username", raw.get("username"));
        m.put("rating", raw.get("rating"));
        m.put("body", raw.get("body"));
        Object reply = raw.get("reply");
        m.put("reply", reply == null ? "" : String.valueOf(reply));
        m.put("repliedAt", fmt(raw.get("repliedAt")));
        m.put("createdAt", fmt(raw.get("createdAt")));
        try {
            m.put("displayName", UserStore.displayName(String.valueOf(raw.get("username"))));
        } catch (Exception ignored) {
        }
        return m;
    }

    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        String s = String.valueOf(o);
        return s.isBlank() ? null : s;
    }

    private static void require() {
        if (!enabled) throw new IllegalStateException("订单评价暂不可用");
    }
}
