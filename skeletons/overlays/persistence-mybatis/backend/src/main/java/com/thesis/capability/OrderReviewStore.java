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
        if (!"completed".equals(String.valueOf(order.get("status")))) {
            throw new IllegalStateException("仅已完成订单可评价");
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
            list.add(shape(r));
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", pi.getTotal());
        out.put("page", page);
        out.put("size", size);
        return out;
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
