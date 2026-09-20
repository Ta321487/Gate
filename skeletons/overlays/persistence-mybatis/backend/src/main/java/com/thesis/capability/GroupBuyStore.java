package com.thesis.capability;

import com.thesis.config.MybatisSupport;
import com.thesis.mapper.GroupBuyMapper;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 拼团。规则与 jdbc 相同，只换数据访问。
 */
public final class GroupBuyStore {

    private static final DateTimeFormatter TS = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static boolean enabled;

    private GroupBuyStore() {}

    public static void configure(boolean on) {
        enabled = on;
    }

    public static boolean enabled() {
        return enabled;
    }

    public static void sweep() {
        if (!enabled) return;
        List<Map<String, Object>> rows;
        try {
            rows = db().openCampaigns();
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置拼团表", e);
        }
        if (rows == null) return;
        LocalDateTime now = LocalDateTime.now();
        for (Map<String, Object> row : rows) {
            long id = lng(row.get("id"));
            int target = num(first(row, "targetSize", "target_size"));
            int joined = count(id);
            if (joined >= target) {
                form(id);
                continue;
            }
            LocalDateTime deadline = toTime(row.get("deadline"));
            if (deadline != null && !deadline.isAfter(now)) fail(id);
        }
    }

    public static void assertJoin(long campaignId, String username, List<Long> itemIds) {
        if (!enabled) throw new IllegalStateException("拼团未开启");
        Map<String, Object> camp = loadOpen(campaignId);
        long itemId = lng(first(camp, "itemId", "item_id"));
        boolean hit = false;
        if (itemIds != null) {
            for (Long id : itemIds) {
                if (id != null && id == itemId) hit = true;
            }
        }
        if (!hit) throw new IllegalArgumentException("购物车里没有这个团的商品");
        Integer mine = db().countMine(campaignId, username);
        if (mine != null && mine > 0) throw new IllegalArgumentException("你已经在这个团里");
    }

    public static void join(String username, long orderId, long campaignId) {
        if (!enabled) return;
        db().insertMember(campaignId, orderId, username);
        Map<String, Object> camp = loadOpen(campaignId);
        if (count(campaignId) >= num(first(camp, "targetSize", "target_size"))) form(campaignId);
    }

    public static List<Map<String, Object>> listOpen() {
        requireOn();
        sweep();
        return withVerb(db().listOpen(itemTable()));
    }

    public static List<Map<String, Object>> listAll() {
        requireOn();
        return withVerb(db().listAll(itemTable()));
    }

    public static List<Map<String, Object>> products() {
        requireOn();
        return db().products(itemTable());
    }

    public static Map<String, Object> save(Map<String, Object> body) {
        requireOn();
        if (body == null) body = Map.of();
        long itemId = lng(body.get("itemId"));
        int target = num(body.get("targetSize"));
        LocalDateTime deadline = parseTs(str(body.get("deadline")));
        if (itemId <= 0) throw new IllegalArgumentException("请选择商品");
        if (target < 2) throw new IllegalArgumentException("成团人数至少 2");
        if (deadline == null) throw new IllegalArgumentException("请选择截止时间");
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("itemId", itemId);
        row.put("targetSize", target);
        row.put("deadline", Timestamp.valueOf(deadline));
        long id = lng(body.get("id"));
        if (id > 0) {
            row.put("id", id);
            if (db().updateCampaign(row) <= 0) throw new IllegalArgumentException("只能修改仍开放的团");
        } else {
            db().insertCampaign(row);
        }
        sweep();
        return Map.of("ok", true);
    }

    private static void form(long campaignId) {
        db().markFormed(campaignId);
        String order = orderTable();
        List<Long> ids = db().memberOrders(campaignId);
        if (ids == null) return;
        for (Long orderId : ids) {
            if (orderId != null) db().confirmOrder(order, orderId);
        }
    }

    private static void fail(long campaignId) {
        db().markFailed(campaignId);
        List<Map<String, Object>> rows = db().groupingOrders(orderTable(), campaignId);
        if (rows == null) return;
        for (Map<String, Object> row : rows) {
            long orderId = lng(first(row, "orderId", "order_id"));
            db().cancelOrder(orderTable(), orderId);
            double paid = row.get("paid") instanceof Number n ? n.doubleValue() : 0;
            if (paid > 0) LoyaltyStore.refundOrderPay(str(row.get("username")), orderId, paid);
        }
    }

    private static Map<String, Object> loadOpen(long campaignId) {
        Map<String, Object> camp;
        try {
            camp = db().campaign(campaignId);
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置拼团表", e);
        }
        if (camp == null || camp.isEmpty()) throw new IllegalArgumentException("拼团不存在");
        if (!"open".equals(str(camp.get("status")))) throw new IllegalArgumentException("这个团已结束");
        LocalDateTime deadline = toTime(camp.get("deadline"));
        if (deadline == null || !deadline.isAfter(LocalDateTime.now())) {
            throw new IllegalArgumentException("这个团已过截止时间");
        }
        return camp;
    }

    private static int count(long id) {
        Integer n = db().countMembers(id);
        return n == null ? 0 : n;
    }

    private static List<Map<String, Object>> withVerb(List<Map<String, Object>> rows) {
        if (rows == null) return List.of();
        for (Map<String, Object> row : rows) {
            int joined = num(row.get("joined"));
            row.put("verb", joined <= 0 ? "开团" : "参团");
        }
        return rows;
    }

    private static void requireOn() {
        if (!enabled) throw new IllegalStateException("拼团未开启");
    }

    private static GroupBuyMapper db() {
        return MybatisSupport.mapper(GroupBuyMapper.class);
    }

    private static String itemTable() {
        return safeIdent(ArchiveStore.itemTable(), "product");
    }

    private static String orderTable() {
        return safeIdent(OrderStore.orderTable(), "biz_order");
    }

    private static String safeIdent(String raw, String fallback) {
        String t = raw == null ? "" : raw.trim();
        if (!t.matches("[A-Za-z_][A-Za-z0-9_]*")) return fallback;
        return t;
    }

    private static Object first(Map<String, Object> row, String a, String b) {
        if (row == null) return null;
        if (row.get(a) != null) return row.get(a);
        return row.get(b);
    }

    private static LocalDateTime toTime(Object raw) {
        if (raw instanceof Timestamp ts) return ts.toLocalDateTime();
        if (raw instanceof LocalDateTime dt) return dt;
        if (raw instanceof java.util.Date d) return new Timestamp(d.getTime()).toLocalDateTime();
        return parseTs(str(raw));
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static int num(Object o) {
        if (o instanceof Number n) return n.intValue();
        if (o == null || String.valueOf(o).isBlank()) return 0;
        try {
            return Integer.parseInt(String.valueOf(o).trim());
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    private static long lng(Object o) {
        if (o instanceof Number n) return n.longValue();
        if (o == null || String.valueOf(o).isBlank()) return 0;
        try {
            return Long.parseLong(String.valueOf(o).trim());
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    private static LocalDateTime parseTs(String raw) {
        if (raw == null || raw.isBlank()) return null;
        String s = raw.trim().replace('T', ' ');
        if (s.length() > 19) s = s.substring(0, 19);
        if (s.length() == 16) s = s + ":00";
        try {
            return LocalDateTime.parse(s, TS);
        } catch (Exception e) {
            return null;
        }
    }
}
