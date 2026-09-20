package com.thesis.capability;

import com.thesis.config.GeneratedKeyHolder;
import com.thesis.config.JpaDb;
import com.thesis.config.JpaSupport;
import com.thesis.config.KeyHolder;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.PreparedStatement;
import java.sql.Statement;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 旧书回收。上架前不能买。商品仍走档案表。 */
public final class BuybackStore {

    private static boolean enabled;

    private BuybackStore() {}

    public static void configure(boolean on) {
        enabled = on;
    }

    public static boolean enabled() {
        return enabled;
    }

    public static void assertListed(long itemId) {
        if (!enabled || itemId <= 0) return;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM buyback_order WHERE product_id=? AND status<>'listed'",
                    Integer.class, itemId);
            if (n != null && n > 0) throw new IllegalStateException("还没上架，不能购买");
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置回收", e);
        }
    }

    public static List<Map<String, Object>> slots(boolean onlyEnabled) {
        requireOn();
        String sql = onlyEnabled
                ? "SELECT id, name, enabled FROM buyback_slot WHERE enabled=1 ORDER BY id"
                : "SELECT id, name, enabled FROM buyback_slot ORDER BY id";
        return db().query(sql, (rs, i) -> {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id", rs.getLong("id"));
            m.put("name", rs.getString("name"));
            m.put("enabled", rs.getInt("enabled") == 1);
            return m;
        });
    }

    public static Map<String, Object> saveSlot(Map<String, Object> body) {
        requireOn();
        String name = str(body == null ? null : body.get("name"));
        if (name.isBlank()) throw new IllegalArgumentException("请填写时段名称");
        int on = flag(body == null ? null : body.get("enabled")) ? 1 : 0;
        long id = lng(body == null ? null : body.get("id"));
        if (id > 0) {
            db().update("UPDATE buyback_slot SET name=?, enabled=? WHERE id=?", name, on, id);
        } else {
            db().update("INSERT INTO buyback_slot (name, enabled) VALUES (?,?)", name, on);
        }
        return Map.of("ok", true);
    }

    public static Map<String, Object> submit(String username, Map<String, Object> body) {
        requireOn();
        String title = str(body == null ? null : body.get("bookTitle"));
        if (title.isBlank()) throw new IllegalArgumentException("请填写书名");
        long slotId = lng(body == null ? null : body.get("slotId"));
        Integer slots = db().queryForObject(
                "SELECT COUNT(*) FROM buyback_slot WHERE enabled=1", Integer.class);
        if (slots != null && slots > 0 && !slotOpen(slotId)) {
            throw new IllegalArgumentException("请选择上门时段");
        }
        String note = str(body == null ? null : body.get("conditionNote"));
        db().update(
                "INSERT INTO buyback_order (username, book_title, condition_note, slot_id, status) VALUES (?,?,?,?,'pending')",
                username, title, note, slotId > 0 ? slotId : null);
        return Map.of("ok", true);
    }

    public static List<Map<String, Object>> mine(String username) {
        requireOn();
        return db().query(
                "SELECT o.id, o.book_title, o.condition_note, o.quote_yuan, o.status, o.product_id, s.name AS slot_name "
                        + "FROM buyback_order o LEFT JOIN buyback_slot s ON s.id=o.slot_id "
                        + "WHERE o.username=? ORDER BY o.id DESC",
                (rs, i) -> orderRow(rs),
                username);
    }

    public static List<Map<String, Object>> all() {
        requireOn();
        return db().query(
                "SELECT o.id, o.username, o.book_title, o.condition_note, o.quote_yuan, o.status, o.product_id, s.name AS slot_name "
                        + "FROM buyback_order o LEFT JOIN buyback_slot s ON s.id=o.slot_id ORDER BY o.id DESC",
                (rs, i) -> {
                    Map<String, Object> m = orderRow(rs);
                    m.put("username", rs.getString("username"));
                    return m;
                });
    }

    public static Map<String, Object> decide(long id, String username, boolean agree) {
        requireOn();
        Map<String, Object> row = must(id);
        if (!username.equals(String.valueOf(row.get("username")))) {
            throw new IllegalStateException("只能处理自己的回收单");
        }
        if (!"quoted".equals(row.get("status"))) throw new IllegalStateException("当前不能确认");
        db().update(
                "UPDATE buyback_order SET status=? WHERE id=?",
                agree ? "agreed" : "closed", id);
        return Map.of("ok", true);
    }

    public static Map<String, Object> quote(long id, BigDecimal price) {
        requireOn();
        Map<String, Object> row = must(id);
        if (!"pending".equals(row.get("status"))) throw new IllegalStateException("当前不能报价");
        if (price == null || price.signum() < 0) throw new IllegalArgumentException("请填写报价");
        BigDecimal yuan = price.setScale(2, RoundingMode.HALF_UP);
        db().update("UPDATE buyback_order SET quote_yuan=?, status='quoted' WHERE id=?", yuan, id);
        return Map.of("ok", true);
    }

    public static Map<String, Object> pick(long id) {
        requireOn();
        Map<String, Object> row = must(id);
        if (!"agreed".equals(row.get("status"))) throw new IllegalStateException("当前不能上门");
        db().update("UPDATE buyback_order SET status='picked' WHERE id=?", id);
        return Map.of("ok", true);
    }

    public static Map<String, Object> stock(long id) {
        requireOn();
        Map<String, Object> row = must(id);
        if (!"picked".equals(row.get("status"))) throw new IllegalStateException("当前不能入库");
        long productId = insertProduct(str(row.get("bookTitle")), money(row.get("quoteYuan")), str(row.get("conditionNote")));
        db().update("UPDATE buyback_order SET product_id=?, status='stocked' WHERE id=?", productId, id);
        return Map.of("productId", productId);
    }

    public static Map<String, Object> listOn(long id) {
        requireOn();
        Map<String, Object> row = must(id);
        if (!"stocked".equals(row.get("status"))) throw new IllegalStateException("当前不能上架");
        long productId = lng(row.get("productId"));
        if (productId <= 0) throw new IllegalStateException("还没入库");
        String table = table(ArchiveStore.itemTable());
        db().update("UPDATE " + table + " SET stock=1, status='available' WHERE id=?", productId);
        db().update("UPDATE buyback_order SET status='listed' WHERE id=?", id);
        return Map.of("ok", true);
    }

    private static long insertProduct(String title, BigDecimal price, String note) {
        String table = table(ArchiveStore.itemTable());
        String author = table(ArchiveStore.authorColumn());
        String isbn = table(ArchiveStore.isbnColumn());
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO " + table + " (title," + author + "," + isbn
                            + ",category_id,stock,status,cover_url) VALUES (?,?,?,1,0,'unavailable','')",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, title);
            ps.setString(2, price.toPlainString());
            ps.setString(3, "");
            return ps;
        }, kh);
        Number key = kh.getKey();
        long id = key == null ? 0L : key.longValue();
        if (id <= 0) throw new IllegalStateException("系统未配置回收");
        if (!note.isBlank() && hasColumn(table, "condition_grade")) {
            db().update("UPDATE " + table + " SET condition_grade=? WHERE id=?", note, id);
        }
        return id;
    }

    private static boolean hasColumn(String table, String column) {
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name=? AND column_name=?",
                Integer.class, table, column);
        return n != null && n > 0;
    }

    private static boolean slotOpen(long id) {
        if (id <= 0) return false;
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM buyback_slot WHERE id=? AND enabled=1", Integer.class, id);
        return n != null && n > 0;
    }

    private static Map<String, Object> must(long id) {
        List<Map<String, Object>> rows = db().query(
                "SELECT o.id, o.username, o.book_title, o.condition_note, o.quote_yuan, o.status, o.product_id "
                        + "FROM buyback_order o WHERE o.id=?",
                (rs, i) -> orderRow(rs),
                id);
        if (rows.isEmpty()) throw new IllegalArgumentException("回收单不存在");
        Map<String, Object> row = rows.get(0);
        List<String> users = db().query(
                "SELECT username FROM buyback_order WHERE id=?",
                (rs, i) -> rs.getString("username"), id);
        if (!users.isEmpty()) row.put("username", users.get(0));
        return row;
    }

    private static Map<String, Object> orderRow(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("bookTitle", rs.getString("book_title"));
        m.put("conditionNote", rs.getString("condition_note"));
        m.put("quoteYuan", rs.getBigDecimal("quote_yuan"));
        m.put("status", rs.getString("status"));
        long productId = rs.getLong("product_id");
        m.put("productId", rs.wasNull() ? null : productId);
        try {
            m.put("slotName", rs.getString("slot_name"));
        } catch (java.sql.SQLException ignored) {
            m.put("slotName", "");
        }
        return m;
    }

    private static void requireOn() {
        if (!enabled) throw new IllegalStateException("回收未开启");
    }

    private static JpaDb db() {
        return JpaSupport.db();
    }

    private static String table(String name) {
        if (name == null || !name.matches("[A-Za-z_][A-Za-z0-9_]*")) {
            throw new IllegalStateException("系统未配置回收");
        }
        return name;
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static long lng(Object o) {
        if (o instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(str(o));
        } catch (Exception e) {
            return 0L;
        }
    }

    private static boolean flag(Object o) {
        if (o instanceof Boolean b) return b;
        String text = str(o);
        return !"0".equals(text) && !"false".equalsIgnoreCase(text) && !text.isBlank();
    }

    private static BigDecimal money(Object o) {
        if (o instanceof BigDecimal b) return b;
        try {
            return new BigDecimal(str(o));
        } catch (Exception e) {
            return BigDecimal.ZERO;
        }
    }
}
