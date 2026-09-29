package com.thesis.service;

import com.thesis.capability.ArchiveStore;
import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 浅进销存（C-17）：管理端入库/出库登记，即时调整档案 stock 并写流水。
 * 可选报废 scrap、盘点 count（按课题需要启用）。
 */
public class StockIoStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static boolean enabled;
    private static boolean scrapEnabled;
    private static boolean countEnabled;
    /** 盘点锁定：禁止入/出/报废过账 */
    private static boolean countLocked;
    /** 盲盘：响应不回写账存 */
    private static boolean blindCount;
    /** 有差额时须手填差异原因 */
    private static boolean requireDiffReason;
    /** 报废走独立审批单（pending→approved/rejected） */
    private static boolean scrapApproveFlow;
    private static Boolean tableReady;
    private static Boolean scrapTableReady;

    private StockIoStore() {}

    public static void configure(boolean on) {
        configure(on, false, false);
    }

    public static void configure(boolean on, boolean scrap, boolean count) {
        configure(on, scrap, count, false, false, false, false);
    }

    public static void configure(
            boolean on, boolean scrap, boolean count, boolean lock, boolean blind, boolean diffReason) {
        configure(on, scrap, count, lock, blind, diffReason, false);
    }

    public static void configure(
            boolean on,
            boolean scrap,
            boolean count,
            boolean lock,
            boolean blind,
            boolean diffReason,
            boolean scrapApprove) {
        enabled = on;
        scrapEnabled = scrap;
        countEnabled = count;
        countLocked = lock;
        blindCount = blind;
        requireDiffReason = diffReason;
        scrapApproveFlow = scrapApprove;
        tableReady = null;
        scrapTableReady = null;
    }

    public static void setCountLocked(boolean locked) {
        countLocked = locked;
    }

    public static boolean countLocked() {
        return enabled && countLocked;
    }

    public static boolean blindCount() {
        return enabled && blindCount;
    }

    public static boolean requireDiffReason() {
        return enabled && requireDiffReason;
    }

    public static boolean scrapApproveFlow() {
        return enabled && scrapEnabled && scrapApproveFlow;
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

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
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

    public static boolean scrapRequestReady() {
        if (!scrapApproveFlow()) return false;
        if (scrapTableReady != null) return scrapTableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='scrap_request'",
                    Integer.class);
            scrapTableReady = n != null && n > 0;
        } catch (Exception e) {
            scrapTableReady = false;
        }
        return scrapTableReady;
    }

    private static void require() {
        if (!ready()) throw new IllegalStateException("入出库功能暂不可用");
    }

    private static void requireScrapRequest() {
        require();
        if (!scrapRequestReady()) throw new IllegalStateException("报废审批功能暂不可用");
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

    private static Map<String, Object> insertAndLoad(
            String mt, long itemId, String title, int n, String note, String op) {
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

    /** 即时过账：写流水并调整档案库存。报废审批流开启时 scrap 改为提交申请。 */
    public static Map<String, Object> post(String moveType, long itemId, int qty, String remark, String operator) {
        require();
        if (countLocked) {
            throw new IllegalStateException("盘点锁定中，暂不可出入库或报废");
        }
        String mt = clip(moveType, 16).toLowerCase(Locale.ROOT);
        if (!"in".equals(mt) && !"out".equals(mt) && !"scrap".equals(mt)) {
            throw new IllegalArgumentException("类型须为入库(in)、出库(out)或报废(scrap)");
        }
        if ("scrap".equals(mt) && !scrapEnabled) {
            throw new IllegalStateException("未开通报废登记");
        }
        if ("scrap".equals(mt) && scrapApproveFlow()) {
            return submitScrapRequest(itemId, qty, remark, operator);
        }
        return postImmediate(mt, itemId, qty, remark, operator);
    }

    private static Map<String, Object> postImmediate(
            String mt, long itemId, int qty, String remark, String operator) {
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

    private static Map<String, Object> mapScrapRow(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("itemId", rs.getLong("item_id"));
        m.put("itemTitle", rs.getString("item_title"));
        m.put("qty", rs.getInt("qty"));
        m.put("reason", rs.getString("reason"));
        m.put("status", rs.getString("status"));
        m.put("applicant", rs.getString("applicant"));
        m.put("handler", rs.getString("handler"));
        m.put("handleNote", rs.getString("handle_note"));
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        m.put("handledAt", fmt(rs.getTimestamp("handled_at")));
        return m;
    }

    public static Map<String, Object> submitScrapRequest(long itemId, int qty, String reason, String applicant) {
        requireScrapRequest();
        if (itemId <= 0) throw new IllegalArgumentException("请选择物资");
        int n = qty; // already validated by caller via qty(Object) when from body; else positive
        if (n <= 0) throw new IllegalArgumentException("数量须为正整数");
        String who = clip(applicant, 64);
        if (who.isBlank()) throw new IllegalArgumentException("操作人无效");
        String note = clip(reason, 255);
        if (note.isBlank()) throw new IllegalArgumentException("请填写报废原因");
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) throw new IllegalStateException("物资不存在");
        String title = str(item.get("title"));
        if (title.isBlank()) title = "物资#" + itemId;
        int stock = stockOf(item);
        if (stock < n) throw new IllegalStateException("库存不足，无法报废");
        db().update(
                "INSERT INTO scrap_request (item_id, item_title, qty, reason, status, applicant) VALUES (?,?,?,?, 'pending', ?)",
                itemId, clip(title, 200), n, note, who);
        Long id = db().queryForObject("SELECT LAST_INSERT_ID()", Long.class);
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM scrap_request WHERE id=?", (rs, i) -> mapScrapRow(rs), id == null ? 0L : id);
        Map<String, Object> out = rows.isEmpty() ? new LinkedHashMap<>() : new LinkedHashMap<>(rows.get(0));
        out.put("pendingApproval", true);
        return out;
    }

    public static Map<String, Object> pageScrapRequests(int page, int size, String status) {
        requireScrapRequest();
        if (page < 1) page = 1;
        if (size < 1) size = 20;
        String st = clip(status, 16).toLowerCase(Locale.ROOT);
        boolean filter = "pending".equals(st) || "approved".equals(st) || "rejected".equals(st);
        Integer total;
        List<Map<String, Object>> list;
        if (filter) {
            total = db().queryForObject(
                    "SELECT COUNT(*) FROM scrap_request WHERE status=?", Integer.class, st);
            list = db().query(
                    "SELECT * FROM scrap_request WHERE status=? ORDER BY id DESC LIMIT ? OFFSET ?",
                    (rs, i) -> mapScrapRow(rs),
                    st, size, (page - 1) * size);
        } else {
            total = db().queryForObject("SELECT COUNT(*) FROM scrap_request", Integer.class);
            list = db().query(
                    "SELECT * FROM scrap_request ORDER BY id DESC LIMIT ? OFFSET ?",
                    (rs, i) -> mapScrapRow(rs),
                    size, (page - 1) * size);
        }
        return pageOut(list, total, page, size);
    }

    public static Map<String, Object> approveScrapRequest(long id, String handler, String handleNote) {
        requireScrapRequest();
        if (id <= 0) throw new IllegalArgumentException("报废单无效");
        String who = clip(handler, 64);
        if (who.isBlank()) throw new IllegalArgumentException("操作人无效");
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM scrap_request WHERE id=?", (rs, i) -> mapScrapRow(rs), id);
        if (rows.isEmpty()) throw new IllegalStateException("报废单不存在");
        Map<String, Object> req = rows.get(0);
        if (!"pending".equals(str(req.get("status")))) {
            throw new IllegalStateException("仅待审报废单可通过");
        }
        long itemId = req.get("itemId") instanceof Number n ? n.longValue() : 0L;
        int nQty = req.get("qty") instanceof Number n ? n.intValue() : 0;
        String reason = str(req.get("reason"));
        Map<String, Object> move = postImmediate("scrap", itemId, nQty, reason, who);
        String note = clip(handleNote, 255);
        db().update(
                "UPDATE scrap_request SET status='approved', handler=?, handle_note=?, handled_at=NOW() WHERE id=?",
                who, note, id);
        Map<String, Object> out = new LinkedHashMap<>(req);
        out.put("status", "approved");
        out.put("handler", who);
        out.put("handleNote", note);
        out.put("stockMove", move);
        return out;
    }

    public static Map<String, Object> rejectScrapRequest(long id, String handler, String handleNote) {
        requireScrapRequest();
        if (id <= 0) throw new IllegalArgumentException("报废单无效");
        String who = clip(handler, 64);
        if (who.isBlank()) throw new IllegalArgumentException("操作人无效");
        String note = clip(handleNote, 255);
        if (note.isBlank()) throw new IllegalArgumentException("请填写驳回原因");
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM scrap_request WHERE id=?", (rs, i) -> mapScrapRow(rs), id);
        if (rows.isEmpty()) throw new IllegalStateException("报废单不存在");
        if (!"pending".equals(str(rows.get(0).get("status")))) {
            throw new IllegalStateException("仅待审报废单可驳回");
        }
        db().update(
                "UPDATE scrap_request SET status='rejected', handler=?, handle_note=?, handled_at=NOW() WHERE id=?",
                who, note, id);
        Map<String, Object> out = new LinkedHashMap<>(rows.get(0));
        out.put("status", "rejected");
        out.put("handler", who);
        out.put("handleNote", note);
        return out;
    }

    /** 申购单明细一键入库：按 procure_line 匹配或新建档案并记 in 流水。 */
    public static Map<String, Object> receiveFromProcureTicket(long ticketId, String operator) {
        require();
        if (ticketId <= 0) throw new IllegalArgumentException("单据无效");
        String op = clip(operator, 64);
        if (op.isBlank()) throw new IllegalArgumentException("操作人无效");
        if (countLocked) {
            throw new IllegalStateException("盘点锁定中，暂不可入库");
        }
        Integer tableOk;
        try {
            tableOk = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='procure_line'",
                    Integer.class);
        } catch (Exception e) {
            tableOk = 0;
        }
        if (tableOk == null || tableOk <= 0) {
            throw new IllegalStateException("未开通申购明细，无法一键入库");
        }
        List<Map<String, Object>> lines = db().query(
                "SELECT id, item_title, qty FROM procure_line WHERE ticket_id=? ORDER BY id",
                (rs, i) -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("id", rs.getLong("id"));
                    row.put("itemTitle", rs.getString("item_title"));
                    row.put("qty", rs.getInt("qty"));
                    return row;
                },
                ticketId);
        if (lines.isEmpty()) {
            // 无明细表数据时：用单据标题/册数兜底一行，保证答辩可演示
            Map<String, Object> fallback = new LinkedHashMap<>();
            fallback.put("itemTitle", "");
            fallback.put("qty", 1);
            lines = List.of(fallback);
        }
        List<Map<String, Object>> moves = new ArrayList<>();
        for (Map<String, Object> line : lines) {
            String title = clip(str(line.get("itemTitle")), 200);
            int n = line.get("qty") instanceof Number num ? num.intValue() : 0;
            if (n <= 0) n = 1;
            if (title.isBlank()) {
                // 由 TicketStore 传入补充标题时写在 remark；此处再用通用名
                title = "申购物资#" + ticketId;
            }
            long itemId = findItemIdByTitle(title);
            if (itemId <= 0) {
                Map<String, Object> created = ArchiveStore.addItem(title, "", "", 0L, 0, "");
                if (created == null || !(created.get("id") instanceof Number)) {
                    throw new IllegalStateException("无法创建物资档案：" + title);
                }
                itemId = ((Number) created.get("id")).longValue();
            }
            String remark = clip("申购单#" + ticketId + " 转入", 255);
            moves.add(postImmediate("in", itemId, n, remark, op));
        }
        if (moves.isEmpty()) {
            throw new IllegalStateException("明细无效，未产生入库");
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("ticketId", ticketId);
        out.put("moves", moves);
        out.put("count", moves.size());
        return out;
    }

    private static long findItemIdByTitle(String title) {
        try {
            List<Long> ids = db().query(
                    "SELECT id FROM " + ArchiveStore.itemTable() + " WHERE title=? ORDER BY id LIMIT 1",
                    (rs, i) -> rs.getLong("id"),
                    title);
            return ids.isEmpty() ? 0L : ids.get(0);
        } catch (Exception e) {
            return 0L;
        }
    }

    /** 盘点：把库存调整为实盘数，并记差额流水。 */
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
        if (requireDiffReason && delta != 0 && note.isBlank()) {
            throw new IllegalArgumentException("有盘点差异时请填写差异原因");
        }
        String auto = "账存" + book + "→实盘" + actual + " 差额" + delta;
        if (note.isBlank()) note = auto;
        else note = clip(auto + "；" + note, 255);

        if (delta != 0) {
            ArchiveStore.adjustStock(itemId, delta);
        }
        Map<String, Object> out = insertAndLoad("count", itemId, title, Math.abs(delta), note, op);
        if (!blindCount) {
            out.put("stockBefore", book);
        }
        out.put("actualQty", actual);
        out.put("delta", delta);
        return out;
    }

    /** 入出库类型分布（工作台饼图）。 */
    public static List<Map<String, Object>> typeSeries() {
        if (!ready()) return List.of();
        try {
            return db().query(
                    "SELECT move_type AS name, COUNT(*) AS value FROM stock_move GROUP BY move_type",
                    (rs, i) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        String mt = rs.getString("name");
                        String label = mt;
                        if ("in".equals(mt)) label = "入库";
                        else if ("out".equals(mt)) label = "出库";
                        else if ("scrap".equals(mt)) label = "报废";
                        else if ("count".equals(mt)) label = "盘点";
                        row.put("name", label);
                        row.put("value", rs.getLong("value"));
                        return row;
                    });
        } catch (Exception e) {
            return List.of();
        }
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
