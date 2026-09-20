package com.thesis.capability;

import com.thesis.config.JpaDb;
import com.thesis.config.JpaSupport;

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
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM blind_pool WHERE box_id=? AND enabled=1",
                    Integer.class, boxId);
            return n != null && n > 0;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置盲盒奖池", e);
        }
    }

    /**
     * 按该盒子当前奖池抽 qty 次，把结果记到订单明细，并累加保底计数。
     * 返回抽中的奖品，库存由 OrderStore 在成功后扣减。
     */
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
            String title = str(prize.get("title"));
            if (title.isBlank()) title = "奖品" + lng(prize.get("prizeId"));
            titles.append(title);
            if (flag(prize.get("hidden"))) {
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
            one.put("itemId", lng(prize.get("prizeId")));
            out.add(one);
        }
        return out;
    }

    public static String pityText(long orderId, long boxId) {
        if (!enabled || orderId <= 0 || boxId <= 0) return "";
        try {
            String user = db().queryForObject(
                    "SELECT username FROM " + orderTable() + " WHERE id=?",
                    String.class, orderId);
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
        boolean got = flag(pity.get("hiddenGot"));
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("draws", draws);
        m.put("pityN", pityNeed);
        m.put("hiddenGot", got);
        m.put("text", pityLine(draws, pityNeed, got));
        return m;
    }

    public static List<Map<String, Object>> listAll() {
        requireOn();
        String item = itemTable();
        try {
            return db().query(
                    "SELECT p.id, p.box_id, b.title AS box_title, p.prize_id, i.title AS prize_title, "
                            + "p.weight, p.hidden, p.enabled, b.pity_n, i.stock "
                            + "FROM blind_pool p "
                            + "LEFT JOIN " + item + " b ON b.id=p.box_id "
                            + "LEFT JOIN " + item + " i ON i.id=p.prize_id "
                            + "ORDER BY p.box_id, p.id",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("id", rs.getLong("id"));
                        m.put("boxId", rs.getLong("box_id"));
                        m.put("boxTitle", rs.getString("box_title") == null ? "" : rs.getString("box_title"));
                        m.put("prizeId", rs.getLong("prize_id"));
                        m.put("prizeTitle", rs.getString("prize_title") == null ? "" : rs.getString("prize_title"));
                        m.put("weight", rs.getInt("weight"));
                        m.put("hidden", rs.getInt("hidden") != 0);
                        m.put("enabled", rs.getInt("enabled") != 0);
                        m.put("pityN", rs.getInt("pity_n"));
                        m.put("prizeStock", rs.getInt("stock"));
                        return m;
                    });
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置盲盒奖池", e);
        }
    }

    public static List<Map<String, Object>> products() {
        requireOn();
        try {
            return db().query(
                    "SELECT id, title, pity_n FROM " + itemTable() + " ORDER BY id",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("id", rs.getLong("id"));
                        m.put("title", rs.getString("title") == null ? "" : rs.getString("title"));
                        m.put("pityN", rs.getInt("pity_n"));
                        return m;
                    });
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置保底次数", e);
        }
    }

    public static List<Map<String, Object>> boxes(String username) {
        requireOn();
        String item = itemTable();
        String user = username == null ? "" : username;
        try {
            return db().query(
                    "SELECT p.box_id, MAX(i.title) AS title, MAX(i.pity_n) AS pity_n, "
                            + "MAX(IFNULL(y.draws,0)) AS draws, MAX(IFNULL(y.hidden_got,0)) AS hidden_got "
                            + "FROM blind_pool p "
                            + "LEFT JOIN " + item + " i ON i.id=p.box_id "
                            + "LEFT JOIN blind_pity y ON y.box_id=p.box_id AND y.username=? "
                            + "WHERE p.enabled=1 GROUP BY p.box_id ORDER BY p.box_id",
                    (rs, i) -> mapBox(rs),
                    user);
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置盲盒奖池", e);
        }
    }

    /** 只在奖池里、本身不是盒子的商品。用户不能直接买。 */
    public static List<Map<String, Object>> prizeOnly() {
        requireOn();
        try {
            return db().query(
                    "SELECT DISTINCT prize_id FROM blind_pool WHERE enabled=1 "
                            + "AND prize_id NOT IN (SELECT box_id FROM blind_pool WHERE enabled=1)",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("id", rs.getLong("prize_id"));
                        return m;
                    });
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置盲盒奖池", e);
        }
    }

    public static void assertPurchasable(long itemId) {
        if (!enabled || itemId <= 0) return;
        try {
            Integer asPrize = db().queryForObject(
                    "SELECT COUNT(*) FROM blind_pool WHERE prize_id=? AND enabled=1",
                    Integer.class, itemId);
            if (asPrize == null || asPrize <= 0) return;
            Integer asBox = db().queryForObject(
                    "SELECT COUNT(*) FROM blind_pool WHERE box_id=? AND enabled=1",
                    Integer.class, itemId);
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
            Integer dup = db().queryForObject(
                    "SELECT COUNT(*) FROM blind_pool WHERE box_id=? AND prize_id=? AND id<>?",
                    Integer.class, boxId, prizeId, id);
            if (dup != null && dup > 0) throw new IllegalArgumentException("这个奖品已经在这个盒子里");
            if (id > 0) {
                db().update(
                        "UPDATE blind_pool SET box_id=?, prize_id=?, weight=?, hidden=?, enabled=? WHERE id=?",
                        boxId, prizeId, weight, hidden, on, id);
            } else {
                db().update(
                        "INSERT INTO blind_pool (box_id, prize_id, weight, hidden, enabled) VALUES (?,?,?,?,?)",
                        boxId, prizeId, weight, hidden, on);
            }
            db().update("UPDATE " + itemTable() + " SET pity_n=? WHERE id=?", pityNeed, boxId);
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
            int updated = db().update(
                    "UPDATE " + lineTable() + " SET draw_title=?, draw_hidden=? WHERE order_id=? AND item_id=?",
                    text, hidden, orderId, boxId);
            if (updated <= 0) throw new IllegalStateException("抽奖结果未能记到订单");
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置盲盒抽奖字段", e);
        }
    }

    private static void savePity(String username, long boxId, int draws, int hiddenGot) {
        try {
            db().update(
                    "INSERT INTO blind_pity (username, box_id, draws, hidden_got) VALUES (?,?,?,?) "
                            + "ON DUPLICATE KEY UPDATE draws=?, hidden_got=?",
                    username, boxId, draws, hiddenGot, draws, hiddenGot);
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置盲盒保底表", e);
        }
    }

    private static int pityN(long boxId) {
        try {
            Integer n = db().queryForObject(
                    "SELECT pity_n FROM " + itemTable() + " WHERE id=?",
                    Integer.class, boxId);
            return n == null ? 0 : n;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置保底次数", e);
        }
    }

    private static Map<String, Object> loadPity(String username, long boxId) {
        try {
            List<Map<String, Object>> rows = db().query(
                    "SELECT draws, hidden_got FROM blind_pity WHERE username=? AND box_id=?",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("draws", rs.getInt("draws"));
                        m.put("hiddenGot", rs.getInt("hidden_got"));
                        return m;
                    },
                    username, boxId);
            if (!rows.isEmpty()) return rows.get(0);
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
            return db().query(
                    "SELECT p.prize_id, p.weight, p.hidden, i.title, i.stock FROM blind_pool p "
                            + "LEFT JOIN " + itemTable() + " i ON i.id=p.prize_id "
                            + "WHERE p.box_id=? AND p.enabled=1 ORDER BY p.id",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("prizeId", rs.getLong("prize_id"));
                        m.put("weight", rs.getInt("weight"));
                        m.put("hidden", rs.getInt("hidden"));
                        m.put("title", rs.getString("title") == null ? "" : rs.getString("title"));
                        m.put("stock", rs.getInt("stock"));
                        return m;
                    },
                    boxId);
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置盲盒奖池", e);
        }
    }

    private static List<Map<String, Object>> available(List<Map<String, Object>> pool) {
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> row : pool) {
            if (num(row.get("weight")) <= 0) continue;
            if (num(row.get("stock")) <= 0) continue;
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

    private static Map<String, Object> mapBox(java.sql.ResultSet rs) throws java.sql.SQLException {
        int pityNeed = rs.getInt("pity_n");
        int draws = rs.getInt("draws");
        boolean got = rs.getInt("hidden_got") != 0;
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("box_id"));
        m.put("title", rs.getString("title") == null ? "" : rs.getString("title"));
        m.put("pityN", pityNeed);
        m.put("draws", draws);
        m.put("hiddenGot", got);
        m.put("text", pityLine(draws, pityNeed, got));
        return m;
    }

    private static String pityLine(int draws, int pityNeed, boolean got) {
        if (pityNeed <= 0) return "已抽 " + draws + " 次，未设保底";
        if (got) return "已抽 " + draws + " 次，保底 " + pityNeed + " 次，已出隐藏款";
        return "已抽 " + draws + " 次，保底 " + pityNeed + " 次，尚未出隐藏款";
    }

    private static void requireOn() {
        if (!enabled) throw new IllegalStateException("盲盒未开启");
    }

    private static JpaDb db() {
        return JpaSupport.db();
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
