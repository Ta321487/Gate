package com.thesis.capability;

import com.thesis.config.MybatisSupport;
import com.thesis.mapper.BuybackMapper;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 旧书回收。规则与 jdbc 相同，只换数据访问。 */
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
            Integer n = db().unlisted(itemId);
            if (n != null && n > 0) throw new IllegalStateException("还没上架，不能购买");
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置回收", e);
        }
    }

    public static List<Map<String, Object>> slots(boolean onlyEnabled) {
        requireOn();
        List<Map<String, Object>> rows = onlyEnabled ? db().enabledSlots() : db().allSlots();
        return flagRows(rows);
    }

    public static Map<String, Object> saveSlot(Map<String, Object> body) {
        requireOn();
        String name = str(body == null ? null : body.get("name"));
        if (name.isBlank()) throw new IllegalArgumentException("请填写时段名称");
        int on = flag(body == null ? null : body.get("enabled")) ? 1 : 0;
        long id = lng(body == null ? null : body.get("id"));
        if (id > 0) db().updateSlot(id, name, on);
        else db().insertSlot(name, on);
        return Map.of("ok", true);
    }

    public static Map<String, Object> submit(String username, Map<String, Object> body) {
        requireOn();
        String title = str(body == null ? null : body.get("bookTitle"));
        if (title.isBlank()) throw new IllegalArgumentException("请填写书名");
        long slotId = lng(body == null ? null : body.get("slotId"));
        Integer slots = db().openSlotCount();
        Integer on = db().slotOn(slotId);
        if (slots != null && slots > 0 && (on == null || on == 0)) {
            throw new IllegalArgumentException("请选择上门时段");
        }
        db().insertOrder(username, title, str(body == null ? null : body.get("conditionNote")), slotId > 0 ? slotId : null);
        return Map.of("ok", true);
    }

    public static List<Map<String, Object>> mine(String username) {
        requireOn();
        return db().mine(username);
    }

    public static List<Map<String, Object>> all() {
        requireOn();
        return db().allOrders();
    }

    public static Map<String, Object> decide(long id, String username, boolean agree) {
        requireOn();
        Map<String, Object> row = must(id);
        if (!username.equals(String.valueOf(row.get("username")))) {
            throw new IllegalStateException("只能处理自己的回收单");
        }
        if (!"quoted".equals(String.valueOf(row.get("status")))) throw new IllegalStateException("当前不能确认");
        db().setStatus(id, agree ? "agreed" : "closed");
        return Map.of("ok", true);
    }

    public static Map<String, Object> quote(long id, BigDecimal price) {
        requireOn();
        Map<String, Object> row = must(id);
        if (!"pending".equals(String.valueOf(row.get("status")))) throw new IllegalStateException("当前不能报价");
        if (price == null || price.signum() < 0) throw new IllegalArgumentException("请填写报价");
        db().quote(id, price.setScale(2, RoundingMode.HALF_UP));
        return Map.of("ok", true);
    }

    public static Map<String, Object> pick(long id) {
        requireOn();
        if (!"agreed".equals(String.valueOf(must(id).get("status")))) {
            throw new IllegalStateException("当前不能上门");
        }
        db().setStatus(id, "picked");
        return Map.of("ok", true);
    }

    public static Map<String, Object> stock(long id) {
        requireOn();
        Map<String, Object> row = must(id);
        if (!"picked".equals(String.valueOf(row.get("status")))) throw new IllegalStateException("当前不能入库");
        long productId = insertProduct(str(row.get("bookTitle")), money(row.get("quoteYuan")), str(row.get("conditionNote")));
        db().stock(id, productId);
        return Map.of("productId", productId);
    }

    public static Map<String, Object> listOn(long id) {
        requireOn();
        Map<String, Object> row = must(id);
        if (!"stocked".equals(String.valueOf(row.get("status")))) throw new IllegalStateException("当前不能上架");
        long productId = lng(row.get("productId"));
        if (productId <= 0) throw new IllegalStateException("还没入库");
        db().publish(table(ArchiveStore.itemTable()), productId);
        db().setStatus(id, "listed");
        return Map.of("ok", true);
    }

    private static long insertProduct(String title, BigDecimal price, String note) {
        String item = table(ArchiveStore.itemTable());
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("table", item);
        row.put("author", table(ArchiveStore.authorColumn()));
        row.put("isbn", table(ArchiveStore.isbnColumn()));
        row.put("title", title);
        row.put("price", price.toPlainString());
        db().insertProduct(row);
        long id = lng(row.get("id"));
        if (id <= 0) throw new IllegalStateException("系统未配置回收");
        Integer grade = db().gradeColumn(item);
        if (!note.isBlank() && grade != null && grade > 0) db().setGrade(item, note, id);
        return id;
    }

    private static Map<String, Object> must(long id) {
        List<Map<String, Object>> rows = db().one(id);
        if (rows == null || rows.isEmpty()) throw new IllegalArgumentException("回收单不存在");
        return rows.get(0);
    }

    private static List<Map<String, Object>> flagRows(List<Map<String, Object>> rows) {
        if (rows == null) return List.of();
        for (Map<String, Object> row : rows) {
            Object on = row.get("enabled");
            row.put("enabled", on instanceof Number n ? n.intValue() == 1 : Boolean.TRUE.equals(on));
        }
        return rows;
    }

    private static void requireOn() {
        if (!enabled) throw new IllegalStateException("回收未开启");
    }

    private static BuybackMapper db() {
        return MybatisSupport.mapper(BuybackMapper.class);
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
        if (o == null) return true;
        if (o instanceof Boolean b) return b;
        String text = str(o);
        return !"0".equals(text) && !"false".equalsIgnoreCase(text);
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
