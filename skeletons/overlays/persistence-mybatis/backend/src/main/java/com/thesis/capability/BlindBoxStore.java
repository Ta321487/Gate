package com.thesis.capability;

import com.thesis.config.MybatisSupport;
import com.thesis.mapper.BlindBoxMapper;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;

/**
 * 盲盒。规则与 jdbc 相同，只换数据访问。
 */
public final class BlindBoxStore {

    private static boolean enabled;

    private BlindBoxStore() {}

    public static void configure(boolean on) {
        enabled = on;
    }

    public static boolean enabled() {
        return enabled;
    }

    public static boolean isBox(long boxId) {
        if (!enabled || boxId <= 0) return false;
        try {
            Integer n = db().countBox(boxId);
            return n != null && n > 0;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置盲盒奖池", e);
        }
    }

    public static List<Map<String, Object>> drawAll(String username, long orderId, long boxId, int qty) {
        if (!enabled || qty <= 0) return List.of();
        int pityNeed = pityN(boxId);
        List<Map<String, Object>> pool = loadPool(boxId);
        Map<String, Object> pity = loadPity(username, boxId);
        int draws = num(pity.get("draws"));
        int hiddenGot = flag(pity.get("hiddenGot")) ? 1 : 0;
        List<Map<String, Object>> picked = new ArrayList<>();
        StringBuilder titles = new StringBuilder();
        int anyHidden = 0;
        for (int i = 0; i < qty; i++) {
            List<Map<String, Object>> cands = available(pool);
            if (pityNeed > 0 && draws + 1 >= pityNeed && hiddenGot == 0) {
                List<Map<String, Object>> hidden = new ArrayList<>();
                for (Map<String, Object> c : cands) {
                    if (flag(c.get("hidden"))) hidden.add(c);
                }
                if (!hidden.isEmpty()) cands = hidden;
            }
            if (cands.isEmpty()) throw new IllegalStateException("奖池已空，无法下单");
            Map<String, Object> prize = pickWeighted(cands);
            prize.put("stock", num(prize.get("stock")) - 1);
            picked.add(prize);
            if (titles.length() > 0) titles.append('；');
            String title = str(first(prize, "title"));
            if (title.isBlank()) title = "奖品" + lng(first(prize, "prizeId", "prize_id"));
            titles.append(title);
            if (flag(first(prize, "hidden"))) {
                anyHidden = 1;
                hiddenGot = 1;
            }
            draws++;
        }
        String text = titles.toString();
        if (text.length() > 500) text = text.substring(0, 500);
        stamp(orderId, boxId, text, anyHidden);
        savePity(username, boxId, draws, hiddenGot);
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> prize : picked) {
            Map<String, Object> one = new LinkedHashMap<>();
            one.put("itemId", lng(first(prize, "prizeId", "prize_id")));
            out.add(one);
        }
        return out;
    }

    public static String pityText(long orderId, long boxId) {
        if (!enabled || orderId <= 0 || boxId <= 0) return "";
        try {
            String user = db().orderUser(orderTable(), orderId);
            if (user == null || user.isBlank()) return "";
            return str(progress(user, boxId).get("text"));
        } catch (RuntimeException e) {
            return "";
        }
    }

    public static Map<String, Object> progress(String username, long boxId) {
        requireOn();
        int pityNeed = pityN(boxId);
        Map<String, Object> pity = loadPity(username, boxId);
        int draws = num(pity.get("draws"));
        boolean got = flag(first(pity, "hiddenGot", "hidden_got"));
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("draws", draws);
        m.put("pityN", pityNeed);
        m.put("hiddenGot", got);
        m.put("text", pityLine(draws, pityNeed, got));
        return m;
    }

    public static List<Map<String, Object>> listAll() {
        requireOn();
        try {
            List<Map<String, Object>> rows = db().listAll(itemTable());
            if (rows == null) return List.of();
            for (Map<String, Object> row : rows) {
                row.put("hidden", flag(row.get("hidden")));
                row.put("enabled", flag(row.get("enabled")));
                row.put("weight", num(row.get("weight")));
                row.put("pityN", num(first(row, "pityN", "pity_n")));
                row.put("prizeStock", num(first(row, "prizeStock", "prize_stock", "stock")));
            }
            return rows;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置盲盒奖池", e);
        }
    }

    public static List<Map<String, Object>> products() {
        requireOn();
        try {
            List<Map<String, Object>> rows = db().products(itemTable());
            if (rows == null) return List.of();
            for (Map<String, Object> row : rows) {
                row.put("pityN", num(first(row, "pityN", "pity_n")));
            }
            return rows;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置保底次数", e);
        }
    }

    public static List<Map<String, Object>> boxes(String username) {
        requireOn();
        try {
            List<Map<String, Object>> rows = db().boxes(itemTable(), username == null ? "" : username);
            if (rows == null) return List.of();
            List<Map<String, Object>> out = new ArrayList<>();
            for (Map<String, Object> row : rows) {
                int pityNeed = num(first(row, "pityN", "pity_n"));
                int draws = num(first(row, "draws"));
                boolean got = flag(first(row, "hiddenGot", "hidden_got"));
                Map<String, Object> m = new LinkedHashMap<>();
                m.put("id", lng(first(row, "id", "boxId", "box_id")));
                m.put("title", str(first(row, "title")));
                m.put("pityN", pityNeed);
                m.put("draws", draws);
                m.put("hiddenGot", got);
                m.put("text", pityLine(draws, pityNeed, got));
                out.add(m);
            }
            return out;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置盲盒奖池", e);
        }
    }

    public static List<Map<String, Object>> prizeOnly() {
        requireOn();
        try {
            List<Map<String, Object>> rows = db().prizeOnly();
            return rows == null ? List.of() : rows;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置盲盒奖池", e);
        }
    }

    public static void assertPurchasable(long itemId) {
        if (!enabled || itemId <= 0) return;
        try {
            Integer asPrize = db().countPrize(itemId);
            if (asPrize == null || asPrize <= 0) return;
            Integer asBox = db().countBox(itemId);
            if (asBox != null && asBox > 0) return;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置盲盒奖池", e);
        }
        throw new IllegalArgumentException("奖品不能单独购买，请选盲盒");
    }

    public static Map<String, Object> save(Map<String, Object> body) {
        requireOn();
        Map<String, Object> in = body == null ? Map.of() : body;
        long id = lng(in.get("id"));
        long boxId = lng(in.get("boxId"));
        long prizeId = lng(in.get("prizeId"));
        int weight = num(in.get("weight"));
        int hidden = flag(in.get("hidden")) ? 1 : 0;
        int on = in.containsKey("enabled") && !flag(in.get("enabled")) ? 0 : 1;
        int pityNeed = num(in.get("pityN"));
        if (boxId <= 0 || prizeId <= 0) throw new IllegalArgumentException("请选择盒子和奖品");
        if (boxId == prizeId) throw new IllegalArgumentException("奖品不能是盒子自己");
        if (weight < 1) throw new IllegalArgumentException("权重至少为 1");
        if (pityNeed < 0) throw new IllegalArgumentException("保底次数不能为负");
        if (ArchiveStore.getItemRaw(boxId) == null || ArchiveStore.getItemRaw(prizeId) == null) {
            throw new IllegalArgumentException("商品不存在");
        }
        try {
            Integer dup = db().countDup(boxId, prizeId, id);
            if (dup != null && dup > 0) throw new IllegalArgumentException("这个奖品已经在这个盒子里");
            if (id > 0) db().updatePool(id, boxId, prizeId, weight, hidden, on);
            else db().insertPool(boxId, prizeId, weight, hidden, on);
            db().updatePity(itemTable(), boxId, pityNeed);
        } catch (IllegalArgumentException e) {
            throw e;
        } catch (Exception e) {
            String msg = e.getMessage() == null ? "" : e.getMessage();
            if (msg.contains("pity_n")) throw new IllegalStateException("系统未配置保底次数", e);
            throw new IllegalStateException("系统未配置盲盒奖池", e);
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("ok", true);
        return out;
    }

    private static void stamp(long orderId, long boxId, String text, int hidden) {
        try {
            int updated = db().stamp(lineTable(), orderId, boxId, text, hidden);
            if (updated <= 0) throw new IllegalStateException("抽奖结果未能记到订单");
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置盲盒抽奖字段", e);
        }
    }

    private static void savePity(String username, long boxId, int draws, int hiddenGot) {
        try {
            db().upsertPity(username, boxId, draws, hiddenGot);
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置盲盒保底表", e);
        }
    }

    private static int pityN(long boxId) {
        try {
            Integer n = db().pityN(itemTable(), boxId);
            return n == null ? 0 : n;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置保底次数", e);
        }
    }

    private static Map<String, Object> loadPity(String username, long boxId) {
        try {
            Map<String, Object> row = db().pity(username, boxId);
            if (row != null && !row.isEmpty()) return row;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置盲盒保底表", e);
        }
        Map<String, Object> empty = new LinkedHashMap<>();
        empty.put("draws", 0);
        empty.put("hiddenGot", 0);
        return empty;
    }

    private static List<Map<String, Object>> loadPool(long boxId) {
        try {
            List<Map<String, Object>> rows = db().pool(itemTable(), boxId);
            return rows == null ? List.of() : rows;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置盲盒奖池", e);
        }
    }

    private static List<Map<String, Object>> available(List<Map<String, Object>> pool) {
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> row : pool) {
            if (num(row.get("weight")) <= 0) continue;
            if (num(first(row, "stock")) <= 0) continue;
            out.add(row);
        }
        return out;
    }

    private static Map<String, Object> pickWeighted(List<Map<String, Object>> cands) {
        int sum = 0;
        for (Map<String, Object> c : cands) sum += num(c.get("weight"));
        if (sum <= 0) throw new IllegalStateException("奖池已空，无法下单");
        int roll = ThreadLocalRandom.current().nextInt(sum);
        int acc = 0;
        for (Map<String, Object> c : cands) {
            acc += num(c.get("weight"));
            if (roll < acc) return c;
        }
        return cands.get(cands.size() - 1);
    }

    private static String pityLine(int draws, int pityNeed, boolean got) {
        if (pityNeed <= 0) return "已抽 " + draws + " 次，未设保底";
        if (got) return "已抽 " + draws + " 次，保底 " + pityNeed + " 次，已出隐藏款";
        return "已抽 " + draws + " 次，保底 " + pityNeed + " 次，尚未出隐藏款";
    }

    private static Object first(Map<String, Object> row, String... keys) {
        if (row == null) return null;
        for (String key : keys) {
            if (row.containsKey(key) && row.get(key) != null) return row.get(key);
        }
        return null;
    }

    private static void requireOn() {
        if (!enabled) throw new IllegalStateException("盲盒未开启");
    }

    private static BlindBoxMapper db() {
        return MybatisSupport.mapper(BlindBoxMapper.class);
    }

    private static String itemTable() {
        return safeIdent(ArchiveStore.itemTable(), "product");
    }

    private static String orderTable() {
        return safeIdent(OrderStore.orderTable(), "biz_order");
    }

    private static String lineTable() {
        return safeIdent(OrderStore.lineTable(), "order_line");
    }

    private static String safeIdent(String raw, String fallback) {
        String t = raw == null ? "" : raw.trim();
        if (!t.matches("[A-Za-z_][A-Za-z0-9_]*")) return fallback;
        return t;
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
        if (o == null || String.valueOf(o).isBlank()) return 0L;
        try {
            return Long.parseLong(String.valueOf(o).trim());
        } catch (NumberFormatException e) {
            return 0L;
        }
    }

    private static boolean flag(Object o) {
        if (o instanceof Boolean b) return b;
        if (o instanceof Number n) return n.intValue() != 0;
        String s = str(o);
        return "1".equals(s) || "true".equalsIgnoreCase(s);
    }
}
