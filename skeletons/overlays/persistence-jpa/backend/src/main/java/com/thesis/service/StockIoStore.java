package com.thesis.service;

import com.thesis.capability.ArchiveStore;
import com.thesis.config.JpaSupport;
import com.thesis.config.JpaDb;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 浅进销存（C-17）：管理端入库/出库登记，即时调整档案 stock 并写流水。
 */
public class StockIoStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static boolean enabled;
    private static Boolean tableReady;

    private StockIoStore() {}

    public static void configure(boolean on) {
        enabled = on;
        tableReady = null;
    }

    public static boolean enabled() {
        return enabled;
    }

    private static JpaDb db() {
        return JpaSupport.db();
    }

    public static boolean ready() {
        if (!enabled) return false;
        if (tableReady != null) return tableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='stock_move'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static void require() {
        if (!ready()) throw new IllegalStateException("入出库功能暂不可用");
    }

    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        String s = String.valueOf(o);
        return s.isBlank() ? null : s;
    }

    private static String clip(String s, int max) {
        if (s == null) return "";
        String t = s.trim();
        return t.length() <= max ? t : t.substring(0, max);
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static int qty(Object o) {
        if (o == null || String.valueOf(o).isBlank()) {
            throw new IllegalArgumentException("数量无效");
        }
        int n;
        if (o instanceof Number num) n = num.intValue();
        else n = Integer.parseInt(String.valueOf(o).trim());
        if (n <= 0) throw new IllegalArgumentException("数量须为正整数");
        if (n > 999999) throw new IllegalArgumentException("单次数量过大");
        return n;
    }

    private static Map<String, Object> pageOut(List<?> list, Integer total, int page, int size) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    private static Map<String, Object> mapRow(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("moveType", rs.getString("move_type"));
        m.put("itemId", rs.getLong("item_id"));
        m.put("itemTitle", rs.getString("item_title"));
        m.put("qty", rs.getInt("qty"));
        m.put("remark", rs.getString("remark"));
        m.put("operator", rs.getString("operator"));
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        return m;
    }

    public static Map<String, Object> pageMoves(int page, int size, String moveType) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 20;
        String mt = clip(moveType, 16).toLowerCase(Locale.ROOT);
        boolean filter = "in".equals(mt) || "out".equals(mt);
        Integer total;
        List<Map<String, Object>> list;
        if (filter) {
            total = db().queryForObject(
                    "SELECT COUNT(*) FROM stock_move WHERE move_type=?", Integer.class, mt);
            list = db().query(
                    "SELECT * FROM stock_move WHERE move_type=? ORDER BY id DESC LIMIT ? OFFSET ?",
                    (rs, i) -> mapRow(rs),
                    mt, size, (page - 1) * size);
        } else {
            total = db().queryForObject("SELECT COUNT(*) FROM stock_move", Integer.class);
            list = db().query(
                    "SELECT * FROM stock_move ORDER BY id DESC LIMIT ? OFFSET ?",
                    (rs, i) -> mapRow(rs),
                    size, (page - 1) * size);
        }
        return pageOut(list, total, page, size);
    }

    /** 即时过账：写流水并调整档案库存。 */
    public static Map<String, Object> post(String moveType, long itemId, int qty, String remark, String operator) {
        require();
        String mt = clip(moveType, 16).toLowerCase(Locale.ROOT);
        if (!"in".equals(mt) && !"out".equals(mt)) {
            throw new IllegalArgumentException("类型须为入库(in)或出库(out)");
        }
        if (itemId <= 0) throw new IllegalArgumentException("请选择物资");
        int n = qty;
        String op = clip(operator, 64);
        if (op.isBlank()) throw new IllegalArgumentException("操作人无效");
        String note = clip(remark, 255);

        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) throw new IllegalStateException("物资不存在");
        String title = str(item.get("title"));
        if (title.isBlank()) title = "物资#" + itemId;

        int delta = "in".equals(mt) ? n : -n;
        ArchiveStore.adjustStock(itemId, delta);

        db().update(
                "INSERT INTO stock_move (move_type, item_id, item_title, qty, remark, operator) VALUES (?,?,?,?,?,?)",
                mt, itemId, clip(title, 200), n, note, op);
        Long id = db().queryForObject("SELECT LAST_INSERT_ID()", Long.class);
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM stock_move WHERE id=?", (rs, i) -> mapRow(rs), id == null ? 0L : id);
        Map<String, Object> out = rows.isEmpty() ? new LinkedHashMap<>() : new LinkedHashMap<>(rows.get(0));
        Map<String, Object> after = ArchiveStore.getItemRaw(itemId);
        if (after != null && after.get("stock") instanceof Number sn) {
            out.put("stockAfter", sn.intValue());
        }
        return out;
    }

    public static Map<String, Object> postFromBody(Map<String, Object> body, String operator) {
        Map<String, Object> b = body == null ? Map.of() : body;
        String mt = str(b.get("moveType"));
        if (mt.isBlank()) mt = str(b.get("type"));
        long itemId = 0L;
        Object rawId = b.get("itemId");
        if (rawId == null) rawId = b.get("bookId");
        if (rawId instanceof Number num) itemId = num.longValue();
        else if (rawId != null && !String.valueOf(rawId).isBlank()) {
            itemId = Long.parseLong(String.valueOf(rawId).trim());
        }
        return post(mt, itemId, qty(b.get("qty")), str(b.get("remark")), operator);
    }
}
