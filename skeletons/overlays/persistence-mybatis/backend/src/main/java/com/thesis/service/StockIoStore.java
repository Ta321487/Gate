package com.thesis.service;

import com.thesis.capability.ArchiveStore;
import com.thesis.config.MybatisSupport;
import com.thesis.mapper.StockIoMapper;

import java.util.*;

/** 浅进销存（C-17）MyBatis 叠层；E-08 报废/盘点。 */
public class StockIoStore {

    private static boolean enabled;
    private static boolean scrapEnabled;
    private static boolean countEnabled;
    private static Boolean tableReady;

    private StockIoStore() {}

    private static StockIoMapper mapper() {
        return MybatisSupport.mapper(StockIoMapper.class);
    }

    public static void configure(boolean on) {
        configure(on, false, false);
    }

    public static void configure(boolean on, boolean scrap, boolean count) {
        enabled = on;
        scrapEnabled = scrap;
        countEnabled = count;
        tableReady = null;
    }

    public static boolean enabled() {
        return enabled;
    }

    public static boolean scrapEnabled() {
        return enabled && scrapEnabled;
    }

    public static boolean countEnabled() {
        return enabled && countEnabled;
    }

    public static boolean ready() {
        if (!enabled) return false;
        if (tableReady != null) return tableReady;
        try {
            Integer n = mapper().countTable();
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static void require() {
        if (!ready()) throw new IllegalStateException("入出库功能暂不可用");
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

    private static int nonNegQty(Object o) {
        if (o == null || String.valueOf(o).isBlank()) {
            throw new IllegalArgumentException("实盘数量无效");
        }
        int n;
        if (o instanceof Number num) n = num.intValue();
        else n = Integer.parseInt(String.valueOf(o).trim());
        if (n < 0) throw new IllegalArgumentException("实盘数量不能为负");
        if (n > 999999) throw new IllegalArgumentException("实盘数量过大");
        return n;
    }

    private static int stockOf(Map<String, Object> item) {
        Object s = item.get("stock");
        if (s instanceof Number num) return num.intValue();
        if (s != null && !String.valueOf(s).isBlank()) {
            return Integer.parseInt(String.valueOf(s).trim());
        }
        return 0;
    }

    private static Map<String, Object> pageOut(List<?> list, Integer total, int page, int size) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    private static boolean filterType(String mt) {
        return "in".equals(mt) || "out".equals(mt) || "scrap".equals(mt) || "count".equals(mt);
    }

    public static Map<String, Object> pageMoves(int page, int size, String moveType) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 20;
        String mt = clip(moveType, 16).toLowerCase(Locale.ROOT);
        boolean filter = filterType(mt);
        Integer total;
        List<Map<String, Object>> list;
        if (filter) {
            total = mapper().countByType(mt);
            list = mapper().pageByType(mt, size, (page - 1) * size);
        } else {
            total = mapper().countAll();
            list = mapper().pageAll(size, (page - 1) * size);
        }
        return pageOut(list, total, page, size);
    }

    private static Map<String, Object> insertAndLoad(
            String mt, long itemId, String title, int n, String note, String op) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("moveType", mt);
        row.put("itemId", itemId);
        row.put("itemTitle", clip(title, 200));
        row.put("qty", n);
        row.put("remark", note);
        row.put("operator", op);
        mapper().insert(row);
        Object idObj = row.get("id");
        long id = idObj instanceof Number num ? num.longValue() : 0L;
        Map<String, Object> out = mapper().getById(id);
        if (out == null) out = new LinkedHashMap<>(row);
        else out = new LinkedHashMap<>(out);
        Map<String, Object> after = ArchiveStore.getItemRaw(itemId);
        if (after != null && after.get("stock") instanceof Number sn) {
            out.put("stockAfter", sn.intValue());
        }
        return out;
    }

    public static Map<String, Object> post(String moveType, long itemId, int qty, String remark, String operator) {
        require();
        String mt = clip(moveType, 16).toLowerCase(Locale.ROOT);
        if (!"in".equals(mt) && !"out".equals(mt) && !"scrap".equals(mt)) {
            throw new IllegalArgumentException("类型须为入库(in)、出库(out)或报废(scrap)");
        }
        if ("scrap".equals(mt) && !scrapEnabled) {
            throw new IllegalStateException("未开通报废登记");
        }
        if (itemId <= 0) throw new IllegalArgumentException("请选择物资");
        int n = qty;
        String op = clip(operator, 64);
        if (op.isBlank()) throw new IllegalArgumentException("操作人无效");
        String note = clip(remark, 255);
        if ("scrap".equals(mt) && note.isBlank()) {
            throw new IllegalArgumentException("请填写报废原因");
        }

        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) throw new IllegalStateException("物资不存在");
        String title = str(item.get("title"));
        if (title.isBlank()) title = "物资#" + itemId;

        int delta = "in".equals(mt) ? n : -n;
        ArchiveStore.adjustStock(itemId, delta);
        return insertAndLoad(mt, itemId, title, n, note, op);
    }

    public static Map<String, Object> postCount(long itemId, int actualQty, String remark, String operator) {
        require();
        if (!countEnabled) throw new IllegalStateException("未开通盘点登记");
        if (itemId <= 0) throw new IllegalArgumentException("请选择物资");
        String op = clip(operator, 64);
        if (op.isBlank()) throw new IllegalArgumentException("操作人无效");
        int actual = actualQty;

        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) throw new IllegalStateException("物资不存在");
        String title = str(item.get("title"));
        if (title.isBlank()) title = "物资#" + itemId;
        int book = stockOf(item);
        int delta = actual - book;
        String note = clip(remark, 255);
        String auto = "账存" + book + "→实盘" + actual + " 差额" + delta;
        if (note.isBlank()) note = auto;
        else note = clip(auto + "；" + note, 255);

        if (delta != 0) {
            ArchiveStore.adjustStock(itemId, delta);
        }
        Map<String, Object> out = insertAndLoad("count", itemId, title, Math.abs(delta), note, op);
        out.put("stockBefore", book);
        out.put("actualQty", actual);
        out.put("delta", delta);
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
        mt = clip(mt, 16).toLowerCase(Locale.ROOT);
        if ("count".equals(mt)) {
            Object rawActual = b.get("actualQty");
            if (rawActual == null) rawActual = b.get("qty");
            return postCount(itemId, nonNegQty(rawActual), str(b.get("remark")), operator);
        }
        return post(mt, itemId, qty(b.get("qty")), str(b.get("remark")), operator);
    }
}
